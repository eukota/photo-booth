import json
import os
from src.common.session import create_session
from src.common.response import json_response


def lambda_handler(event, context):
    body = json.loads(event.get("body") or "{}")
    submitted = body.get("password", "")
    expected = os.environ["GALLERY_PASSWORD"]

    if submitted != expected:
        return json_response(401, {"error": "invalid credentials"})

    token = create_session(secret=os.environ["SESSION_SECRET"])
    return json_response(200, {"session": token})
