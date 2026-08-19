import math
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status, Depends
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.dependencies import get_optional_user
from app.models.db_models import User, TrainingRunModel
from app.core.session import get_dataset
from app.analytics.profiling import (
    dataset_health,
    column_schema,
    column_statistics,
    generate_insights
)
from app.analytics.kpi_engine import recommend_kpis
from app.analytics.chart_engine import recommend_charts
from app.analytics.chart_data import get_chart_data
from app.datascience.ml_profiling import detect_ml_problem_hints, evaluate_feature_candidates
from app.datascience.model_recommender import recommend_models
from app.datascience.model_training import train_and_evaluate_model
from app.datascience.model_prediction import make_prediction
from app.datascience.model_export import (
    export_trained_model,
    export_predictions_csv,
    export_metrics_json,
    export_reproduction_code,
)
from app.schemas.dataset import (
    DatasetOverviewResponse,
    PaginatedPreviewResponse,
    HealthOverview,
    ColumnSchemaItem,
    ColumnStatisticsResponse,
    KPIRecommendationResponse,
    RecommendedKPI,
    ChartRecommendationResponse,
    RecommendedChart,
    ChartDataResponse,
    ChartDataPoint,
    TargetCandidate,
    TargetCandidatesResponse,
    FeatureCandidate,
    FeatureCandidatesResponse,
    ModelRecommendation,
    ModelRecommendationsResponse,
    ModelTrainingRequest,
    ModelTrainingResponse,
    PredictRequest,
    PredictResponse,
)

router = APIRouter(prefix="/dataset", tags=["dataset"])


def _clean_record(val: Any) -> Any:
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    if isinstance(val, (pd.Timestamp, np.datetime64)):
        return str(val)
    return str(val)


