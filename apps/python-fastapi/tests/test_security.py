import time

import jwt
import pytest

from app.config import get_settings
from app.security import CLOCK_SKEW_LEEWAY_SECONDS, create_access_token, decode_access_token


def _token(**claims) -> str:
    settings = get_settings()
    return jwt.encode(claims, settings.secret_key.get_secret_value(), algorithm="HS256")


def test_round_trip():
    assert decode_access_token(create_access_token("42"))["sub"] == "42"


def test_recently_expired_token_is_accepted_within_leeway():
    now = int(time.time())
    token = _token(sub="1", iat=now - 3600, exp=now - CLOCK_SKEW_LEEWAY_SECONDS + 30)
    assert decode_access_token(token)["sub"] == "1"


def test_token_issued_slightly_in_the_future_is_accepted():
    now = int(time.time())
    token = _token(sub="1", iat=now + 60, exp=now + 3600)
    assert decode_access_token(token)["sub"] == "1"


def test_expired_token_is_rejected():
    now = int(time.time())
    token = _token(sub="1", iat=now - 7200, exp=now - CLOCK_SKEW_LEEWAY_SECONDS - 30)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_token_without_subject_is_rejected():
    now = int(time.time())
    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(_token(iat=now, exp=now + 60))


def test_token_with_wrong_signature_is_rejected():
    token = jwt.encode({"sub": "1"}, "another-key-another-key-another-key", algorithm="HS256")
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token)
