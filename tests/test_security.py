import pytest
import jwt
from datetime import timedelta, datetime, timezone

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
)
from app.core.config import settings


class TestPasswordHashing:

    def test_hash_and_verify_roundtrip(self):
        """Hash a password, then verify it — should return True."""
        password = "supersecret123"
        hashed = hash_password(password)

        assert hashed != password                    # not stored in plain text
        assert verify_password(password, hashed)     # correct password works

    def test_verify_wrong_password(self):
        """Wrong password should return False, not raise."""
        hashed = hash_password("correct_password")
        assert not verify_password("wrong_password", hashed)


class TestJWT:

    def test_create_token_has_correct_sub(self):
        """Token should contain the 'sub' claim we passed in."""
        token = create_access_token({"sub": "42"})
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
        )
        assert payload["sub"] == "42"

    def test_create_token_has_exp(self):
        """Token should contain an 'exp' (expiry) claim."""
        token = create_access_token({"sub": "1"})
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
        )
        assert "exp" in payload

    def test_create_token_custom_expiry(self):
        """Custom expires_delta should be respected."""
        token = create_access_token({"sub": "1"}, expires_delta=timedelta(minutes=5))
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        # Expiry should be roughly 5 minutes from now (allow 10s tolerance)
        diff = (exp - now).total_seconds()
        assert 290 < diff < 310

    def test_verify_token_valid(self):
        """verify_token should return the user_id as int for a valid token."""
        token = create_access_token({"sub": "99"})
        result = verify_token(token)
        assert result == 99

    def test_verify_token_expired(self):
        """Expired token should return None."""
        token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
        result = verify_token(token)
        assert result is None

    def test_verify_token_invalid_string(self):
        """Garbage string should return None."""
        result = verify_token("not.a.real.token")
        assert result is None

    def test_verify_token_missing_sub(self):
        """Token without 'sub' claim should return None."""
        token = create_access_token({})  # no "sub" key
        result = verify_token(token)
        assert result is None
