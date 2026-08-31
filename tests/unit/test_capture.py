import boto3
import pytest
from moto import mock_aws
from pi.capture import capture_and_upload


def fake_capture_ok():
    return b"fake-jpeg-bytes"


def fake_capture_fails():
    raise RuntimeError("webcam not found")


@mock_aws
def test_successful_capture_uploads_with_correct_key_structure():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-bucket")

    key = capture_and_upload(
        bucket="test-bucket",
        event_id="e1",
        device_id="pi-7",
        capture_fn=fake_capture_ok,
        s3_client=s3,
    )

    assert key.startswith("events/e1/pi-7/")
    assert key.endswith(".jpg")
    obj = s3.get_object(Bucket="test-bucket", Key=key)
    assert obj["Body"].read() == b"fake-jpeg-bytes"


@mock_aws
def test_capture_failure_raises_after_retries():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-bucket")

    with pytest.raises(RuntimeError, match="webcam not found"):
        capture_and_upload(
            bucket="test-bucket",
            event_id="e1",
            device_id="pi-7",
            capture_fn=fake_capture_fails,
            s3_client=s3,
            max_retries=2,
        )
