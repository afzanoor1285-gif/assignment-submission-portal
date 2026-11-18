# Assignment Submission Portal & DevOps CI/CD Pipeline

**Course:** CSC418 - DevOps for Cloud Computing  
**Institution:** COMSATS University Islamabad, Attock Campus  
**Instructor:** Mr. Babar Shazad  
**Assessment:** DevOps Lab Mid Examination (Core Marks: 40 + Bonus: 10)  

---

## 📌 Executive Summary

This repository implements a production-grade, end-to-end automated DevOps workflow for a department **Assignment Submission Portal**. It prevents code regressions by enforcing automated test execution on every Git revision, dispatches comprehensive test reports directly to a local receiver on the instructor/developer's workstation in real time, publishes a live interactive demo to **GitHub Pages** conditionally upon green builds, and alerts stakeholders via **automated email reports**.

---

## 🏗️ Architecture & Pipeline Flow

```
[ Developer / Student Workstation ]
        │
        ├── 1. Code Commit & Push ─────────────► [ GitHub Remote Repository ]
        │                                                     │
        │                                                     ▼
        │                                          [ GitHub Actions CI Pipeline ]
        │                                                     │
        │                                           ┌─────────┴─────────┐
        │                                           ▼                   ▼
        │                                    [ Test Stage ]      [ Failure ? ]
        │                                           │                   │
        │                                    Pytest Execution     Exit Code 1
        │                                           │                   │
        │                                    Generate JSON              │
        │                                           │                   │
        │                      ┌────────────────────┼───────────────────┤
        │                      ▼                    ▼                   ▼
        │            [ HTTP POST Dispatch ]  [ Email Dispatch ]  [ Upload Artifact ]
        │                      │                    │                   │
        │         Tunnel / Relay / Localhost   SMTP Server         test-report.json
        │                      │                    │
        ▼                      ▼                    ▼
[ Local Receiver (receiver.py) ]             [ Student/Instructor Inbox ]
        │
   Writes test-report.json locally
        │
        ▼ (Only If All Tests Pass on 'main')
[ GitHub Pages Conditional Deployment ] ──► Live Web Demo
```

---

## 📂 Repository Structure

```
assignment-submission-portal/
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI/CD pipeline definition
├── docs/                      # Static frontend build deployed to GitHub Pages
│   ├── index.html
│   ├── style.css
│   └── app.js
├── static/                    # Application frontend assets
│   ├── index.html             # COMSATS-branded responsive UI
│   ├── style.css              # Custom styling
│   └── app.js                 # Dynamic client-side logic & demo fallback
├── tests/
│   ├── __init__.py
│   └── test_submission.py     # Automated test suite (all 3 required test cases)
├── app.py                     # Flask web server & REST API
├── receiver.py                # Local HTTP test report receiver (saves test-report.json)
├── test_runner.py             # Custom runner: tests + report generator + dispatchers
├── simulate_workflow.py       # Automated 3-stage demonstration script (Pass -> Fail -> Fix)
├── requirements.txt           # Python dependencies (flask, pytest, requests)
├── test-report.json           # Real-time local JSON test report output
└── README.md                  # Comprehensive documentation and setup guide
```

---

## ⚙️ Prerequisites & Setup

Ensure Python 3.10+ and Git are installed on your workstation.

### 1. Clone Repository & Install Dependencies
```bash
git clone <YOUR_GITHUB_REPO_URL>
cd assignment-submission-portal

# (Optional) Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Running the Components

### Component 1: Start the Web Application
```bash
python app.py
```
- Open your browser at: `http://localhost:5000`
- The portal allows students to submit:
  - **Student Name** (Required)
  - **Registration Number** (Required)
  - **Assignment Title** (Required)
  - **Submission URL** (Required; must be a valid HTTP or HTTPS URL)
- Submissions are validated, stored, and displayed in the real-time table.

---

### Component 2: Start the Local Report Receiver (Requirement 4)
Open a separate terminal window and run:
```bash
python receiver.py
```
- Listens on `http://localhost:5050/report` (customizable via `PORT` environment variable).
- Receives the test report via HTTP POST from the CI pipeline (or local test runner).
- Automatically writes/updates **`test-report.json`** in your repository directory.
- Pretty-prints incoming test details, pass/fail counts, and failure logs directly to your console.

