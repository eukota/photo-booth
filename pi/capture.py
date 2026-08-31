import io
import subprocess
import time
import uuid


def default_capture() -> bytes:
    """Grab one still frame from a USB webcam via fswebcam (Raspberry Pi)."""
    result = subprocess.run(
        ["fswebcam", "--no-banner", "-r", "1280x720", "-"],
        capture_output=True,
        check=True,
    )
    return result.stdout


def capture_and_upload(
    bucket: str,
    event_id: str,
    device_id: str,
    capture_fn=default_capture,
    s3_client=None,
    max_retries: int = 3,
) -> str:
    last_error = None
    for attempt in range(max_retries):
        try:
            image_bytes = capture_fn()
            key = f"events/{event_id}/{device_id}/{uuid.uuid4()}.jpg"
            s3_client.upload_fileobj(io.BytesIO(image_bytes), bucket, key)
            return key
        except Exception as error:  # noqa: BLE001 - retry any capture/upload failure
            last_error = error
            time.sleep(min(2**attempt, 10))
    raise last_error
