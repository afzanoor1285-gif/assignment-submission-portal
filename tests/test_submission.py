import pytest
from app import app, submissions

@pytest.fixture(autouse=True)
def client():
    """Create a test client and reset submissions before each test."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        # Reset submissions list
        client.post("/api/reset")
        yield client
        # Clean up after test
        client.post("/api/reset")


def test_complete_details_and_valid_url(client):
    """
    Test Case 1: Complete details and a valid submission URL
    Expected: The submission is saved and appears in the submission list.
    """
    payload = {
        "name": "Muhammad Ali",
        "reg_no": "SP21-BCS-045",
        "assignment_title": "DevOps Assignment 1 - CI/CD Pipeline",
        "submission_url": "https://github.com/ali/devops-lab"
    }
    
    # 1. Send submission
    response = client.post("/api/submissions", json=payload)
    assert response.status_code == 201, f"Expected 201 Created, got {response.status_code}: {response.data}"
    data = response.get_json()
    assert data["success"] is True
    assert "submission" in data
    assert data["submission"]["name"] == "Muhammad Ali"
    assert data["submission"]["reg_no"] == "SP21-BCS-045"
    assert data["submission"]["submission_url"] == "https://github.com/ali/devops-lab"

    # 2. Verify submission appears in the submission list
    get_res = client.get("/api/submissions")
    assert get_res.status_code == 200
    list_data = get_res.get_json()
    assert list_data["count"] == 1
    saved_items = list_data["submissions"]
    assert len(saved_items) == 1
    assert saved_items[0]["reg_no"] == "SP21-BCS-045"
    assert saved_items[0]["submission_url"] == "https://github.com/ali/devops-lab"


def test_missing_registration_number(client):
    """
    Test Case 2: Missing registration number
    Expected: The submission is rejected with a validation message.
    """
    payload = {
        "name": "Muhammad Ali",
        "reg_no": "",  # missing / empty registration number
        "assignment_title": "DevOps Assignment 1 - CI/CD Pipeline",
        "submission_url": "https://github.com/ali/devops-lab"
    }
    
    response = client.post("/api/submissions", json=payload)
    assert response.status_code == 400, f"Expected 400 Bad Request, got {response.status_code}"
    data = response.get_json()
    assert data["success"] is False
    assert "Registration number is required" in data["error"]

    # Verify not saved in submissions
    get_res = client.get("/api/submissions")
    assert get_res.get_json()["count"] == 0


def test_invalid_submission_url(client):
    """
    Test Case 3: Invalid submission URL
    Expected: The submission is rejected and is not saved.
    """
    payload = {
        "name": "Muhammad Ali",
        "reg_no": "SP21-BCS-045",
        "assignment_title": "DevOps Assignment 1 - CI/CD Pipeline",
        "submission_url": "invalid-url-without-protocol"
    }
    
    response = client.post("/api/submissions", json=payload)
    assert response.status_code == 400, f"Expected 400 Bad Request, got {response.status_code}"
    data = response.get_json()
    assert data["success"] is False
    assert "Invalid submission URL" in data["error"]

    # Verify submission is NOT saved
    get_res = client.get("/api/submissions")
    assert get_res.get_json()["count"] == 0


def test_missing_student_name(client):
    """Supplementary test: Missing student name."""
    payload = {
        "name": "",
        "reg_no": "SP21-BCS-045",
        "assignment_title": "DevOps Assignment 1",
        "submission_url": "https://github.com/ali/devops-lab"
    }
    response = client.post("/api/submissions", json=payload)
    assert response.status_code == 400
    assert "Student name is required" in response.get_json()["error"]


def test_missing_assignment_title(client):
    """Supplementary test: Missing assignment title."""
    payload = {
        "name": "Muhammad Ali",
        "reg_no": "SP21-BCS-045",
        "assignment_title": "",
        "submission_url": "https://github.com/ali/devops-lab"
    }
    response = client.post("/api/submissions", json=payload)
    assert response.status_code == 400
    assert "Assignment title is required" in response.get_json()["error"]
