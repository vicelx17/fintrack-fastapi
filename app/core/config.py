import os
from datetime import timedelta

DATABASE_URL_DEFAULT = "postgresql+asyncpg://vicente:secret@db:5432/finanzas"

SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PROD")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

DATABASE_URL = os.getenv("DATABASE_URL", DATABASE_URL_DEFAULT)

def access_token_expires() -> timedelta:
    return timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)