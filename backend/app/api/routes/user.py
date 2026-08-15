import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.db_models import User, DatasetModel, DashboardConfigModel, TrainingRunModel, ChatConversationModel
from app.core.session import store_dataset, get_dataset
from app.analytics.profiling import dataset_health, column_schema, generate_insights, column_statistics
import pandas as pd
import os

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/datasets")
def list_user_datasets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all datasets uploaded by the current logged-in user."""
    records = db.query(DatasetModel).filter(
        DatasetModel.user_id == current_user.id
    ).order_by(DatasetModel.uploaded_at.desc()).all()

    datasets = []
    for r in records:
        datasets.append({
            "file_id": r.id,
            "filename": r.filename,
            "file_type": r.file_type,
            "row_count": r.row_count,
            "column_count": r.column_count,
            "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else None
        })
    return {"datasets": datasets}


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
        get_dataset(dataset_id)
    except KeyError:
        if os.path.exists(rec.file_path):
            if rec.file_type.lower() in [".csv"]:
                df = pd.read_csv(rec.file_path)
            elif rec.file_type.lower() in [".xlsx", ".xls"]:
                df = pd.read_excel(rec.file_path)
            elif rec.file_type.lower() in [".json"]:
                df = pd.read_json(rec.file_path)
            else:
                df = pd.read_csv(rec.file_path)
            store_dataset(dataset_id, df)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset file missing from disk path '{rec.file_path}'."
            )

    df = get_dataset(dataset_id)
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
