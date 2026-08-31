import json
from src.common.response import json_response


def test_json_response_includes_cors_header():
    result = json_response(200, {"ok": True})
    assert result["headers"]["Access-Control-Allow-Origin"] == "*"
    assert json.loads(result["body"]) == {"ok": True}
    assert result["statusCode"] == 200
