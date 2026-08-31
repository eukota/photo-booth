#!/usr/bin/env python3
import argparse
import io
import uuid
import boto3

# A real, browser-renderable 4x4 baseline JPEG (solid red), used as a
# stand-in for a real capture. NOTE: an earlier version of this fixture
# used arithmetic-coded JPEG markers (SOF9) - technically a valid JPEG per
# file-format checkers like `file`, but essentially no web browser can
# decode arithmetic coding (patent history), so it rendered nothing in
# the gallery with no console error. This one uses standard baseline
# (SOF0) Huffman coding, which every browser supports.
FIXTURE_JPEG_BYTES = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300100b0c0e0c0a10"
    "0e0d0e1211101318281a181616183123251d283a333d3c3933383740485c4e40"
    "4457453738506d51575f626768673e4d71797064785c656763ffdb0043011112"
    "121815182f1a1a2f634238426363636363636363636363636363636363636363"
    "636363636363636363636363636363636363636363636363636363636363ffc0"
    "0011080004000403012200021101031101ffc4001f0000010501010101010100"
    "000000000000000102030405060708090a0bffc400b510000201030302040305"
    "0504040000017d01020300041105122131410613516107227114328191a10823"
    "42b1c11552d1f02433627282090a161718191a25262728292a3435363738393a"
    "434445464748494a535455565758595a636465666768696a737475767778797a"
    "838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7"
    "b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1"
    "f2f3f4f5f6f7f8f9faffc4001f01000301010101010101010100000000000001"
    "02030405060708090a0bffc400b5110002010204040304070504040001027700"
    "0102031104052131061241510761711322328108144291a1b1c109233352f015"
    "6272d10a162434e125f11718191a262728292a35363738393a43444546474849"
    "4a535455565758595a636465666768696a737475767778797a82838485868788"
    "898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4"
    "c5c6c7c8c9cad2d3d4d5d6d7d8d9dae2e3e4e5e6e7e8e9eaf2f3f4f5f6f7f8f9"
    "faffda000c03010002110311003f00a545145721f427ffd9"
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
