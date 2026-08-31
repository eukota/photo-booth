import json
import boto3
import pytest
from moto import mock_aws
from src.common.session import create_session


@pytest.fixture
def bucket_with_photos(monkeypatch):
    monkeypatch.setenv("PHOTOS_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        s3.put_object(Bucket="test-bucket", Key="events/e1/pi-1/abc.jpg", Body=b"fake")
        s3.put_object(Bucket="test-bucket", Key="events/e1/pi-2/def.jpg", Body=b"fake")
        yield


def test_valid_session_lists_photos(bucket_with_photos):
    from src.lambdas.list_photos.handler import lambda_handler

    token = create_session(secret="test-secret")
    event = {"headers": {"authorization": f"Bearer {token}"}}
    result = lambda_handler(event, None)
    assert result["statusCode"] == 200
    photos = json.loads(result["body"])["photos"]
    assert len(photos) == 2
    assert all("url" in p and "key" in p for p in photos)


def test_missing_session_returns_401(bucket_with_photos):
    from src.lambdas.list_photos.handler import lambda_handler

    event = {"headers": {}}
    result = lambda_handler(event, None)
    assert result["statusCode"] == 401


def test_capitalized_header_casing_still_works(bucket_with_photos):
    """REST API v1 (unlike HTTP API v2) preserves header casing as sent."""
    from src.lambdas.list_photos.handler import lambda_handler

    token = create_session(secret="test-secret")
    event = {"headers": {"Authorization": f"Bearer {token}"}}
    result = lambda_handler(event, None)
    assert result["statusCode"] == 200


def test_presign_endpoint_override_changes_url_host(bucket_with_photos, monkeypatch):
    """PRESIGN_ENDPOINT_URL lets local dev serve URLs reachable from the
    host browser, distinct from the (internal-only) endpoint used for the
    real list_objects_v2 call."""
    monkeypatch.setenv("PRESIGN_ENDPOINT_URL", "http://localhost:4566")
    from src.lambdas.list_photos.handler import lambda_handler

    token = create_session(secret="test-secret")
    event = {"headers": {"authorization": f"Bearer {token}"}}
    result = lambda_handler(event, None)
    photos = json.loads(result["body"])["photos"]
    assert all(p["url"].startswith("http://localhost:4566/") for p in photos)
