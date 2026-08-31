import os
import subprocess
import sys
import requests
import pytest

LOCALSTACK_ENDPOINT = "http://localhost:4566"
API_BASE_URL = os.environ.get("LOCAL_API_BASE_URL")  # set by dev/CI after deploy


@pytest.mark.skipif(
    not API_BASE_URL, reason="LOCAL_API_BASE_URL not set; run `make local-deploy` first"
)
def test_uploaded_photos_appear_in_gallery():
    subprocess.run(
        [
            sys.executable,
            "scripts/upload_test_photo.py",
            "--bucket",
            "kinetic-photo-booth-photos-000000000000",
            "--count",
            "2",
            "--endpoint-url",
            LOCALSTACK_ENDPOINT,
        ],
        check=True,
        env={**os.environ, "AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test",
             "AWS_DEFAULT_REGION": "us-east-1"},
    )

    auth_res = requests.post(
        f"{API_BASE_URL}/auth",
        json={"password": "localtest"},
        headers={"Content-Type": "application/json"},
    )
    assert auth_res.status_code == 200
    token = auth_res.json()["session"]

    photos_res = requests.get(
        f"{API_BASE_URL}/photos", headers={"Authorization": f"Bearer {token}"}
    )
    assert photos_res.status_code == 200
    photos = photos_res.json()["photos"]
    assert len(photos) >= 2
    for photo in photos:
        fetched = requests.get(photo["url"])
        assert fetched.status_code == 200


@pytest.mark.skipif(
    not API_BASE_URL, reason="LOCAL_API_BASE_URL not set; run `make local-deploy` first"
)
def test_wrong_password_rejected():
    auth_res = requests.post(
        f"{API_BASE_URL}/auth",
        json={"password": "not-the-password"},
        headers={"Content-Type": "application/json"},
    )
    assert auth_res.status_code == 401


@pytest.mark.skipif(
    not API_BASE_URL, reason="LOCAL_API_BASE_URL not set; run `make local-deploy` first"
)
def test_missing_session_rejected():
    photos_res = requests.get(f"{API_BASE_URL}/photos")
    assert photos_res.status_code == 401
