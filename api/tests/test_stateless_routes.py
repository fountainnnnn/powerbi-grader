from fastapi.testclient import TestClient

from src.config import settings
from src.main import app

client = TestClient(app)


def auth_headers(monkeypatch) -> dict[str, str]:
    monkeypatch.setattr(settings, "app_login_username", "teacher")
    monkeypatch.setattr(settings, "app_login_password", "strict")

    response = client.post(
        "/api/auth/login",
        json={"username": "teacher", "password": "strict"},
    )

    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def sample_inspection() -> dict:
    return {
        "file_name": "sample.pbix",
        "pages": [
            {
                "display_name": "Dashboard",
                "visuals": [
                    {
                        "visual_type": "lineChart",
                        "fields": [],
                        "text_content": [{"text": "Trend by Year (Student 1)"}],
                    },
                    {
                        "visual_type": "treemap",
                        "fields": [],
                        "text_content": [{"text": "Highest Qualification {Student 2}"}],
                    },
                ],
            },
            {
                "display_name": "Individual Insights",
                "visuals": [
                    {
                        "visual_type": "textbox",
                        "fields": [],
                        "text_content": [
                            {"text": "[Student 1]: Insight with enough detail."},
                            {"text": "[Student 2]: Insight with enough detail."},
                        ],
                    }
                ],
            },
        ],
    }


def test_vercel_prefixed_student_detection_requires_auth() -> None:
    response = client.post(
        "/api/students",
        files={"file": ("sample.pbix", b"not-a-real-pbix", "application/octet-stream")},
    )

    assert response.status_code == 401


def test_vercel_prefixed_student_detection_route(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.routes.stateless.pbix_inspector.inspect",
        lambda _: sample_inspection(),
    )

    response = client.post(
        "/api/students",
        headers=auth_headers(monkeypatch),
        files={"file": ("sample.pbix", b"not-a-real-pbix", "application/octet-stream")},
    )

    assert response.status_code == 200
    assert response.json() == {"students": ["Student 1", "Student 2"]}


def test_vercel_prefixed_stateless_grade_route(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.services.chat_service.pbix_inspector.inspect",
        lambda _: sample_inspection(),
    )

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

    response = client.post(
        "/api/grade",
        headers=auth_headers(monkeypatch),
        data={"message": "Grade all students"},
        files={"pbix_file": ("sample.pbix", b"not-a-real-pbix", "application/octet-stream")},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["ai_response"]["text"] == "ok"
    assert body["pbix_filename"] == "sample.pbix"
    assert body["dashboard_id"] is None
