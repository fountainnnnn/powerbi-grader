from pathlib import Path

from fastapi.testclient import TestClient

from src.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STUDENT_NUMBERED_UPLOAD_PBIX = (
    PROJECT_ROOT / "api" / "uploads" / "368338fa-2119-4da2-83b0-3bd8fd66a750.pbix"
)


client = TestClient(app)


def test_vercel_prefixed_student_detection_route() -> None:
    with STUDENT_NUMBERED_UPLOAD_PBIX.open("rb") as handle:
        response = client.post(
            "/api/students",
            files={"file": ("sample.pbix", handle, "application/octet-stream")},
        )

    assert response.status_code == 200
    assert response.json() == {"students": ["Student 1", "Student 2"]}


def test_vercel_prefixed_stateless_grade_route(monkeypatch) -> None:
    def fake_grade_dashboard(**kwargs):
        assert kwargs["rubric_path"] is None
        assert kwargs["all_students"] == ["Student 1", "Student 2"]
        assert "Student 2" in kwargs["evidence_summary"]
        return {
            "text": "ok",
            "model": "test-model",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }

    monkeypatch.setattr(
        "src.services.chat_service.openai_client.grade_dashboard",
        fake_grade_dashboard,
    )

    with STUDENT_NUMBERED_UPLOAD_PBIX.open("rb") as handle:
        response = client.post(
            "/api/grade",
            data={"message": "Grade all students"},
            files={"pbix_file": ("sample.pbix", handle, "application/octet-stream")},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["ai_response"]["text"] == "ok"
    assert body["pbix_filename"] == "sample.pbix"
    assert body["dashboard_id"] is None
