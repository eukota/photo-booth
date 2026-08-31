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