---

### Component 3: Execute Automated Tests Locally
To run pytest directly:
```bash
pytest -v
```

To run via the automated reporter (which runs pytest, compiles the JSON report, saves it, and dispatches it to `receiver.py` and email):
```bash
python test_runner.py
```

---

## 🌐 Connecting GitHub Actions to Localhost (Requirement 4)

GitHub-hosted runners execute in GitHub's cloud environment. To route reports from the cloud runner to your local `receiver.py`, use one of the following methods:

### Method A: Cloud Tunnel (Recommended - ngrok or Pinggy)
1. Start your local receiver:
   ```bash
   python receiver.py
   ```
2. In another terminal, start a tunnel to port `5050`:
   - **Using ngrok:**
     ```bash
     ngrok http 5050
     ```
     Copy the public forwarding URL (e.g. `https://a1b2-c3d4.ngrok-free.app`).
   - **Or using Pinggy (zero install):**
     ```bash
     ssh -p 443 -R0:localhost:5050 a.pinggy.io
     ```
3. Set the GitHub Repository Secret:
   - Go to your repository on GitHub: **Settings** ➔ **Secrets and variables** ➔ **Actions**.
   - Click **New repository secret**.
   - **Name:** `RECEIVER_URL`
   - **Value:** `https://<YOUR_TUNNEL_URL>/report` (e.g., `https://a1b2-c3d4.ngrok-free.app/report`)
4. On every push, GitHub Actions will POST the test report across the tunnel directly to your local computer's `receiver.py`, updating `test-report.json`!

### Method B: Self-Hosted Runner
If you register a GitHub self-hosted runner directly on your machine, `localhost` resolves directly to your computer. The pipeline automatically sends reports to `http://localhost:5050/report` without needing a tunnel.

---

## 🧪 Automated Test Cases (Requirement 3)

