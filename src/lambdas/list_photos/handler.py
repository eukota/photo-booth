import json
import os
import boto3
from src.common.session import verify_session

PRESIGN_TTL_SECONDS = 30 * 60


def lambda_handler(event, context):
    auth_header = (event.get("headers") or {}).get("authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()

    if not token or not verify_session(token, secret=os.environ["SESSION_SECRET"]):
        return {"statusCode": 401, "body": json.dumps({"error": "unauthorized"})}

    bucket = os.environ["PHOTOS_BUCKET_NAME"]
    s3 = boto3.client("s3")
    response = s3.list_objects_v2(Bucket=bucket)

    photos = [
        {
            "key": obj["Key"],
            "url": s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": obj["Key"]},
                ExpiresIn=PRESIGN_TTL_SECONDS,
            ),
        }
        for obj in response.get("Contents", [])
    ]

    return {"statusCode": 200, "body": json.dumps({"photos": photos})}
