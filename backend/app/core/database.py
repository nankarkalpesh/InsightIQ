import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.strip():
    DATABASE_URL = DATABASE_URL.strip()
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    db_path_env = os.getenv("DB_PATH")
    if db_path_env and db_path_env.strip():
        DB_PATH = db_path_env.strip()
    else:
        DATA_DIR = os.path.join(BASE_DIR, "data")
        DB_PATH = os.path.join(DATA_DIR, "insightiq.db")

    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    if db_dir:
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create database directory '{db_dir}': {e}")

    DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and run column migrations if needed."""
    from app.models import db_models  # noqa
    Base.metadata.create_all(bind=engine)

    # Database migration: check if preferred_llm_provider / groq_api_key columns exist in users table
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        if inspector.has_table("users"):
            columns = [col["name"] for col in inspector.get_columns("users")]
            if columns:
                with engine.begin() as conn:
                    if "preferred_llm_provider" not in columns:
                        conn.execute(text("ALTER TABLE users ADD COLUMN preferred_llm_provider VARCHAR(50);"))
                    if "groq_api_key" not in columns:
                        conn.execute(text("ALTER TABLE users ADD COLUMN groq_api_key VARCHAR(255);"))
    except Exception as e:
        logger.warning(f"DB Migration note: {e}")


