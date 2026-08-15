import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, font_exists:=True, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "insightiq.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
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

    # SQLite migration: check if preferred_llm_provider column exists in users table
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("PRAGMA table_info(users);"))
            columns = [row[1] for row in result.fetchall()]
            if columns:
                if "preferred_llm_provider" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN preferred_llm_provider VARCHAR(50);"))
                if "groq_api_key" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN groq_api_key VARCHAR(255);"))
                conn.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"DB Migration note: {e}")

