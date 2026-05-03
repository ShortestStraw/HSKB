import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hearthstone.db")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-for-jwt-generation")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30