import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()
database_url = settings.DATABASE_URL
is_vercel = bool(os.environ.get("VERCEL"))

if is_vercel:
    if database_url.startswith("sqlite"):
        raise RuntimeError("Set DATABASE_URL to a persistent PostgreSQL database on Vercel.")
    if not database_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("DATABASE_URL must use PostgreSQL on Vercel.")
    if settings.APP_ENV != "production":
        raise RuntimeError("Set APP_ENV=production in the Vercel environment.")
    if not 1 <= settings.MAX_UPLOAD_SIZE_MB <= 25:
        raise RuntimeError("Set MAX_UPLOAD_SIZE_MB to a value from 1 to 25 on Vercel.")
    if (
        len(settings.SECRET_KEY) < 32
        or settings.SECRET_KEY
        in {
            "finsight-dev-secret-key-change-in-production",
            "generate-a-unique-secret-of-at-least-32-characters",
            "change-this-to-a-secure-random-secret-in-production",
        }
    ):
        raise RuntimeError("Set a unique SECRET_KEY of at least 32 characters on Vercel.")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
engine_options = {"connect_args": connect_args, "future": True}

if database_url.startswith("postgresql+psycopg://"):
    engine_options.update(
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
        connect_args={"prepare_threshold": None},
    )

engine = create_engine(database_url, **engine_options)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
