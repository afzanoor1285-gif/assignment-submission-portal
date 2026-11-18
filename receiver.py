import os
import json
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

DEFAULT_PORT = 5050
REPORT_FILENAME = "test-report.json"

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
            except Exception as e:
                pass

        self._set_headers(200)
        self.wfile.write(json.dumps({
            "status": "active",
            "message": "Local Test Report Receiver is running. Waiting for POST /report",
            "listening_port": self.server.server_port,
            "save_target": os.path.abspath(REPORT_FILENAME)
        }, indent=2).encode("utf-8"))

    def do_POST(self):
        """Receive test report JSON and save to test-report.json."""
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

        # Save to disk as test-report.json
        filepath = os.path.abspath(REPORT_FILENAME)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": f"Failed to save file: {e}"}).encode("utf-8"))
            return

        # Print human-readable summary to console
        self._log_report(report_data, filepath)
        sys.stdout.flush()

        # Respond to caller
        self._set_headers(200)
        response = {
            "status": "success",
            "message": "Test report received and saved successfully.",
            "saved_as": filepath,
            "overall_status": report_data.get("overall_status", "UNKNOWN")
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def _log_report(self, report, filepath):
        print("\n" + "=" * 65)
        print("📥  NEW TEST REPORT RECEIVED FROM CI PIPELINE")
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
                # Indent failure message
                indented = "\n".join("        " + line for line in t.get("failure_message").splitlines()[:5])
                print(f"      Reason:\n{indented}")
        print("-" * 65)
        print(f"💾 Report saved to: {filepath}")
        print("=" * 65 + "\n")

    def log_message(self, format, *args):
        # Suppress default noisy HTTP request logs
        return


def run_receiver(port=DEFAULT_PORT):
    server_address = ("", port)
    httpd = HTTPServer(server_address, TestReportReceiver)
    print("\n" + "#" * 65)
    print(f"🚀 LOCAL TEST REPORT RECEIVER RUNNING ON PORT {port}")
    print(f"   URL: http://localhost:{port}/report")
    print(f"   Output target: {os.path.abspath(REPORT_FILENAME)}")
    print("   Ready to accept test reports from CI / forwarding tunnel...")
    print("#" * 65 + "\n", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nReceiver stopped by user.")
        httpd.server_close()


if __name__ == "__main__":
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    elif "PORT" in os.environ:
        try:
            port = int(os.environ["PORT"])
        except ValueError:
            pass
    run_receiver(port)
