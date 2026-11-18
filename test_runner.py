import os
import sys
import json
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import pytest
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_FILE = os.path.join(SCRIPT_DIR, "test-report.json")

class PytestReportCollector:
    """Pytest plugin to collect test execution results."""
    def __init__(self):
        self.reports = []

    def pytest_runtest_logreport(self, report):
        # Collect results for the call phase, or setup/teardown if failure occurred there
        if report.when == "call" or (report.when in ("setup", "teardown") and report.failed):
            self.reports.append(report)


def build_test_report(reports, exit_code):
    """
    Constructs the test report JSON adhering to the exact assignment specifications:
    - Repository name, branch, commit SHA, pipeline run identifier, and execution timestamp.
    - Each test's name, result, and failure message where applicable.
    - Total, passed, and failed test counts, together with the overall test status.
    """
    tests_summary = []
    passed_count = 0
    failed_count = 0

    for rep in reports:
        test_name = rep.nodeid.split("::")[-1]
        if rep.passed:
            passed_count += 1
            result = "PASSED"
            failure_message = None
        else:
            failed_count += 1
            result = "FAILED"
            failure_message = str(rep.longrepr)

        tests_summary.append({
            "name": test_name,
            "full_id": rep.nodeid,
            "result": result,
            "duration_seconds": round(getattr(rep, "duration", 0.0), 4),
            "failure_message": failure_message
        })

    total_count = len(tests_summary)
    overall_status = "PASSED" if (failed_count == 0 and exit_code == 0 and total_count > 0) else "FAILED"

    # Capture CI or local environment metadata
    repo_name = os.environ.get("GITHUB_REPOSITORY", "afzanoor1285-gif/assignment-submission-portal")
    
    if "GITHUB_SHA" in os.environ:
        commit_sha = os.environ.get("GITHUB_SHA")
        branch = os.environ.get("GITHUB_REF_NAME", "main")
        run_id = str(os.environ.get("GITHUB_RUN_ID", f"run-{int(datetime.now().timestamp())}"))
    else:
        # Local execution: extract actual git details if available
        try:
            import subprocess
            commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
            branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
        except Exception:
            commit_sha = "local-commit-" + datetime.now().strftime("%Y%m%d%H%M%S")
            branch = "main"
        run_id = f"local-{int(datetime.now().timestamp())}"
        
    timestamp = datetime.now(timezone.utc).isoformat()

    report = {
        "repository": repo_name,
        "branch": branch,
        "commit_sha": commit_sha,
        "pipeline_run_id": str(run_id),
        "execution_timestamp": timestamp,
        "overall_status": overall_status,
        "total_tests": total_count,
        "passed_tests": passed_count,
        "failed_tests": failed_count,
        "tests": tests_summary
    }

    return report


def save_report_locally(report):
    """Saves the report locally to test-report.json."""
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Saved test report to local file: {os.path.abspath(REPORT_FILE)}")


