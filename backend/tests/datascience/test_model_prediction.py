import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.core.session import store_dataset
from app.datascience.model_training import train_and_evaluate_model

client = TestClient(app)


@pytest.fixture
def sample_ds():
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "feature_num": np.random.randn(n),
        "feature_cat": np.random.choice(["High", "Medium", "Low"], size=n),
        "target_cls": np.random.choice(["Alpha", "Beta"], size=n),
        "target_num": np.random.randn(n) * 10
    })
    file_id = "test_file_predict"
    store_dataset(file_id, df)
    return file_id, df


def test_predict_success_classification(sample_ds):
    file_id, df = sample_ds

    # Train model first
    train_res = train_and_evaluate_model(
        file_id=file_id,
        df=df,
        target_col="target_cls",
        feature_cols=["feature_num", "feature_cat"],
        model_name="Random Forest"
    )
    run_id = train_res["training_run_id"]

    # Predict via API endpoint
    payload = {
        "training_run_id": run_id,
        "input_values": {
            "feature_num": 0.5,
            "feature_cat": "High"
        }
    }
    response = client.post(f"/api/dataset/{file_id}/predict", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["training_run_id"] == run_id
    assert data["predicted_class"] in ["Alpha", "Beta"]
    assert data["probabilities"] is not None
    assert len(data["probabilities"]) == 2


def test_predict_missing_run_id_404(sample_ds):
    file_id, _ = sample_ds
    payload = {
        "training_run_id": "run_nonexistent_123",
        "input_values": {
            "feature_num": 0.5,
            "feature_cat": "High"
        }
    }
    response = client.post(f"/api/dataset/{file_id}/predict", json=payload)
    assert response.status_code == 404
    assert "not found or expired" in response.json()["detail"]


def test_predict_missing_feature_400(sample_ds):
    file_id, df = sample_ds

    train_res = train_and_evaluate_model(
        file_id=file_id,
        df=df,
        target_col="target_cls",
        feature_cols=["feature_num", "feature_cat"],
        model_name="Decision Tree"
    )
    run_id = train_res["training_run_id"]

    # Missing feature_cat
    payload = {
        "training_run_id": run_id,
        "input_values": {
            "feature_num": 0.5
        }
    }
    response = client.post(f"/api/dataset/{file_id}/predict", json=payload)
    assert response.status_code == 400
    assert "Missing required feature value" in response.json()["detail"]
