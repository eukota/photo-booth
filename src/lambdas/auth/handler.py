import json
import os
from src.common.session import create_session


def lambda_handler(event, context):
    body = json.loads(event.get("body") or "{}")
    submitted = body.get("password", "")
    expected = os.environ["GALLERY_PASSWORD"]

    if submitted != expected:
        return {
            "statusCode": 401,
            "body": json.dumps({"error": "invalid credentials"}),
        }

    token = create_session(secret=os.environ["SESSION_SECRET"])
    return {
        "statusCode": 200,
        "body": json.dumps({"session": token}),
    }
