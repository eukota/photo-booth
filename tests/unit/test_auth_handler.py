import json
from src.lambdas.auth.handler import lambda_handler


def test_correct_password_returns_session(monkeypatch):
    monkeypatch.setenv("GALLERY_PASSWORD", "correct-horse")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    event = {"body": json.dumps({"password": "correct-horse"})}
    result = lambda_handler(event, None)
    assert result["statusCode"] == 200
    assert "session" in json.loads(result["body"])


def test_wrong_password_returns_401(monkeypatch):
    monkeypatch.setenv("GALLERY_PASSWORD", "correct-horse")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    event = {"body": json.dumps({"password": "wrong"})}
    result = lambda_handler(event, None)
    assert result["statusCode"] == 401
    assert "session" not in result["body"]
