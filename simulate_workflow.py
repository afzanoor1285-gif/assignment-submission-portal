import os
import sys
import time
import json
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_FILE = os.path.join(PROJECT_DIR, "app.py")
REPORT_FILE = os.path.join(PROJECT_DIR, "test-report.json")

def print_banner(text):
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)

def read_current_report():
    if os.path.exists(REPORT_FILE):
        try:
            with open(REPORT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def display_report_snapshot(title):
    rep = read_current_report()
    if not rep:
        print("  [No test-report.json found yet]")
        return
    status = rep.get("overall_status", "UNKNOWN")
    mark = "✅" if status == "PASSED" else "❌"
    print(f"\n📄 [SNAPSHOT: {title}]")
    print(f"   Status      : {mark} {status}")
    print(f"   Total Tests : {rep.get('total_tests')}")
    print(f"   Passed      : {rep.get('passed_tests')}")
    print(f"   Failed      : {rep.get('failed_tests')}")
    print(f"   Timestamp   : {rep.get('execution_timestamp')}")
    if rep.get("failed_tests", 0) > 0:
        print("   Failures:")
        for t in rep.get("tests", []):
            if t.get("result") == "FAILED":
                print(f"     - {t.get('name')}: {t.get('failure_message', '')[:120]}...")

def run_tests():
    proc = subprocess.run([sys.executable, "test_runner.py"], cwd=PROJECT_DIR, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr

def main():
    auto_mode = "--auto" in sys.argv or "--non-interactive" in sys.argv
    def pause(prompt_text):
        if not auto_mode:
            input(prompt_text)
        else:
            print(f"[Auto Mode] {prompt_text}")

    print_banner("DEMONSTRATION SIMULATOR: DevOps Lab Mid Workflow (CSC418)")
    print("This script simulates the complete 3-stage workflow required by Section 5:")
    print(" 1. Initial Passing Run")
    print(" 2. Defect Introduced -> Pipeline Fails -> Local Report Automatically Updates to FAILED")
    print(" 3. Defect Fixed -> Pipeline Passes -> Local Report Automatically Updates to PASSED\n")

    pause("Press ENTER to start Step 1 (Passing Run)... ")

    # -------------------------------------------------------------
    # Step 1: Passing Run
    # -------------------------------------------------------------
    print_banner("STEP 1: Executing Initial Passing Test Run")
    code, out, err = run_tests()
    print(out)
    if code == 0:
        print("✅ Step 1 Successful: All tests passed!")
    else:
        print("❌ Unexpected failure in Step 1.")
    display_report_snapshot("After Step 1 (Passing)")

    time.sleep(1)
    pause("\nPress ENTER to start Step 2 (Introduce Defect & Run)... ")

    # -------------------------------------------------------------
    # Step 2: Introduce Defect (Break Registration Number Validation)
    # -------------------------------------------------------------
    print_banner("STEP 2: Introducing Defect into app.py (Bypass Registration Number Check)")
    with open(APP_FILE, "r", encoding="utf-8") as f:
        original_code = f.read()

    # Defect: Comment out registration number validation
    defect_target = 'if not reg_no:\n        return False, "Registration number is required.", None'
    defect_replacement = '# DEFECT INTRODUCED FOR DEMONSTRATION:\n    # if not reg_no:\n    #     return False, "Registration number is required.", None\n    pass'

    if defect_target not in original_code:
        print("⚠️ Could not find exact validation target string in app.py")
        return

    broken_code = original_code.replace(defect_target, defect_replacement, 1)
    with open(APP_FILE, "w", encoding="utf-8") as f:
        f.write(broken_code)

    print("⚠️ Defect introduced: app.py now accepts missing registration numbers!")
    print("Running test suite (expecting failure)...")

    code, out, err = run_tests()
    print(out)
    if code != 0:
        print("✅ Step 2 Successful: Test runner properly failed with non-zero exit code!")
    else:
        print("❌ Error: Test runner was supposed to fail, but returned 0.")
    display_report_snapshot("After Step 2 (Defect / FAILED)")

    time.sleep(1)
    pause("\nPress ENTER to start Step 3 (Fix Defect & Re-run)... ")

    # -------------------------------------------------------------
    # Step 3: Fix Defect
    # -------------------------------------------------------------
    print_banner("STEP 3: Fixing Defect in app.py (Restoring Registration Number Check)")
    with open(APP_FILE, "w", encoding="utf-8") as f:
        f.write(original_code)

    print("🔧 Defect fixed: app.py restored to full working state.")
    print("Running test suite (expecting pass)...")

    code, out, err = run_tests()
    print(out)
    if code == 0:
        print("✅ Step 3 Successful: Tests passed and pipeline restored to green!")
    else:
        print("❌ Unexpected failure in Step 3.")
    display_report_snapshot("After Step 3 (Fixed / PASSED)")

    print_banner("WORKFLOW SIMULATION COMPLETED SUCCESSFULLY!")
    print("Both passing and failing test runs generated real-time local test-report.json files.")

if __name__ == "__main__":
    main()
