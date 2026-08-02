import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker 
from dotenv import load_dotenv

load_dotenv()

# Use DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL est manquant. Configurez-la dans le fichier .env "
        "(ex: postgresql+psycopg2://user:password@localhost:5433/futurekawa_local)"
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

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