@router.get("/{file_id}/overview", response_model=DatasetOverviewResponse)
async def get_dataset_overview(
    file_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    df = get_dataset(file_id, db=db, current_user=current_user)

    health_data = dataset_health(df)
    schema_data = column_schema(df)
    stats_data = column_statistics(df)
    insights_data = generate_insights(df)

    return DatasetOverviewResponse(
        file_id=file_id,
        health=HealthOverview(**health_data),
        schema_info=[ColumnSchemaItem(**item) for item in schema_data],
        statistics=ColumnStatisticsResponse(**stats_data),
        insights=insights_data
    )


@router.get("/{file_id}/preview", response_model=PaginatedPreviewResponse)
async def get_dataset_preview(
    file_id: str,
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(50, ge=1, le=500, description="Number of items per page (max 500)"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    df = get_dataset(file_id, db=db, current_user=current_user)
    total_rows = len(df)

    if total_rows == 0:
        return PaginatedPreviewResponse(
            file_id=file_id,
            page=page,
            page_size=page_size,
            total_rows=0,
            total_pages=0,
            data=[]
        )

    total_pages = math.ceil(total_rows / page_size)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    slice_df = df.iloc[start_idx:end_idx]

    records: List[Dict[str, Any]] = []
    for row in slice_df.to_dict(orient="records"):
        clean_row = {str(k): _clean_record(v) for k, v in row.items()}
        records.append(clean_row)

    return PaginatedPreviewResponse(
        file_id=file_id,
        page=page,
        page_size=page_size,
        total_rows=total_rows,
        total_pages=total_pages,
        data=records
    )


@router.get("/{file_id}/kpis", response_model=KPIRecommendationResponse)
async def get_dataset_kpis(
    file_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    df = get_dataset(file_id, db=db, current_user=current_user)
    kpi_result = recommend_kpis(df, table_name="Dataset")

    return KPIRecommendationResponse(
        file_id=file_id,
        total_kpis=kpi_result["total_kpis"],
        message=kpi_result.get("message"),
        kpis=[RecommendedKPI(**item) for item in kpi_result["kpis"]]
    )


@router.get("/{file_id}/charts", response_model=ChartRecommendationResponse)
async def get_dataset_charts(
    file_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    df = get_dataset(file_id, db=db, current_user=current_user)
    chart_result = recommend_charts(df)

    return ChartRecommendationResponse(
        file_id=file_id,
        total_charts=chart_result["total_charts"],
        message=chart_result.get("message"),
        charts=[RecommendedChart(**item) for item in chart_result["charts"]]
    )


@router.get("/{file_id}/chart-data", response_model=ChartDataResponse)
async def get_dataset_chart_data(
    file_id: str,
    x_axis: str = Query(..., description="Column name for X axis"),
    y_axis: str = Query(..., description="Column name for Y axis"),
    aggregation: str = Query("SUM", description="Aggregation function: SUM, AVERAGE, COUNT, DISTINCTCOUNT, NONE"),
    chart_type: str = Query("bar", description="Chart type: bar, column, line, scatter, donut, table"),
    top_n: int | None = Query(default=None, description="Optional top N records limit"),
    date_granularity: str | None = Query(default=None, description="Optional date granularity: year, month, day"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    df = get_dataset(file_id, db=db, current_user=current_user)
    chart_data = get_chart_data(
        df=df,
        x_axis=x_axis,
        y_axis=y_axis,
        aggregation=aggregation,
        chart_type=chart_type,
        top_n=top_n,
        date_granularity=date_granularity
    )

    return ChartDataResponse(
        file_id=file_id,
        x_axis=x_axis,
        y_axis=y_axis,
        aggregation=aggregation,
        chart_type=chart_type,
        total_points=chart_data["total_points"],
        data=[ChartDataPoint(**item) for item in chart_data["data"]]
    )


@router.get("/{file_id}/target-candidates", response_model=TargetCandidatesResponse)
async def get_dataset_target_candidates(
    file_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    df = get_dataset(file_id, db=db, current_user=current_user)
    result = detect_ml_problem_hints(df)

    return TargetCandidatesResponse(
        file_id=file_id,
        total_candidates=result["total_candidates"],
        execution_time_ms=result.get("execution_time_ms"),
        message=result.get("message"),
        candidates=[TargetCandidate(**item) for item in result["candidates"]]
    )


@router.get("/{file_id}/feature-candidates", response_model=FeatureCandidatesResponse)
async def get_dataset_feature_candidates(
    file_id: str,
    target: str = Query(..., description="Target column name to evaluate features for"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    df = get_dataset(file_id, db=db, current_user=current_user)
    result = evaluate_feature_candidates(df, target_col=target)

    return FeatureCandidatesResponse(
        file_id=file_id,
        target=target,
        total_features=result["total_features"],
        recommended_count=result["recommended_count"],
        features=[FeatureCandidate(**item) for item in result["features"]]
    )


@router.get("/{file_id}/model-recommendations", response_model=ModelRecommendationsResponse)
async def get_dataset_model_recommendations(
    file_id: str,
    target: str = Query(..., description="Target column name to evaluate model recommendations for"),
    features: str | None = None,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    df = get_dataset(file_id, db=db, current_user=current_user)

    parsed_features: Optional[List[str]] = None
    if features:
        parsed_features = [f.strip() for f in features.split(",") if f.strip()]

    try:
        result = recommend_models(df, target_col=target, feature_cols=parsed_features)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )

    return ModelRecommendationsResponse(
        file_id=file_id,
        target=target,
        problem_type=result["problem_type"],
        total_models=result["total_models"],
        data_quality_note=result.get("data_quality_note"),
        recommendations=[ModelRecommendation(**m) for m in result["recommendations"]]
    )


@router.post("/{file_id}/train", response_model=ModelTrainingResponse)
async def train_dataset_model(
    file_id: str,
    payload: ModelTrainingRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    df = get_dataset(file_id, db=db, current_user=current_user)
    try:
        result = train_and_evaluate_model(
            file_id=file_id,
            df=df,
            target_col=payload.target,
            feature_cols=payload.features,
            model_name=payload.model_name
        )

        if db:
            try:
                run_rec = TrainingRunModel(
                    id=result.get("training_run_id"),
                    user_id=current_user.id if current_user else None,
                    dataset_id=file_id,
                    target_column=payload.target,
                    features_json=json.dumps(payload.features),
                    model_name=payload.model_name,
                    metrics_json=json.dumps(result.get("metrics", {}))
                )
                db.add(run_rec)
                db.commit()
            except Exception as db_err:
                db.rollback()
                # Log or swallow non-fatal DB commit error to keep model training working
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model training failed: {str(err)}"
        )

    return ModelTrainingResponse(**result)


@router.post("/{file_id}/predict", response_model=PredictResponse)
async def predict_dataset_model(
    file_id: str,
    payload: PredictRequest
):
    return make_prediction(
        file_id=file_id,
        training_run_id=payload.training_run_id,
        input_values=payload.input_values
    )


@router.get("/{file_id}/export/model")
async def export_dataset_model(
    file_id: str,
    training_run_id: str = Query(..., description="Training run ID to export model pipeline for")
):
    return export_trained_model(file_id=file_id, training_run_id=training_run_id)


@router.get("/{file_id}/export/predictions")
async def export_dataset_predictions(
    file_id: str,
    training_run_id: str = Query(..., description="Training run ID to export predictions CSV for")
):
    return export_predictions_csv(file_id=file_id, training_run_id=training_run_id)


@router.get("/{file_id}/export/metrics")
async def export_dataset_metrics(
    file_id: str,
    training_run_id: str = Query(..., description="Training run ID to export metrics JSON for")
):
    return export_metrics_json(file_id=file_id, training_run_id=training_run_id)


@router.get("/{file_id}/export/code")
async def export_dataset_reproduction_code(
    file_id: str,
    training_run_id: str = Query(..., description="Training run ID to export Python training code for")
):
    return export_reproduction_code(file_id=file_id, training_run_id=training_run_id)
