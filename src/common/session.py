import time
import jwt

DEFAULT_TTL_SECONDS = 60 * 60  # 1 hour


def create_session(secret: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    payload = {"exp": int(time.time()) + ttl_seconds, "role": "operator"}
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_session(token: str, secret: str) -> bool:
    try:
        jwt.decode(token, secret, algorithms=["HS256"])
        return True
    except jwt.PyJWTError:
        return False
