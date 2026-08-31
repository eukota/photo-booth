import time
from src.common.session import create_session, verify_session


def test_valid_session_verifies():
    token = create_session(secret="test-secret")
    assert verify_session(token, secret="test-secret") is True


def test_session_with_wrong_secret_fails():
    token = create_session(secret="test-secret")
    assert verify_session(token, secret="wrong-secret") is False


def test_expired_session_fails():
    token = create_session(secret="test-secret", ttl_seconds=1)
    time.sleep(2)
    assert verify_session(token, secret="test-secret") is False
