import json
import os
import boto3
from src.common.session import verify_session

PRESIGN_TTL_SECONDS = 30 * 60


def lambda_handler(event, context):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    auth_header = headers.get("authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()

    if not token or not verify_session(token, secret=os.environ["SESSION_SECRET"]):
        return {"statusCode": 401, "body": json.dumps({"error": "unauthorized"})}

    bucket = os.environ["PHOTOS_BUCKET_NAME"]
    s3 = boto3.client("s3")
    response = s3.list_objects_v2(Bucket=bucket)

    # Presigned URLs are signed locally (no network call), so this client
    # can point at a different, externally-reachable endpoint than the one
    # used above for the real list_objects_v2 call - needed for local dev,
    # where the Lambda container reaches LocalStack via an internal Docker
    # address that a browser on the host can't resolve. Unset in
    # production, where boto3's default (real AWS) endpoint is correct.
    presign_endpoint_url = os.environ.get("PRESIGN_ENDPOINT_URL") or None
    presign_client = (
        boto3.client("s3", endpoint_url=presign_endpoint_url)
        if presign_endpoint_url
        else s3
    )

    photos = [
        {
            "key": obj["Key"],
            "url": presign_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": obj["Key"]},
                ExpiresIn=PRESIGN_TTL_SECONDS,
            ),
        }
        for obj in response.get("Contents", [])
    ]

    return {"statusCode": 200, "body": json.dumps({"photos": photos})}
