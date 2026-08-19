import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.db_models import User, DatasetModel, DashboardConfigModel, TrainingRunModel, ChatConversationModel, DatasetFileBlobModel
from app.core.session import store_dataset, get_dataset, remove_dataset
from app.core.storage import get_local_cache_path, get_dataset_file_bytes, delete_dataset_file
from app.analytics.profiling import dataset_health, column_schema, generate_insights, column_statistics
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["user"])


class SaveActivityRequest(BaseModel):
    activity_name: Optional[str] = None
    dashboard_items: Optional[List[Dict[str, Any]]] = None
    ds_state: Optional[Dict[str, Any]] = None


class DashboardSaveRequest(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list)


class DSStateSaveRequest(BaseModel):
    target_column: str
    features: List[str] = Field(default_factory=list)
    model_name: str
    metrics: Dict[str, Any] = Field(default_factory=dict)


@router.get("/datasets")
def list_user_datasets(
    saved_only: bool = Query(False, description="Filter only explicitly saved activities"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List datasets owned by the current logged-in user with server-side pagination."""
    query = db.query(DatasetModel).filter(DatasetModel.user_id == current_user.id)
    if saved_only:
        query = query.filter(DatasetModel.is_saved == True)

    total_count = query.count()
    records = query.order_by(DatasetModel.saved_at.desc(), DatasetModel.uploaded_at.desc()).offset(offset).limit(limit).all()

    datasets = []
    for r in records:
        # Calculate associated metadata counts
        dash_rec = db.query(DashboardConfigModel).filter(DashboardConfigModel.dataset_id == r.id).first()
        dash_items = json.loads(dash_rec.config_json) if dash_rec and dash_rec.config_json else []
        kpi_count = sum(1 for item in dash_items if item.get("type") == "kpi")
        chart_count = sum(1 for item in dash_items if item.get("type") in ("chart", "custom_chart"))

        chat_rec = db.query(ChatConversationModel).filter(ChatConversationModel.dataset_id == r.id).first()
        chat_msgs = json.loads(chat_rec.messages_json) if chat_rec and chat_rec.messages_json else []
        chat_count = sum(1 for m in chat_msgs if m.get("role") == "user")

        ml_count = db.query(TrainingRunModel).filter(TrainingRunModel.dataset_id == r.id).count()

        file_size = 0
        local_path = get_local_cache_path(r.id, r.filename, r.user_id)
        if os.path.exists(local_path):
            try:
                file_size = os.path.getsize(local_path)
            except Exception:
                pass

        datasets.append({
            "file_id": r.id,
            "filename": r.filename,
            "activity_name": r.activity_name or r.filename,
            "is_saved": bool(r.is_saved),
            "file_type": r.file_type,
            "file_size": file_size,
            "row_count": r.row_count,
            "column_count": r.column_count,
            "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else None,
            "saved_at": (r.saved_at or r.uploaded_at).isoformat() if (r.saved_at or r.uploaded_at) else None,
            "chat_count": chat_count,
            "kpi_count": kpi_count,
            "chart_count": chart_count,
            "ml_count": ml_count
        })

    return {
        "datasets": datasets,
        "total": total_count,
        "limit": limit,
        "offset": offset
    }


@router.post("/datasets/{dataset_id}/save-activity")
def save_activity(
    dataset_id: str,
    payload: Optional[SaveActivityRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Explicitly save or update a dataset activity for an authenticated user.
    Ensures dataset binary content is persisted in DB blob storage for full hydration survival.
    """
    rec = db.query(DatasetModel).filter(DatasetModel.id == dataset_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found."
        )

    # Security ownership check
    if rec.user_id and rec.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot save activity belonging to another user."
        )

    rec.user_id = current_user.id
    rec.is_saved = True
    rec.saved_at = datetime.utcnow()

    if payload and payload.activity_name:
        rec.activity_name = payload.activity_name.strip()

    # Ensure DatasetFileBlobModel contains raw bytes in PostgreSQL / SQLite
    blob_rec = db.query(DatasetFileBlobModel).filter(DatasetFileBlobModel.file_id == dataset_id).first()
    if not blob_rec or not blob_rec.content:
        try:
            content_bytes = get_dataset_file_bytes(file_id=dataset_id, filename=rec.filename, user_id=rec.user_id, db=db)
            if content_bytes:
                if not blob_rec:
                    blob_rec = DatasetFileBlobModel(file_id=dataset_id, content=content_bytes)
                    db.add(blob_rec)
                else:
                    blob_rec.content = content_bytes
        except Exception as err:
            logger.warning(f"Unable to write blob during save-activity for '{dataset_id}': {err}")

    # Optional payload: Dashboard config
    if payload and payload.dashboard_items is not None:
        dash_rec = db.query(DashboardConfigModel).filter(DashboardConfigModel.dataset_id == dataset_id).first()
        dash_json = json.dumps(payload.dashboard_items)
        if not dash_rec:
            dash_rec = DashboardConfigModel(user_id=current_user.id, dataset_id=dataset_id, config_json=dash_json)
            db.add(dash_rec)
        else:
            dash_rec.config_json = dash_json
            dash_rec.user_id = current_user.id

    # Optional payload: DS state
    if payload and payload.ds_state:
        ds = payload.ds_state
        if "target_column" in ds and "model_name" in ds:
            run_rec = TrainingRunModel(
                user_id=current_user.id,
                dataset_id=dataset_id,
                target_column=ds["target_column"],
                features_json=json.dumps(ds.get("features", [])),
                model_name=ds["model_name"],
                metrics_json=json.dumps(ds.get("metrics", {}))
            )
            db.add(run_rec)

    db.commit()
    return {
        "status": "saved",
        "file_id": dataset_id,
        "saved_at": rec.saved_at.isoformat(),
        "message": f"Activity '{rec.activity_name or rec.filename}' saved successfully."
    }


@router.get("/datasets/{dataset_id}/resume")
def resume_user_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reconstruct and resume dataset workspace state (metadata, dashboard config,
    training runs, chat conversation history) for a logged-in user.
    """
    rec = db.query(DatasetModel).filter(
        DatasetModel.id == dataset_id,
        DatasetModel.user_id == current_user.id
    ).first()

    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found or access denied."
        )

    # Ensure file is loaded into session memory
    try:
        df = get_dataset(dataset_id, db=db, current_user=current_user)
    except Exception:
        try:
            from app.core.storage import get_dataset_file_bytes, get_local_cache_path
            from app.ingestion.parser import parse_file
            ext = rec.file_type.lower().lstrip(".")
            get_dataset_file_bytes(file_id=rec.id, filename=rec.filename, user_id=rec.user_id, db=db)
            local_cache = get_local_cache_path(rec.id, rec.filename, rec.user_id)
            df = parse_file(local_cache, ext)
            store_dataset(dataset_id, df)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset file is no longer available on server storage. Please re-upload your dataset."
            )

    health = dataset_health(df)
    schema = column_schema(df)
    insights = generate_insights(df)
    statistics = column_statistics(df)

    metadata = {
        "file_id": dataset_id,
        "filename": rec.filename,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": [{"name": str(col), "dtype": str(df[col].dtype)} for col in df.columns],
        "health": health,
        "schema": schema,
        "statistics": statistics,
        "insights": insights
    }

    # Saved dashboard config
    dash_rec = db.query(DashboardConfigModel).filter(
        DashboardConfigModel.dataset_id == dataset_id
    ).order_by(DashboardConfigModel.updated_at.desc()).first()
    dash_config = json.loads(dash_rec.config_json) if dash_rec and dash_rec.config_json else []

    # Saved training runs
    t_recs = db.query(TrainingRunModel).filter(
        TrainingRunModel.dataset_id == dataset_id
    ).order_by(TrainingRunModel.run_at.desc()).all()
    training_runs = []
    for tr in t_recs:
        training_runs.append({
            "run_id": tr.id,
            "target_column": tr.target_column,
            "features": json.loads(tr.features_json) if tr.features_json else [],
            "model_name": tr.model_name,
            "metrics": json.loads(tr.metrics_json) if tr.metrics_json else {},
            "run_at": tr.run_at.isoformat() if tr.run_at else None
        })

    # Saved chat history
    chat_rec = db.query(ChatConversationModel).filter(
        ChatConversationModel.dataset_id == dataset_id
    ).order_by(ChatConversationModel.updated_at.desc()).first()
    chat_history = json.loads(chat_rec.messages_json) if chat_rec and chat_rec.messages_json else []

    return {
        "dataset": metadata,
        "dashboard_config": dash_config,
        "training_runs": training_runs,
        "chat_history": chat_history
    }


@router.post("/datasets/{dataset_id}/dashboard")
def save_user_dashboard(
    dataset_id: str,
    payload: DashboardSaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rec = db.query(DatasetModel).filter(
        DatasetModel.id == dataset_id,
        DatasetModel.user_id == current_user.id
    ).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found or access denied."
        )

    dash_rec = db.query(DashboardConfigModel).filter(
        DashboardConfigModel.dataset_id == dataset_id
    ).first()

    config_str = json.dumps(payload.items)
    if not dash_rec:
        dash_rec = DashboardConfigModel(
            user_id=current_user.id,
            dataset_id=dataset_id,
            config_json=config_str
        )
        db.add(dash_rec)
    else:
        dash_rec.config_json = config_str
        dash_rec.user_id = current_user.id

    db.commit()
    return {"status": "ok", "message": "Dashboard configuration saved."}


@router.post("/datasets/{dataset_id}/ds-state")
def save_user_ds_state(
    dataset_id: str,
    payload: DSStateSaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rec = db.query(DatasetModel).filter(
        DatasetModel.id == dataset_id,
        DatasetModel.user_id == current_user.id
    ).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found or access denied."
        )

    run_rec = TrainingRunModel(
        user_id=current_user.id,
        dataset_id=dataset_id,
        target_column=payload.target_column,
        features_json=json.dumps(payload.features),
        model_name=payload.model_name,
        metrics_json=json.dumps(payload.metrics or {})
    )
    db.add(run_rec)
    db.commit()
    return {"status": "ok", "run_id": run_rec.id, "message": "Data Science state saved."}


@router.delete("/datasets/{dataset_id}")
def delete_user_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently delete a saved activity and all associated state (DB blob, dashboards, ML models, chat, local file).
    """
    rec = db.query(DatasetModel).filter(
        DatasetModel.id == dataset_id,
        DatasetModel.user_id == current_user.id
    ).first()

    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved dataset '{dataset_id}' not found or access denied."
        )

    # Delete local file and database blob
    delete_dataset_file(file_id=dataset_id, filename=rec.filename, user_id=current_user.id, db=db)

    # Remove in-memory session if loaded
    remove_dataset(dataset_id)

    # Delete dataset DB record (cascades to dashboards, training_runs, conversations, blob)
    db.delete(rec)
    db.commit()

    return {
        "status": "deleted",
        "file_id": dataset_id,
        "message": f"Saved activity '{rec.filename}' deleted successfully."
    }
