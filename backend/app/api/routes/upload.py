import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Query, Depends, status, HTTPException
import shutil
from sqlalchemy.orm import Session

from app.schemas.upload import DatasetMetadataResponse, ColumnMetadata, SelectSheetRequest
from app.ingestion.parser import parse_file, get_excel_sheet_names, normalize_file_type, SUPPORTED_TYPES
from app.core.exceptions import (
    UnsupportedTypeError,
    EmptyFileError,
    FileNotFoundErrorCustom
)
from app.core.session import store_dataset
from app.core.storage import save_dataset_file, get_local_cache_path
from app.core.database import get_db
from app.auth.dependencies import get_optional_user
from app.models.db_models import User, DatasetModel

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["upload"])


def get_uploads_dir() -> Path:
    """Returns the uploads directory path, creating it lazily if needed.
    Configurable via UPLOADS_DIR_PATH environment variable."""
    env_path = os.getenv("UPLOADS_DIR_PATH")
    if env_path and env_path.strip():
        uploads_dir = Path(env_path.strip()).resolve()
    else:
        uploads_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "uploads"
    
    try:
        uploads_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"Failed to create uploads directory '{uploads_dir}': {e}")

    return uploads_dir


def get_file_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext.startswith("."):
        ext = ext[1:]
    return ext


def build_column_metadata(df) -> list[ColumnMetadata]:
    return [
        ColumnMetadata(name=str(col), dtype=str(df[col].dtype))
        for col in df.columns
    ]


def find_file_by_id(file_id: str) -> Path:
    # Look for matching file in uploads directory recursively
    uploads_dir = get_uploads_dir()
    if uploads_dir.exists():
        for p in uploads_dir.rglob("*"):
            if p.is_file() and p.name.startswith(file_id):
                return p
    raise FileNotFoundErrorCustom(f"File reference '{file_id}' not found.")


@router.post("/upload", response_model=DatasetMetadataResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Query(None, description="Optional sheet name for Excel files"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise EmptyFileError("No filename provided in upload.")

    ext = get_file_extension(file.filename)
    if ext not in SUPPORTED_TYPES:
        raise UnsupportedTypeError(f"Unsupported file extension '.{ext}'. Supported extensions: CSV, XLSX, XLS, JSON, Parquet.")

    # Generate unique reference ID
    file_id = str(uuid.uuid4())
    user_folder = current_user.id if current_user else "guest"
    uploads_dir = get_uploads_dir()
    target_dir = uploads_dir / user_folder
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"Failed to create target upload directory '{target_dir}': {e}")

    safe_filename = f"{file_id}_{Path(file.filename).name}"
    dest_path = target_dir / safe_filename

    # Read uploaded file bytes
    try:
        file_bytes = await file.read()
    finally:
        await file.close()

    file_size = len(file_bytes)
    if file_size == 0:
        raise EmptyFileError("Uploaded file is empty (0 bytes).")

    # Save to unified persistent storage abstraction (PostgreSQL Blob + Local Cache + Optional S3)
    user_id = current_user.id if current_user else None
    storage_ref = save_dataset_file(
        file_id=file_id,
        filename=file.filename,
        content_bytes=file_bytes,
        user_id=user_id,
        db=db
    )
    dest_path = get_local_cache_path(file_id, file.filename, user_id)

    # Excel file handling
    if ext in ("xlsx", "xls"):
        sheet_names = get_excel_sheet_names(dest_path)
        
        if len(sheet_names) > 1 and sheet_name is None:
            # Save preliminary record
            ds_rec = DatasetModel(
                id=file_id,
                user_id=user_id,
                filename=file.filename,
                file_type=f".{ext}",
                file_path=storage_ref
            )
            db.add(ds_rec)
            db.commit()

            return DatasetMetadataResponse(
                file_id=file_id,
                filename=file.filename,
                file_type=ext,
                file_size=file_size,
                sheet_names=sheet_names,
                requires_sheet_selection=True
            )

        target_sheet = sheet_name if sheet_name else sheet_names[0]
        df = parse_file(dest_path, ext, sheet_name=target_sheet)
        store_dataset(file_id, df)

        # Save DB model record
        ds_rec = DatasetModel(
            id=file_id,
            user_id=user_id,
            filename=file.filename,
            file_type=f".{ext}",
            row_count=len(df),
            column_count=len(df.columns),
            file_path=storage_ref
        )
        db.add(ds_rec)
        db.commit()

        return DatasetMetadataResponse(
            file_id=file_id,
            filename=file.filename,
            file_type=ext,
            file_size=file_size,
            row_count=len(df),
            column_count=len(df.columns),
            columns=build_column_metadata(df),
            sheet_names=sheet_names,
            selected_sheet=target_sheet,
            requires_sheet_selection=False
        )

    # Standard non-Excel files (CSV, JSON, Parquet)
    df = parse_file(dest_path, ext)
    store_dataset(file_id, df)

    # Save DB model record
    ds_rec = DatasetModel(
        id=file_id,
        user_id=user_id,
        filename=file.filename,
        file_type=f".{ext}",
        row_count=len(df),
        column_count=len(df.columns),
        file_path=storage_ref
    )
    db.add(ds_rec)
    db.commit()

    return DatasetMetadataResponse(
        file_id=file_id,
        filename=file.filename,
        file_type=ext,
        file_size=file_size,
        row_count=len(df),
        column_count=len(df.columns),
        columns=build_column_metadata(df),
        requires_sheet_selection=False
    )


@router.post("/select-sheet", response_model=DatasetMetadataResponse)
@router.post("/upload/select-sheet", response_model=DatasetMetadataResponse)
async def select_excel_sheet(
    payload: SelectSheetRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    file_path = find_file_by_id(payload.file_id)
    ext = get_file_extension(file_path.name)
    sheet_names = get_excel_sheet_names(file_path)

    if payload.sheet_name not in sheet_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sheet '{payload.sheet_name}' does not exist in this workbook. Available sheets: {', '.join(sheet_names)}"
        )

    df = parse_file(file_path, ext, sheet_name=payload.sheet_name)
    store_dataset(payload.file_id, df)
    file_size = os.path.getsize(file_path)

    # Check if DB record exists or create it
    ds_rec = db.query(DatasetModel).filter(DatasetModel.id == payload.file_id).first()
    if not ds_rec:
        ds_rec = DatasetModel(
            id=payload.file_id,
            user_id=current_user.id if current_user else None,
            filename=file_path.name,
            file_type=f".{ext}",
            row_count=len(df),
            column_count=len(df.columns),
            file_path=str(file_path)
        )
        db.add(ds_rec)
    else:
        ds_rec.row_count = len(df)
        ds_rec.column_count = len(df.columns)
    db.commit()

    return DatasetMetadataResponse(
        file_id=payload.file_id,
        filename=file_path.name,
        file_type=ext,
        file_size=file_size,
        row_count=len(df),
        column_count=len(df.columns),
        columns=build_column_metadata(df),
        sheet_names=sheet_names,
        selected_sheet=payload.sheet_name,
        requires_sheet_selection=False
    )
