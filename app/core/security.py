import os
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import jwt
from typing import Optional
from fastapi import HTTPException, status, Request

# Security configurations
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-for-researchtrack-1l-scale")
ALGORITHM = "HS256"
# Allow configuring session expiration from .env, defaulting to 7 days (10080 minutes)
SESSION_EXPIRY_MINUTES = int(os.getenv("SESSION_EXPIRY_MINUTES", 60 * 24 * 7))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=SESSION_EXPIRY_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def get_current_user_from_cookie(request: Request) -> Optional[dict]:
    """Dependency to retrieve user from JWT cookie securely at scale."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    # Token formatted usually as 'Bearer <token>'
    if token.startswith("Bearer "):
        token = token.split("Bearer ")[1]
    
    payload = decode_access_token(token)
    if payload:
        return payload # Returns dictionary with user info (sub/email, role, id)
    return None