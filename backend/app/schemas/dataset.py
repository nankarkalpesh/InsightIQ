from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthOverview(BaseModel):
    total_rows: int
    total_columns: int
    missing_cells: int
    missing_percentage: float
    duplicate_rows: int
    duplicate_percentage: float
    quality_score: float
    constant_columns: List[str]
    likely_id_columns: List[str]


class ColumnSchemaItem(BaseModel):
    name: str
    dtype: str
    unique_count: int
    null_count: int
    null_percentage: float
    sample_value: Optional[Any] = None


class NumericColumnStats(BaseModel):
    mean: Optional[float] = None
    median: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    std: Optional[float] = None


class CategoricalValueCount(BaseModel):
    value: str
    count: int


class CategoricalColumnStats(BaseModel):
    top_values: List[CategoricalValueCount]


class DatetimeColumnStats(BaseModel):
    min: Optional[str] = None
    max: Optional[str] = None
    range_days: Optional[float] = None


class ColumnStatisticsResponse(BaseModel):
    numeric: Dict[str, NumericColumnStats]
    categorical: Dict[str, CategoricalColumnStats]
    datetime: Dict[str, DatetimeColumnStats]


class DatasetOverviewResponse(BaseModel):
    file_id: str
    health: HealthOverview
    schema_info: List[ColumnSchemaItem] = Field(..., alias="schema")
    statistics: ColumnStatisticsResponse
    insights: List[str]

    model_config = {"populate_by_name": True}


class PaginatedPreviewResponse(BaseModel):
    file_id: str
    page: int
    page_size: int
    total_rows: int
    total_pages: int
    data: List[Dict[str, Any]]


class RecommendedKPI(BaseModel):
    kpi_name: str
    value: Optional[Any] = None
    definition: str
    required_columns: List[str]
    calculation_logic: str
    reason: str
    dax: str


class KPIRecommendationResponse(BaseModel):
    file_id: str
    total_kpis: int
    message: Optional[str] = None
    kpis: List[RecommendedKPI]


class RecommendedChart(BaseModel):
    chart_type: str
    title: str
    x_axis: str
    y_axis: str
    legend: Optional[str] = None
    aggregation: str
    suggested_filters: List[str] = Field(default_factory=list)
    sort: str
    top_n: Optional[int] = None
    date_granularity: Optional[str] = None
    reason: str


class ChartRecommendationResponse(BaseModel):
    file_id: str
    total_charts: int
    message: Optional[str] = None
    charts: List[RecommendedChart]


class ChartDataPoint(BaseModel):
    name: Optional[str] = None
    value: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None


class ChartDataResponse(BaseModel):
    file_id: str
    x_axis: str
    y_axis: str
    aggregation: str
    chart_type: str
    total_points: int
    data: List[ChartDataPoint]


class TargetCandidate(BaseModel):
    column: str
    problem_type: str
    unique_value_count: int
    raw_unique_value_count: Optional[int] = None
    distribution: Dict[str, Any]
    reason: str
    rank_score: float
    data_quality_note: Optional[str] = None


class TargetCandidatesResponse(BaseModel):
    file_id: str
    total_candidates: int
    execution_time_ms: Optional[float] = None
    message: Optional[str] = None
    candidates: List[TargetCandidate]


class FeatureCandidate(BaseModel):
    name: str
    column: str
    is_categorical: bool = False
    distinct_values: Optional[List[str]] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    mean_val: Optional[float] = None
    status: str
    reason: str
    data_quality_note: Optional[str] = None


class FeatureCandidatesResponse(BaseModel):
    file_id: str
    target: str
    total_features: int
    recommended_count: int
    features: List[FeatureCandidate]


class ModelRecommendation(BaseModel):
    model_name: str
    problem_type: str
    suitability_score: float
    why: str
    advantages: List[str]
    limitations: List[str]
    recommended_for_baseline: bool


class ModelRecommendationsResponse(BaseModel):
    file_id: str
    target: str
    problem_type: str
    total_models: int
    data_quality_note: Optional[str] = None
    recommendations: List[ModelRecommendation]


class ModelTrainingRequest(BaseModel):
    target: str
    features: List[str]
    model_name: str


class ConfusionMatrixData(BaseModel):
    labels: List[str]
    matrix: List[List[int]]


class ClassificationMetrics(BaseModel):
    accuracy: float
    baseline_accuracy: float
    precision: float
    recall: float
    f1: float
    confusion_matrix: ConfusionMatrixData
    roc_auc: Optional[float] = None


class RegressionMetrics(BaseModel):
    mae: float
    mse: float
    rmse: float
    r2: float


class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float


class ModelTrainingResponse(BaseModel):
    training_run_id: str
    file_id: str
    target: str
    model_name: str
    problem_type: str
    train_row_count: int
    test_row_count: int
    training_time_seconds: float
    classification_metrics: Optional[ClassificationMetrics] = None
    regression_metrics: Optional[RegressionMetrics] = None
    feature_importance: List[FeatureImportanceItem] = []
    data_quality_note: Optional[str] = None


class PredictRequest(BaseModel):
    training_run_id: str
    input_values: Dict[str, Any]


class ClassProbability(BaseModel):
    label: str
    probability: float


class PredictResponse(BaseModel):
    training_run_id: str
    problem_type: str
    predicted_class: Optional[str] = None
    probabilities: Optional[List[ClassProbability]] = None
    predicted_value: Optional[float] = None