The test suite in [`tests/test_submission.py`](file:///C:/Users/hh/.gemini/antigravity/scratch/assignment-submission-portal/tests/test_submission.py) implements the required test cases:

| Test Case | Description | Input Condition | Expected Result |
| :--- | :--- | :--- | :--- |
| **Test Case 1** | Complete details & valid submission URL | Valid name, reg number, title, and valid URL | HTTP 201 Created. Submission saved & appears in `/api/submissions`. |
| **Test Case 2** | Missing registration number | All fields provided, but `reg_no` is empty | HTTP 400 Bad Request. Rejected with error message; submission not saved. |
| **Test Case 3** | Invalid submission URL | Malformed URL string (e.g. `not-a-url`) | HTTP 400 Bad Request. Rejected with URL validation message; submission not saved. |

---

## 📊 Test Report Schema (`test-report.json`)

The generated `test-report.json` satisfies all items specified in Requirement 4:
```json
{
  "repository": "afzanoor344/assignment-submission-portal",
  "branch": "main",
  "commit_sha": "7f8b91a2c3d4e5f6...",
  "pipeline_run_id": "1849203921",
  "execution_timestamp": "2026-10-26T14:32:00.123456+00:00",
  "overall_status": "PASSED",
  "total_tests": 5,
  "passed_tests": 5,
  "failed_tests": 0,
  "tests": [
    {
      "name": "test_complete_details_and_valid_url",
      "full_id": "tests/test_submission.py::test_complete_details_and_valid_url",
      "result": "PASSED",
      "duration_seconds": 0.0018,
      "failure_message": null
    },
    {
      "name": "test_missing_registration_number",
      "full_id": "tests/test_submission.py::test_missing_registration_number",
      "result": "PASSED",
      "duration_seconds": 0.0011,
      "failure_message": null
    },
    {
      "name": "test_invalid_submission_url",
      "full_id": "tests/test_submission.py::test_invalid_submission_url",
      "result": "PASSED",
      "duration_seconds": 0.001,
      "failure_message": null
    }
  ]
}
```

---

## 🎬 Demonstrating the Complete Workflow (Requirement 5)

Requirement 5 requires demonstrating:
1. A push that passes all tests.
2. Introducing a defect and pushing to produce a failing test and an updated failing local JSON report.
3. Fixing the defect and demonstrating a passing run.

### Option 1: One-Click Local Simulation
Run the included workflow simulator:
```bash
python simulate_workflow.py
```
This automatically runs all 3 stages, introduces the defect in `app.py`, executes tests, shows the receiver receiving the failure, verifies `test-report.json`, fixes `app.py`, and proves the passing state.

### Option 2: Live GitHub Push Demonstration

#### Step 1: Push Initial Passing Code
```bash
git add .
git commit -m "feat: complete assignment portal with CI test suite"
git push origin main
```
- **Result:** GitHub Actions tests pass (Green ✅).
- **Local:** `receiver.py` receives the report; `test-report.json` updates to `"overall_status": "PASSED"`.
- **Bonus 1:** Portal deploys to GitHub Pages.

#### Step 2: Introduce Defect
Open `app.py` and comment out the registration number validation:
```python
# if not reg_no:
#     return False, "Registration number is required.", None
```
Commit and push:
```bash
git add app.py
git commit -m "test: introduce defect by removing registration number check"
git push origin main
```
- **Result:** Pipeline fails at `test_missing_registration_number` (Red ❌).
- **Local:** `receiver.py` immediately receives the failing report; `test-report.json` shows `"overall_status": "FAILED"`, `failed_tests: 1`, and the exact stack trace.
- **Bonus 1:** GitHub Pages deployment is SKIPPED; existing deployment remains unchanged.

#### Step 3: Fix Defect
Uncomment the validation in `app.py`:
```python
if not reg_no:
    return False, "Registration number is required.", None
```
Commit and push:
```bash
git add app.py
git commit -m "fix: restore registration number validation"
git push origin main
```
- **Result:** Pipeline turns Green ✅.
- **Local:** `test-report.json` updates back to `"overall_status": "PASSED"`, `failed_tests: 0`.

---

## 🎁 Bonus Tasks Implementation

### 1. Conditional GitHub Pages Deployment (+5 Marks)
- Defined in `.github/workflows/ci.yml`:
  ```yaml
  deploy-pages:
    needs: test
    if: (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master') && success()
  ```
- **Guarantee:** If tests fail in the `test` job, the `deploy-pages` job is skipped. The previous deployed live site remains completely intact.
- **Frontend Fallback:** The static frontend in `docs/` detects standalone hosting on GitHub Pages and runs interactive demo mode using browser storage (`localStorage`), allowing full evaluation directly in the browser!
- **Live Deployed URL:** `https://<YOUR-USERNAME>.github.io/<YOUR-REPO-NAME>/`

### 2. Automated Email Test Report (+5 Marks)
- Implemented in `test_runner.py` using standard secure SMTP (TLS).
- Automatically formats an HTML & text report with pass/fail badges, test breakdowns, and attaches `test-report.json`.
- Dispatches on **both passing and failing test runs**.
- **Configure Secrets in GitHub Repository Settings:**
  - `MAIL_SERVER`: e.g., `smtp.gmail.com`
  - `MAIL_PORT`: `587`
  - `MAIL_USERNAME`: your SMTP email (e.g. `your-email@gmail.com`)
  - `MAIL_PASSWORD`: your SMTP App Password
  - `MAIL_RECIPIENT`: instructor / evaluation email address

---

## 📝 Submission Checklist

- [x] **Repository URL:** Public GitHub repository containing all source, tests, workflows, receiver, and README.
- [x] **Portal Core Functions:** Name, reg number, assignment title, URL input, validation, storage, and display table.
- [x] **Automated Tests:** 3 required test cases (valid submission, missing reg number, invalid URL) + edge cases.
- [x] **Local HTTP Receiver:** Python receiver listening on port 5050 writing `test-report.json`.
- [x] **Report Contents:** Repo name, branch, commit SHA, run ID, timestamp, individual test results/failures, total/passed/failed counts, overall status.
- [x] **Delivery for Both Passing & Failing:** Guaranteed delivery in both passing and defect scenarios.
- [x] **Bonus 1:** Conditional deployment to GitHub Pages on passing `main` push.
- [x] **Bonus 2:** Configurable automated email delivery of test reports.
