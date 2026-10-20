import time
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


def create_access_token(subject: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(
        payload, settings.secret_key.get_secret_value(), algorithm=settings.jwt_algorithm
    )


# Tokens issued by other services can be a few minutes ahead/behind our clock.
CLOCK_SKEW_LEEWAY_SECONDS = 300


def decode_access_token(token: str) -> dict:
    """Decode and validate a token. Raises ``jwt.InvalidTokenError`` on failure."""
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        options={"verify_exp": False, "verify_iat": False},
    )

    exp = payload.get("exp")
    if exp is not None and exp + CLOCK_SKEW_LEEWAY_SECONDS < time.time():
        raise jwt.ExpiredSignatureError("Signature has expired")
    if "sub" not in payload:
        raise jwt.MissingRequiredClaimError("sub")
    return payload
