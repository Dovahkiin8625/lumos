"""认证工具：密码哈希 + JWT。"""
from __future__ import annotations
import time
from dataclasses import dataclass
import bcrypt
import jwt
from lumos.errors import LumosError


def hash_password(password: str, *, rounds: int = 12) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=rounds),
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


def create_token_pair(
    user_id: str,
    *,
    secret: str,
    access_ttl: int,
    refresh_ttl: int,
) -> TokenPair:
    now = int(time.time())
    access = jwt.encode(
        {"sub": user_id, "type": "access", "iat": now, "exp": now + access_ttl},
        secret, algorithm="HS256",
    )
    refresh = jwt.encode(
        {"sub": user_id, "type": "refresh", "iat": now, "exp": now + refresh_ttl},
        secret, algorithm="HS256",
    )
    return TokenPair(access_token=access, refresh_token=refresh, expires_in=access_ttl)


def decode_token(
    token: str, *, secret: str, expected_type: str,
) -> dict:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as e:
        raise LumosError("token expired") from e
    except jwt.InvalidTokenError as e:
        raise LumosError(f"invalid token: {e}") from e
    if payload.get("type") != expected_type:
        raise LumosError(f"wrong token type: expected {expected_type}")
    return payload