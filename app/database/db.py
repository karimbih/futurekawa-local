import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker 
from dotenv import load_dotenv

load_dotenv()

# Use DATABASE_URL from environment or fallback to a local SQLite file for development
DATABASE_URL = os.getenv("DATABASE_URL")
connect_args = {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()