import bcrypt
from datetime import timedelta, datetime, timezone

from fastapi import HTTPException
from jose import jwt, JWTError

from app.core.config import access_token_expires, SECRET_KEY, ALGORITHM

def hash_password(password: str) -> str:
    try:
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_bytes = bcrypt.hashpw(password_bytes, salt)
        hashed_str = hashed_bytes.decode('utf-8')
        return hashed_str
    except Exception as e:
        if "password too long" in str(e):
            raise HTTPException(status_code=401, detail="Password too long")
        print(f"❌ Error al hashear: {e}")
        raise

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        plain_password_bytes = plain_password.encode('utf-8')
        hashed_password_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)
    except Exception as e:
        return False

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or access_token_expires())
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise