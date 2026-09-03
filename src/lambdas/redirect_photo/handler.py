import os
import boto3

# Same TTL as list_photos - this endpoint's whole point is generating the
# presigned URL fresh at scan time rather than at gallery-load time, so a
# QR code scanned long after the gallery page loaded still works.
PRESIGN_TTL_SECONDS = 30 * 60


def lambda_handler(event, context):
    # API Gateway path param is named "proxy" (see infra/template.yaml
    # for why), but it holds the full S3 object key.
    key = (event.get("pathParameters") or {}).get("proxy")
    if not key:
        return {"statusCode": 400, "body": "missing photo key"}

    bucket = os.environ["PHOTOS_BUCKET_NAME"]

    # See list_photos/handler.py for why presigning uses a possibly
    # different endpoint than the rest of this Lambda's S3 calls (local
    # dev via LocalStack vs. real AWS).
    presign_endpoint_url = os.environ.get("PRESIGN_ENDPOINT_URL") or None
    presign_client = boto3.client("s3", endpoint_url=presign_endpoint_url)

    url = presign_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=PRESIGN_TTL_SECONDS,
    )

    return {"statusCode": 302, "headers": {"Location": url}, "body": ""}
