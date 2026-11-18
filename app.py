import os
import json
import re
from datetime import datetime
from urllib.parse import urlparse
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")

# Persistent storage file (fallback to in-memory)
DATA_FILE = os.path.join(os.path.dirname(__file__), "submissions.json")

# In-memory storage seeded from DATA_FILE if it exists
def load_submissions():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_submissions_to_disk(submissions_list):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(submissions_list, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to persist submissions: {e}")

submissions = load_submissions()

def is_valid_url(url: str) -> bool:
    """Validate that the URL is a well-formed HTTP/HTTPS URL."""
    if not isinstance(url, str):
        return False
    url = url.strip()
    if not url:
        return False
    try:
        parsed = urlparse(url)
        # Scheme must be http or https
        if parsed.scheme.lower() not in ("http", "https"):
            return False
        # Netloc (host) must be present
        if not parsed.netloc or " " in url:
            return False
        # Basic host format check (hostname or IP)
        host = parsed.netloc.split(":")[0]
        if not host:
            return False
        return True
    except Exception:
        return False


def validate_submission(data: dict):
    """
    Validate submission input fields.
    Returns (is_valid, error_message, cleaned_data)
    """
    if not isinstance(data, dict):
        return False, "Invalid payload. Expected a JSON object.", None

    name = str(data.get("name", "")).strip()
    reg_no = str(data.get("reg_no", "")).strip()
    assignment_title = str(data.get("assignment_title", "")).strip()
    submission_url = str(data.get("submission_url", "")).strip()

    # 1. Validate required fields
    if not name:
        return False, "Student name is required.", None
    # DEFECT INTRODUCED FOR CI DEMONSTRATION:
    # if not reg_no:
    #     return False, "Registration number is required.", None
    if not assignment_title:
        return False, "Assignment title is required.", None
    if not submission_url:
        return False, "Submission URL is required.", None

    # 2. Validate URL format
    if not is_valid_url(submission_url):
        return False, "Invalid submission URL. Must be a valid HTTP or HTTPS URL (e.g., https://github.com/user/repo).", None

    cleaned = {
        "id": len(submissions) + 1,
        "name": name,
        "reg_no": reg_no,
        "assignment_title": assignment_title,
        "submission_url": submission_url,
        "submitted_at": datetime.now().isoformat()
    }
    return True, None, cleaned


@app.route("/")
def index():
    """Serve the static frontend."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/submissions", methods=["GET"])
def get_submissions():
    """Retrieve all saved submissions."""
    return jsonify({
        "success": True,
        "count": len(submissions),
        "submissions": submissions
    }), 200


@app.route("/api/submissions", methods=["POST"])
def create_submission():
    """
    Submit a new assignment.
    Validates name, reg_no, assignment_title, and submission_url.
    """
    data = request.get_json(silent=True)
    if data is None:
        # Also handle form-data if submitted via standard HTML form
        data = request.form.to_dict()

    is_valid, error_msg, cleaned = validate_submission(data)
    if not is_valid:
        return jsonify({
            "success": False,
            "error": error_msg
        }), 400

    submissions.append(cleaned)
    save_submissions_to_disk(submissions)

    return jsonify({
        "success": True,
        "message": "Assignment submission saved successfully.",
        "submission": cleaned
    }), 201


@app.route("/api/reset", methods=["POST"])
def reset_submissions():
    """Helper endpoint to reset submissions in test environments."""
    global submissions
    submissions = []
    if os.path.exists(DATA_FILE):
        try:
            os.remove(DATA_FILE)
        except OSError:
            pass
    return jsonify({"success": True, "message": "Submissions reset."}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Assignment Submission Portal on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
