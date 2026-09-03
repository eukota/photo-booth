import boto3
import pytest
from moto import mock_aws
from src.lambdas.redirect_photo.handler import lambda_handler


@pytest.fixture
def bucket_with_photo(monkeypatch):
    monkeypatch.setenv("PHOTOS_BUCKET_NAME", "test-bucket")
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        s3.put_object(Bucket="test-bucket", Key="events/e1/pi-1/abc.jpg", Body=b"fake")
        yield


def test_valid_key_redirects_to_presigned_url(bucket_with_photo):
    event = {"pathParameters": {"proxy": "events/e1/pi-1/abc.jpg"}}
    result = lambda_handler(event, None)
    assert result["statusCode"] == 302
    assert "abc.jpg" in result["headers"]["Location"]
    assert "test-bucket" in result["headers"]["Location"]


def test_missing_key_returns_400(bucket_with_photo):
    event = {"pathParameters": {}}
    result = lambda_handler(event, None)
    assert result["statusCode"] == 400


def test_no_path_parameters_returns_400(bucket_with_photo):
    event = {}
    result = lambda_handler(event, None)
    assert result["statusCode"] == 400


def test_presign_endpoint_override_changes_url_host(bucket_with_photo, monkeypatch):
    monkeypatch.setenv("PRESIGN_ENDPOINT_URL", "http://localhost:4566")
    event = {"pathParameters": {"proxy": "events/e1/pi-1/abc.jpg"}}
    result = lambda_handler(event, None)
    assert result["headers"]["Location"].startswith("http://localhost:4566/")
