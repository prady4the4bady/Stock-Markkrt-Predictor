from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db
from .models.user import User
from .config import DATA_DIR
import os

# Secret key for JWT encoding (should be in env, but generating one for now)
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60 # 30 days for convenience

import hashlib
import hmac
import binascii

# PBKDF2 settings (pure-Python, no native dependencies)
PBKDF2_ITERATIONS = int(os.getenv("PBKDF2_ITERATIONS", "260000"))
PBKDF2_SALT_BYTES = 16


def get_password_hash(password: str) -> str:
    """Create a pbkdf2_sha256 password hash string: pbkdf2_sha256$iterations$salt_hex$dk_hex"""
    try:
        if isinstance(password, str):
            password_bytes = password.encode("utf-8")
        else:
            password_bytes = password
        print(f"[Auth] Using PBKDF2 to hash password, bytes length={len(password_bytes)}")
        salt = os.urandom(PBKDF2_SALT_BYTES)
        dk = hashlib.pbkdf2_hmac("sha256", password_bytes, salt, PBKDF2_ITERATIONS)
        return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${binascii.hexlify(salt).decode()}${binascii.hexlify(dk).decode()}"
    except Exception as e:
        print(f"[Auth] Password hashing failed (pbkdf2): {e}")
        raise RuntimeError("Password hashing failed") from e


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")


def verify_password(plain_password, stored_hash):
    """Verify a plain password against stored hash. Supports pbkdf2_sha256 and bcrypt legacy hashes."""
    try:
        if isinstance(plain_password, str):
            plain_bytes = plain_password.encode("utf-8")
        else:
            plain_bytes = plain_password

        if stored_hash.startswith("pbkdf2_sha256$"):
            try:
                _, iter_s, salt_hex, dk_hex = stored_hash.split("$")
                iters = int(iter_s)
                salt = binascii.unhexlify(salt_hex)
                expected = binascii.unhexlify(dk_hex)
                dk = hashlib.pbkdf2_hmac("sha256", plain_bytes, salt, iters)
                return hmac.compare_digest(dk, expected)
            except Exception as e:
                print(f"[Auth] pbkdf2 verify error: {e}")
                return False
        # Legacy bcrypt hash (e.g., $2b$...)
        if stored_hash.startswith("$2"):
            try:
                import bcrypt
                return bcrypt.checkpw(plain_bytes, stored_hash.encode("utf-8"))
            except Exception as e:
                print(f"[Auth] bcrypt verify error: {e}")
                return False

        # Unknown hash format
        return False
    except Exception as e:
        print(f"[Auth] verify_password unexpected error: {e}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
