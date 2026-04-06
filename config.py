import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "devkey123")

    DATABASE_URL = os.getenv("postgresql://analytics_h94f_user:jFVlxpFqygGU6BwOBbu8vTv9VCGhwE7w@dpg-d79odlmuk2gs73ehliu0-a/analytics_h94f")

    # Fix for SQLAlchemy (Render uses postgres:// sometimes)
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
