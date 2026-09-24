import hashlib
import hmac
import time
from typing import Optional, Dict, Any
from backend.app.core.config import settings

def hash_password(password: str) -> str:
    """Hash password using SHA-256 with secret salt for lightweight SIH requirement."""
    salted = f"{settings.SECRET_KEY}:{password}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    payload = data.copy()
    expire = time.time() + (expires_delta or settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    payload["exp"] = expire
    # Simplified signed token
    raw = f"{payload.get('sub','')}:{expire}".encode('utf-8')
    sig = hmac.new(settings.SECRET_KEY.encode('utf-8'), raw, hashlib.sha256).hexdigest()
    return f"{payload.get('sub','')}.{int(expire)}.{sig}"

def verify_access_token(token: str) -> Optional[str]:
    parts = token.split(".")
    if len(parts) != 3:
        return None
    sub, exp_str, sig = parts
    try:
        exp = int(exp_str)
        if time.time() > exp:
            return None
        raw = f"{sub}:{exp}".encode('utf-8')
        expected_sig = hmac.new(settings.SECRET_KEY.encode('utf-8'), raw, hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, expected_sig):
            return sub
    except Exception:
        return None
    return None
