import io
import json
import joblib
import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.core.session import store_dataset
from app.datascience.model_training import train_and_evaluate_model

client = TestClient(app)


@pytest.fixture
def sample_export_ds():
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "weapon_used": np.random.choice(["Knife", "Gun", "Bat"], size=n),
        "severity": np.random.choice(["High", "Low"], size=n),
        "suspect_age": np.random.randint(18, 70, size=n),
        "reported_online": np.random.choice(["Yes", "No"], size=n)
    })
    file_id = "test_file_export"
    store_dataset(file_id, df)
    return file_id, df


def test_export_model_success(sample_export_ds):
    file_id, df = sample_export_ds
    train_res = train_and_evaluate_model(
        file_id=file_id,
        df=df,
        target_col="reported_online",
        feature_cols=["severity", "suspect_age"],
        model_name="Random Forest"
    )
    run_id = train_res["training_run_id"]

    res = client.get(f"/api/dataset/{file_id}/export/model?training_run_id={run_id}")
    assert res.status_code == 200
    assert "attachment; filename=" in res.headers["content-disposition"]
    assert ".joblib" in res.headers["content-disposition"]

    # Verify joblib stream can be unpickled/loaded
    buf = io.BytesIO(res.content)
    pipeline = joblib.load(buf)
    assert hasattr(pipeline, "predict")


def test_export_predictions_csv_success(sample_export_ds):
    file_id, df = sample_export_ds
    train_res = train_and_evaluate_model(
        file_id=file_id,
        df=df,
        target_col="reported_online",
        feature_cols=["severity", "suspect_age"],
        model_name="Decision Tree"
    )
    run_id = train_res["training_run_id"]

    res = client.get(f"/api/dataset/{file_id}/export/predictions?training_run_id={run_id}")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]

    # Load returned CSV
    df_pred = pd.read_csv(io.BytesIO(res.content))
    assert len(df_pred) == len(df)
    assert "severity" in df_pred.columns
    assert "suspect_age" in df_pred.columns
    assert "actual_reported_online" in df_pred.columns
    assert "predicted_reported_online" in df_pred.columns


def test_export_metrics_json_success(sample_export_ds):
    file_id, df = sample_export_ds
    train_res = train_and_evaluate_model(
        file_id=file_id,
        df=df,
        target_col="reported_online",
        feature_cols=["severity", "suspect_age"],
        model_name="Logistic Regression"
    )
    run_id = train_res["training_run_id"]

    res = client.get(f"/api/dataset/{file_id}/export/metrics?training_run_id={run_id}")
    assert res.status_code == 200
    assert "application/json" in res.headers["content-type"]

    json_data = res.json()
    assert json_data["training_run_id"] == run_id
    assert json_data["target"] == "reported_online"
    assert json_data["model_name"] == "Logistic Regression"
    assert "classification_metrics" in json_data


def test_export_code_python_success(sample_export_ds):
    file_id, df = sample_export_ds
    train_res = train_and_evaluate_model(
        file_id=file_id,
        df=df,
        target_col="reported_online",
        feature_cols=["severity", "suspect_age"],
        model_name="Random Forest"
    )
    run_id = train_res["training_run_id"]

    res = client.get(f"/api/dataset/{file_id}/export/code?training_run_id={run_id}")
    assert res.status_code == 200

    code_text = res.text
    assert "TARGET_COL = \"reported_online\"" in code_text
    assert "\"severity\"" in code_text
    assert "\"suspect_age\"" in code_text
    assert "RandomForestClassifier" in code_text
    assert "ColumnTransformer" in code_text


def test_export_missing_run_id_404(sample_export_ds):
    file_id, _ = sample_export_ds
    bad_run_id = "run_nonexistent_999"

    for endpoint in ["model", "predictions", "metrics", "code"]:
        res = client.get(f"/api/dataset/{file_id}/export/{endpoint}?training_run_id={bad_run_id}")
        assert res.status_code == 404
        assert "not found or expired" in res.json()["detail"]
