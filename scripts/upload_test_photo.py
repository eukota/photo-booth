#!/usr/bin/env python3
import argparse
import io
import uuid
import boto3

# Smallest valid 1x1 black JPEG, used as a stand-in for a real capture.
FIXTURE_JPEG_BYTES = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300010101010101"
    "01010101010101010101010101010101010101010101010101010101010101"
    "01010101010101010101010101010101010101010101010101010101010101"
    "0101ffc9000b080001000101011100ffcc000600101005ffda0008010100003f00d2cf20ffd9"
)


def upload(
    bucket: str, event_id: str, device_id: str, count: int, endpoint_url: str | None
):
    s3 = boto3.client("s3", endpoint_url=endpoint_url)
    for _ in range(count):
        key = f"events/{event_id}/{device_id}/{uuid.uuid4()}.jpg"
        s3.upload_fileobj(io.BytesIO(FIXTURE_JPEG_BYTES), bucket, key)
        print(f"uploaded {key}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", default="kinetic-photo-booth-photos-000000000000")
    parser.add_argument("--event-id", default="test-event")
    parser.add_argument("--device-id", default="test-device")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--endpoint-url", default=None)
    args = parser.parse_args()
    upload(args.bucket, args.event_id, args.device_id, args.count, args.endpoint_url)
