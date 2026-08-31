#!/usr/bin/env python3
"""Simulates a Pi Zero W booth: press Enter to "press the button" and
snap + upload a real photo from this machine's webcam. Uses the same
capture_and_upload() core the real Pi will eventually use - only the
capture_fn differs (ffmpeg/avfoundation here instead of fswebcam).

Usage:
    python scripts/webcam_simulator.py --endpoint-url http://localhost:4566
"""
import argparse
import subprocess
import sys
import boto3

sys.path.insert(0, ".")
from pi.capture import capture_and_upload  # noqa: E402


def mac_webcam_capture(camera_index: str = "0") -> bytes:
    """Grab one still frame from a macOS webcam via ffmpeg/avfoundation."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "avfoundation",
            "-video_size",
            "640x480",
            "-framerate",
            "30",
            "-i",
            camera_index,
            "-frames:v",
            "1",
            "-update",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "-",
        ],
        capture_output=True,
        check=True,
    )
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default="kinetic-photo-booth-photos-000000000000")
    parser.add_argument("--event-id", default="test-event")
    parser.add_argument("--device-id", default="webcam-simulator")
    parser.add_argument(
        "--camera-index", default="0", help="ffmpeg avfoundation device index"
    )
    parser.add_argument("--endpoint-url", default=None)
    args = parser.parse_args()

    s3 = boto3.client("s3", endpoint_url=args.endpoint_url)

    print(f"Webcam booth simulator - uploading to bucket: {args.bucket}")
    print("Press Enter to snap a photo (Ctrl+C to quit).")
    try:
        while True:
            input()
            try:
                key = capture_and_upload(
                    bucket=args.bucket,
                    event_id=args.event_id,
                    device_id=args.device_id,
                    capture_fn=lambda: mac_webcam_capture(args.camera_index),
                    s3_client=s3,
                )
                print(f"  uploaded {key}")
            except Exception as error:  # noqa: BLE001 - keep the loop alive on failure
                print(f"  capture/upload failed: {error}")
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")


if __name__ == "__main__":
    main()