def send_report_to_receiver(report):
    """
    Delivers the test report via HTTP POST to the local receiver or tunnel URL.
    Meets Requirement 4 (Send report to localhost and save JSON).
    """
    raw_url = os.environ.get("RECEIVER_URL", "").strip()
    receiver_url = raw_url if raw_url else "http://localhost:5050/report"
    if not receiver_url.startswith("http://") and not receiver_url.startswith("https://"):
        receiver_url = f"https://{receiver_url}"
    print(f"\n📡 Attempting to send report to receiver at: {receiver_url}")
    
    try:
        response = requests.post(
            receiver_url,
            json=report,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if response.status_code == 200:
            print(f"✅ Successfully delivered report to receiver! (HTTP {response.status_code})")
            print(f"   Response: {response.text.strip()}")
            return True
        else:
            print(f"⚠️ Receiver returned status {response.status_code}: {response.text.strip()}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Could not reach receiver at {receiver_url}: {e}")
        print("   Note: Ensure receiver.py is running on localhost:5050 or tunnel URL (RECEIVER_URL) is configured.")
        return False


def send_email_report(report):
    """
    Bonus Task 2 (5 marks):
    Automatically send the test report to a configurable email address after
    both passing and failing test runs.
    """
    server_host = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    port = int(os.environ.get("MAIL_PORT", 587))
    username = os.environ.get("MAIL_USERNAME")
    password = os.environ.get("MAIL_PASSWORD")
    recipient = os.environ.get("MAIL_RECIPIENT")

    if not username or not password or not recipient:
        print("\nℹ️ [Bonus Task 2 - Email Report] Email credentials not fully configured in environment/secrets.")
        print("   To enable email reporting, set MAIL_USERNAME, MAIL_PASSWORD, and MAIL_RECIPIENT.")
        return False

    print(f"\n📧 Sending email report to {recipient} via {server_host}:{port}...")

    subject = f"[{report['overall_status']}] CI Test Report - {report['repository']} (Run #{report['pipeline_run_id']})"
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = username
    msg["To"] = recipient

    # Build text body
    text_content = f"""COMSATS DevOps CI Test Report
----------------------------------------
Repository:  {report['repository']}
Branch:      {report['branch']}
Commit SHA:  {report['commit_sha']}
Run ID:      {report['pipeline_run_id']}
Timestamp:   {report['execution_timestamp']}
Status:      {report['overall_status']}
Total Tests: {report['total_tests']}
Passed:      {report['passed_tests']}
Failed:      {report['failed_tests']}

Individual Results:
"""
    for t in report["tests"]:
        text_content += f" - [{t['result']}] {t['name']}\n"
        if t["failure_message"]:
            text_content += f"   Error: {t['failure_message'].splitlines()[0]}\n"

    # Build HTML body
    status_color = "#28a745" if report['overall_status'] == "PASSED" else "#dc3545"
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #333;">
        <h2 style="color: #003366; border-bottom: 2px solid #c59b27; padding-bottom: 8px;">
          COMSATS DevOps Lab Mid &bull; Automated CI Test Report
        </h2>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 15px 0;">
          <p><strong>Repository:</strong> {report['repository']}</p>
          <p><strong>Branch:</strong> {report['branch']}</p>
          <p><strong>Commit SHA:</strong> <code>{report['commit_sha']}</code></p>
          <p><strong>Pipeline Run ID:</strong> {report['pipeline_run_id']}</p>
          <p><strong>Execution Time:</strong> {report['execution_timestamp']}</p>
          <p><strong>Overall Status:</strong> 
            <span style="color: white; background: {status_color}; padding: 4px 10px; border-radius: 4px; font-weight: bold;">
              {report['overall_status']}
            </span>
          </p>
          <p><strong>Test Counts:</strong> Total: {report['total_tests']} | Passed: {report['passed_tests']} | Failed: {report['failed_tests']}</p>
        </div>

        <h3>Individual Test Results:</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; max-width: 650px;">
          <thead style="background: #003366; color: white;">
            <tr>
              <th>Test Name</th>
              <th>Result</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
    """
    for t in report["tests"]:
        t_color = "#28a745" if t['result'] == "PASSED" else "#dc3545"
        html_content += f"""
            <tr>
              <td><code>{t['name']}</code></td>
              <td style="color: {t_color}; font-weight: bold;">{t['result']}</td>
              <td>{t['duration_seconds']}s</td>
            </tr>
        """
        if t["failure_message"]:
            html_content += f"""
            <tr>
              <td colspan="3" style="background: #fff5f5; color: #c53030; font-size: 12px; font-family: monospace;">
                <pre style="margin: 0;">{t['failure_message'][:500]}</pre>
              </td>
            </tr>
            """

    html_content += """
          </tbody>
        </table>
        <p style="margin-top: 20px; font-size: 12px; color: #777;">
          This email was generated automatically by the continuous integration pipeline.
        </p>
      </body>
    </html>
    """

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    # Also attach test-report.json file
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={REPORT_FILE}")
        msg.attach(part)

    try:
        with smtplib.SMTP(server_host, port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(username, password)
            server.sendmail(username, [recipient], msg.as_string())
        print(f"✅ Successfully sent email test report to {recipient}!")
        return True
    except Exception as e:
        print(f"⚠️ Failed to send email report: {e}")
        return False


def main():
    collector = PytestReportCollector()
    pytest_args = ["-v", "tests/test_submission.py"]

    print("=================================================================")
    print("▶️  EXECUTING AUTOMATED TEST SUITE")
    print("=================================================================")
    exit_code = pytest.main(pytest_args, plugins=[collector])

    # Build report object
    report = build_test_report(collector.reports, exit_code)

    # 1. Save locally
    save_report_locally(report)

    # 2. Send to HTTP receiver (localhost or tunnel)
    send_report_to_receiver(report)

    # 3. Bonus Task 2: Send email report if credentials are present
    send_email_report(report)

    print("\n=================================================================")
    print(f"🏁 RUN COMPLETED: {report['overall_status']} "
          f"({report['passed_tests']}/{report['total_tests']} tests passed)")
    print("=================================================================\n")

    # Enforce requirement: "A failed test must cause the test stage to fail."
    if report["failed_tests"] > 0 or exit_code != 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
