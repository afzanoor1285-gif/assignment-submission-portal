import os
import json
import sys
import time
import io
import zipfile
import threading
import urllib.request
import urllib.error
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

DEFAULT_PORT = 5050
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_FILENAME = os.path.join(SCRIPT_DIR, "test-report.json")
DEFAULT_REPO = os.environ.get("GITHUB_REPOSITORY", "afzanoor1285-gif/assignment-submission-portal")
def get_github_token():
    """Retrieve GitHub token from environment variable or git credential manager."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    try:
        import subprocess
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            timeout=3
        )
        for line in proc.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""

GITHUB_TOKEN = get_github_token()

# Track processed run IDs to avoid duplicates
_processed_run_ids = set()
_lock = threading.Lock()


def format_and_log_report(report, filepath, source="HTTP DISPATCH"):
    """Formatted summary printer for test reports."""
    print("\n" + "=" * 65)
    print(f"📥  NEW TEST REPORT RECEIVED VIA {source}")
    print("=" * 65)
    print(f"  Repository : {report.get('repository', 'N/A')}")
    print(f"  Branch     : {report.get('branch', 'N/A')}")
    print(f"  Commit SHA : {report.get('commit_sha', 'N/A')}")
    print(f"  Run ID     : {report.get('pipeline_run_id', 'N/A')}")
    print(f"  Timestamp  : {report.get('execution_timestamp', 'N/A')}")

    status = report.get("overall_status", "UNKNOWN")
    status_marker = "✅ PASSED" if status == "PASSED" else "❌ FAILED"
    print(f"  Status     : {status_marker}")
    print(f"  Counts     : Total: {report.get('total_tests', 0)} | "
          f"Passed: {report.get('passed_tests', 0)} | "
          f"Failed: {report.get('failed_tests', 0)}")
    print("-" * 65)
    print("  Individual Tests:")
    for t in report.get("tests", []):
        mark = "✓" if t.get("result") == "PASSED" else "✗"
        print(f"    [{mark}] {t.get('name')}: {t.get('result')}")
        if t.get("failure_message"):
            lines = t.get("failure_message").splitlines()[:6]
            indented = "\n".join("        " + line for line in lines)
            print(f"      Reason:\n{indented}")
    print("-" * 65)
    print(f"💾 Report saved to: {filepath}")
    print("=" * 65 + "\n", flush=True)


def save_report_data(report_data, source="HTTP POST"):
    """Thread-safe save of report to test-report.json and console print."""
    with _lock:
        filepath = os.path.abspath(REPORT_FILENAME)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        format_and_log_report(report_data, filepath, source=source)
        return filepath


class TestReportReceiver(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        """Health check and view current saved report."""
        if os.path.exists(REPORT_FILENAME):
            try:
                with open(REPORT_FILENAME, "r", encoding="utf-8") as f:
                    content = json.load(f)
                self._set_headers(200)
                self.wfile.write(json.dumps({
                    "status": "active",
                    "saved_file": os.path.abspath(REPORT_FILENAME),
                    "last_report": content
                }, indent=2).encode("utf-8"))
                return
            except Exception:
                pass

        self._set_headers(200)
        self.wfile.write(json.dumps({
            "status": "active",
            "message": "Local Test Report Receiver is running. Waiting for POST /report or CI sync",
            "listening_port": self.server.server_port,
            "save_target": os.path.abspath(REPORT_FILENAME)
        }, indent=2).encode("utf-8"))

    def do_POST(self):
        """Receive test report JSON directly and save to test-report.json."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Empty request body"}).encode("utf-8"))
            return

        post_data = self.rfile.read(content_length)
        try:
            report_data = json.loads(post_data.decode("utf-8"))
        except json.JSONDecodeError as err:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": f"Invalid JSON: {err}"}).encode("utf-8"))
            return

        filepath = save_report_data(report_data, source="DIRECT HTTP POST")

        self._set_headers(200)
        response = {
            "status": "success",
            "message": "Test report received and saved successfully.",
            "saved_as": filepath,
            "overall_status": report_data.get("overall_status", "UNKNOWN")
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress default HTTP server noise
        return


class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
    """Strip Authorization header when following redirects to AWS S3 storage."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req and "Authorization" in new_req.headers:
            del new_req.headers["Authorization"]
        return new_req


def github_ci_watcher(repo=DEFAULT_REPO, token=GITHUB_TOKEN, poll_interval=5):
    """
    Background watcher that monitors GitHub Actions runs.
    Automatically fetches completed test-report.json artifacts and saves them locally,
    guaranteeing automated delivery on both passing and failing runs.
    """
    if not token:
        return

    opener = urllib.request.build_opener(NoAuthRedirect)
    runs_url = f"https://api.github.com/repos/{repo}/actions/runs?per_page=5"

    while True:
        try:
            req = urllib.request.Request(runs_url, headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "DevOpsLabReceiver"
            })
            with opener.open(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            for run in data.get("workflow_runs", []):
                run_id = run["id"]
                run_status = run.get("status")
                
                # Check completed runs not yet processed
                if run_status == "completed" and run_id not in _processed_run_ids:
                    artifacts_url = run.get("artifacts_url")
                    if not artifacts_url:
                        continue

                    art_req = urllib.request.Request(artifacts_url, headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                        "User-Agent": "DevOpsLabReceiver"
                    })
                    with opener.open(art_req, timeout=10) as art_resp:
                        art_data = json.loads(art_resp.read().decode("utf-8"))

                    for art in art_data.get("artifacts", []):
                        if art.get("name") == "test-report-json":
                            download_url = art.get("archive_download_url")
                            down_req = urllib.request.Request(download_url, headers={
                                "Authorization": f"Bearer {token}",
                                "Accept": "application/vnd.github+json",
                                "User-Agent": "DevOpsLabReceiver"
                            })
                            with opener.open(down_req, timeout=15) as dl_resp:
                                zip_bytes = dl_resp.read()

                            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                                if REPORT_FILENAME in z.namelist():
                                    report_json = json.loads(z.read(REPORT_FILENAME).decode("utf-8"))
                                    save_report_data(report_json, source=f"GITHUB ACTIONS (Run #{run_id})")
                                    _processed_run_ids.add(run_id)
                                    break
                    _processed_run_ids.add(run_id)

        except Exception as e:
            # Silently retry on network hiccups
            pass

        time.sleep(poll_interval)


def run_receiver(port=DEFAULT_PORT, enable_ci_watcher=True):
    # Seed processed runs initially so we only catch new runs going forward
    if enable_ci_watcher and GITHUB_TOKEN:
        try:
            opener = urllib.request.build_opener(NoAuthRedirect)
            init_req = urllib.request.Request(
                f"https://api.github.com/repos/{DEFAULT_REPO}/actions/runs?per_page=5",
                headers={
                    "Authorization": f"Bearer {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "DevOpsLabReceiver"
                }
            )
            with opener.open(init_req, timeout=8) as r:
                d = json.loads(r.read().decode("utf-8"))
                for run in d.get("workflow_runs", []):
                    _processed_run_ids.add(run["id"])
        except Exception:
            pass

        watcher_thread = threading.Thread(
            target=github_ci_watcher,
            args=(DEFAULT_REPO, GITHUB_TOKEN, 4),
            daemon=True
        )
        watcher_thread.start()

    server_address = ("", port)
    httpd = HTTPServer(server_address, TestReportReceiver)
    print("\n" + "#" * 65)
    print(f"🚀 LOCAL TEST REPORT RECEIVER RUNNING ON PORT {port}")
    print(f"   URL: http://localhost:{port}/report")
    print(f"   Output target: {os.path.abspath(REPORT_FILENAME)}")
    if enable_ci_watcher and GITHUB_TOKEN:
        print(f"   CI Watcher   : Active (Monitoring {DEFAULT_REPO})")
    print("   Ready to accept test reports from CI / forwarding tunnel / local runner...")
    print("#" * 65 + "\n", flush=True)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nReceiver stopped by user.")
        httpd.server_close()


if __name__ == "__main__":
    port = DEFAULT_PORT
    watch = True
    for arg in sys.argv[1:]:
        if arg == "--no-watch":
            watch = False
        elif arg.isdigit():
            port = int(arg)
    if "PORT" in os.environ and port == DEFAULT_PORT:
        try:
            port = int(os.environ["PORT"])
        except ValueError:
            pass
    run_receiver(port=port, enable_ci_watcher=watch)
