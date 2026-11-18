import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from backend.app.core.config import settings

# Attempt to load argon2, otherwise fallback to bcrypt
try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    _hasher = PasswordHasher()
    _HAS_ARGON2 = True
except ImportError:
    _HAS_ARGON2 = False
    import bcrypt


def get_pin_hash(pin: str) -> str:
    """Hash PIN using Argon2id if available, otherwise bcrypt."""
    if _HAS_ARGON2:
        return _hasher.hash(pin)
    else:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pin.encode("utf-8"), salt).decode("utf-8")


def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Verify PIN against hash."""
    if not hashed_pin:
        return False
    if _HAS_ARGON2 and hashed_pin.startswith("$argon2"):
        try:
            return _hasher.verify(hashed_pin, plain_pin)
        except Exception:
            return False
    elif hashed_pin.startswith("$2b$") or hashed_pin.startswith("$2a$"):
        import bcrypt
        try:
            return bcrypt.checkpw(plain_pin.encode("utf-8"), hashed_pin.encode("utf-8"))
        except Exception:
            return False
    else:
        # Fallback for plain argon2 or standard compare
        try:
            if _HAS_ARGON2:
                return _hasher.verify(hashed_pin, plain_pin)
        except Exception:
            pass
        return False


def hash_device_token(token: str) -> str:
    """Deterministic hash of device token for DB storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_device_token() -> str:
    """Generate cryptographically secure random device token."""
    return secrets.token_urlsafe(32)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate signed JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate signed JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None
