import json

# The gallery frontend is served from a different origin than the API
# (S3/CloudFront in prod, a plain local static server in dev), so every
# response - success or error - needs this or the browser silently drops
# it, which reads to the frontend exactly like an incorrect password.
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Content-Type": "application/json",
}


def json_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body),
    }
