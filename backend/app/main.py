import os
from pathlib import Path

# Load .env configuration if present
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    with open(_env_file, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ[_k.strip()] = _v.strip().strip("'").strip('"')

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.exceptions import IngestionError, ingestion_error_handler
from app.ai.ollama_client import OllamaUnavailableError
from app.core.database import init_db
from app.api.routes.upload import router as upload_router
from app.api.routes.dataset import router as dataset_router
from app.api.routes.chat import router as chat_router
from app.api.routes.auth import router as auth_router
from app.api.routes.user import router as user_router
from app.api.routes.settings import router as settings_router

# Initialize SQLite database schema
init_db()

app = FastAPI(
    title="InsightIQ API",
    description="Backend API for InsightIQ Data Analytics & Data Science Platform",
    version="1.0.0"
)

# Configure CORS
cors_env = os.getenv("CORS_ORIGINS", "").strip()
if cors_env:
    origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
else:
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(OllamaUnavailableError)
async def ollama_unavailable_handler(request: Request, exc: OllamaUnavailableError):
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)}
    )


# Register custom exception handler
app.add_exception_handler(IngestionError, ingestion_error_handler)

# Register routes
app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(dataset_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
