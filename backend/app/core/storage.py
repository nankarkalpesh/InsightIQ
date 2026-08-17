import os
import logging
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.core.exceptions import FileNotFoundErrorCustom

logger = logging.getLogger(__name__)

# Base upload directory for local caching
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")


def get_local_cache_path(file_id: str, filename: str, user_id: Optional[str] = None) -> str:
    """Get expected local filesystem path for a dataset file."""
    user_folder = user_id if user_id else "guest"
    folder_path = os.path.join(UPLOAD_DIR, user_folder)
    os.makedirs(folder_path, exist_ok=True)
    clean_filename = os.path.basename(filename)
    return os.path.join(folder_path, f"{file_id}_{clean_filename}")


def save_dataset_file(
    file_id: str,
    filename: str,
    content_bytes: bytes,
    user_id: Optional[str] = None,
    db: Optional[Session] = None
) -> str:
    """
    Save raw dataset file bytes to persistent database storage and local disk cache.
    Returns persistent storage URI reference string.
    """
    from app.models.db_models import DatasetFileBlobModel

    # 1. Save to local disk cache for fast parser access
    local_path = get_local_cache_path(file_id, filename, user_id)
    with open(local_path, "wb") as f:
        f.write(content_bytes)

    # 2. Save raw binary content to persistent PostgreSQL blob table if db session provided
    if db is not None:
        try:
            existing_blob = db.query(DatasetFileBlobModel).filter(DatasetFileBlobModel.file_id == file_id).first()
            if existing_blob:
                existing_blob.content = content_bytes
            else:
                new_blob = DatasetFileBlobModel(file_id=file_id, content=content_bytes)
                db.add(new_blob)
            db.commit()
            logger.info(f"[PERSISTENT STORAGE] Saved {len(content_bytes)} bytes for dataset '{file_id}' into database blob table.")
        except Exception as err:
            db.rollback()
            logger.warning(f"[PERSISTENT STORAGE] Failed to write blob to database for dataset '{file_id}': {err}")

    # 3. Optional S3 Cloud Object Storage
    s3_bucket = os.getenv("S3_BUCKET") or os.getenv("AWS_STORAGE_BUCKET_NAME")
    if s3_bucket:
        try:
            import boto3
            s3_client = boto3.client("s3")
            s3_key = f"datasets/{user_id or 'guest'}/{file_id}_{filename}"
            s3_client.put_object(Bucket=s3_bucket, Key=s3_key, Body=content_bytes)
            logger.info(f"[PERSISTENT STORAGE] Uploaded dataset '{file_id}' to S3 bucket '{s3_bucket}/{s3_key}'.")
        except Exception as err:
            logger.warning(f"[PERSISTENT STORAGE] S3 upload skipped or failed: {err}")

    return f"storage://datasets/{file_id}"


def get_dataset_file_bytes(
    file_id: str,
    filename: str = "dataset.csv",
    user_id: Optional[str] = None,
    db: Optional[Session] = None
) -> bytes:
    """
    Retrieve dataset file bytes by file_id.
    Checks local disk cache -> PostgreSQL Database Blob -> S3 Cloud Storage.
    Restores local disk cache if missing from local disk.
    """
    from app.models.db_models import DatasetFileBlobModel

    # 1. Check local disk cache
    local_path = get_local_cache_path(file_id, filename, user_id)
    if os.path.exists(local_path):
        try:
            with open(local_path, "rb") as f:
                data = f.read()
                if data and len(data) > 0:
                    return data
        except Exception:
            pass

    # 2. Retrieve from PostgreSQL database blob table
    if db is not None:
        blob_rec = db.query(DatasetFileBlobModel).filter(DatasetFileBlobModel.file_id == file_id).first()
        if blob_rec and blob_rec.content:
            logger.info(f"[PERSISTENT STORAGE] Hydrated {len(blob_rec.content)} bytes from database blob for dataset '{file_id}'.")
            # Write back to local cache for fast future access
            try:
                with open(local_path, "wb") as f:
                    f.write(blob_rec.content)
            except Exception as e:
                logger.warning(f"Could not cache retrieved blob to disk: {e}")
            return blob_rec.content

    # 3. Retrieve from S3 Cloud Object Storage if configured
    s3_bucket = os.getenv("S3_BUCKET") or os.getenv("AWS_STORAGE_BUCKET_NAME")
    if s3_bucket:
        try:
            import boto3
            s3_client = boto3.client("s3")
            s3_key = f"datasets/{user_id or 'guest'}/{file_id}_{filename}"
            obj = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
            data = obj["Body"].read()
            if data:
                try:
                    with open(local_path, "wb") as f:
                        f.write(data)
                except Exception:
                    pass
                return data
        except Exception as err:
            logger.warning(f"[PERSISTENT STORAGE] S3 download error: {err}")

    raise FileNotFoundErrorCustom("The dataset file is no longer available on server storage. Please re-upload your dataset.")


def delete_dataset_file(
    file_id: str,
    filename: str = "dataset.csv",
    user_id: Optional[str] = None,
    db: Optional[Session] = None
) -> None:
    """Delete dataset file from local cache, database blob, and S3."""
    from app.models.db_models import DatasetFileBlobModel

    # Remove local cache
    local_path = get_local_cache_path(file_id, filename, user_id)
    if os.path.exists(local_path):
        try:
            os.remove(local_path)
        except Exception as err:
            logger.warning(f"Failed to remove local file '{local_path}': {err}")

    # Remove database blob
    if db is not None:
        try:
            db.query(DatasetFileBlobModel).filter(DatasetFileBlobModel.file_id == file_id).delete()
            db.commit()
        except Exception as err:
            db.rollback()
            logger.warning(f"Failed to delete database blob for dataset '{file_id}': {err}")

    # Remove S3 object if configured
    s3_bucket = os.getenv("S3_BUCKET") or os.getenv("AWS_STORAGE_BUCKET_NAME")
    if s3_bucket:
        try:
            import boto3
            s3_client = boto3.client("s3")
            s3_key = f"datasets/{user_id or 'guest'}/{file_id}_{filename}"
            s3_client.delete_object(Bucket=s3_bucket, Key=s3_key)
        except Exception:
            pass
