import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "devkey123")

    # Pull from environment variable
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Fix for SQLAlchemy / psycopg2 if URL starts with postgres://
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
