import pytest
import pandas as pd
import numpy as np

from app.datascience.model_training import train_and_evaluate_model
from app.core.session import store_dataset, get_trained_model, has_trained_model, clear_all_sessions
from app.schemas.dataset import ModelTrainingRequest


@pytest.fixture(autouse=True)
def setup_teardown():
    clear_all_sessions()
    yield
    clear_all_sessions()


def create_sample_dataset():
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "age": np.random.randint(18, 70, size=n),
        "income": np.random.uniform(20000, 120000, size=n),
        "department": np.random.choice(["Sales", "Engineering", "HR"], size=n),
        "performance_score": np.random.uniform(1.0, 5.0, size=n),
        "target_churn": np.random.choice(["Yes", "No"], size=n, p=[0.3, 0.7]),
    })
    return df


def test_train_random_forest_classifier():
    df = create_sample_dataset()
    store_dataset("test_file_1", df)

    res = train_and_evaluate_model(
        file_id="test_file_1",
        df=df,
        target_col="target_churn",
        feature_cols=["age", "income", "department", "performance_score"],
        model_name="Random Forest"
    )

    assert res["problem_type"] == "binary_classification"
    assert res["model_name"] == "Random Forest"
    assert res["train_row_count"] == 80
    assert res["test_row_count"] == 20
    assert res["training_time_seconds"] >= 0.0

    metrics = res["classification_metrics"]
    assert metrics is not None
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert 0.0 <= metrics["baseline_accuracy"] <= 1.0
    assert 0.0 <= metrics["precision"] <= 1.0
    assert 0.0 <= metrics["recall"] <= 1.0
    assert 0.0 <= metrics["f1"] <= 1.0
    assert "labels" in metrics["confusion_matrix"]
    assert "matrix" in metrics["confusion_matrix"]
    assert len(metrics["confusion_matrix"]["labels"]) == 2

    # Verify feature importances
    feat_imp = res["feature_importance"]
    assert len(feat_imp) > 0
    total_imp = sum(item["importance"] for item in feat_imp)
    assert 0.9 <= total_imp <= 1.1

    # Verify model is stored in session store
    run_id = res["training_run_id"]
    assert has_trained_model(run_id)
    stored = get_trained_model(run_id)
    assert stored["target"] == "target_churn"
    assert stored["pipeline"] is not None


def test_train_regression_model():
    df = create_sample_dataset()
    store_dataset("test_file_2", df)

    res = train_and_evaluate_model(
        file_id="test_file_2",
        df=df,
        target_col="performance_score",
        feature_cols=["age", "income", "department"],
        model_name="Random Forest Regressor"
    )

    assert res["problem_type"] == "regression"
    assert res["model_name"] == "Random Forest Regressor"

    metrics = res["regression_metrics"]
    assert metrics is not None
    assert metrics["mae"] >= 0.0
    assert metrics["mse"] >= 0.0
    assert metrics["rmse"] >= 0.0
    assert isinstance(metrics["r2"], float)

    feat_imp = res["feature_importance"]
    assert len(feat_imp) > 0


def test_train_logistic_regression():
    df = create_sample_dataset()
    store_dataset("test_file_3", df)

    res = train_and_evaluate_model(
        file_id="test_file_3",
        df=df,
        target_col="target_churn",
        feature_cols=["age", "income", "department"],
        model_name="Logistic Regression"
    )

    assert res["problem_type"] == "binary_classification"
    assert res["classification_metrics"]["accuracy"] >= 0.0
    assert len(res["feature_importance"]) > 0


def test_invalid_target_error():
    df = create_sample_dataset()
    with pytest.raises(ValueError, match="Target column 'nonexistent' not found"):
        train_and_evaluate_model(
            file_id="test_file",
            df=df,
            target_col="nonexistent",
            feature_cols=["age"],
            model_name="Random Forest"
        )


def test_invalid_model_name_error():
    df = create_sample_dataset()
    with pytest.raises(ValueError, match="is not a recognized classification model"):
        train_and_evaluate_model(
            file_id="test_file",
            df=df,
            target_col="target_churn",
            feature_cols=["age"],
            model_name="NonExistentAlgorithm"
        )


def test_excluded_features_filtered_with_note():
    df = create_sample_dataset()
    df["latitude"] = np.random.uniform(37.0, 38.0, size=len(df))
    df["incident_id"] = [f"ID_{i}" for i in range(len(df))]
    store_dataset("test_file_excluded", df)

    res = train_and_evaluate_model(
        file_id="test_file_excluded",
        df=df,
        target_col="target_churn",
        feature_cols=["age", "income", "latitude", "incident_id"],
        model_name="Logistic Regression"
    )

    # Confirm latitude and incident_id were excluded from training features
    trained_feats = [f["feature"] for f in res["feature_importance"]]
    assert "latitude" not in trained_feats
    assert "incident_id" not in trained_feats
    assert "age" in trained_feats or "income" in trained_feats

    # Confirm data_quality_note mentions excluded columns
    note = res["data_quality_note"]
    assert note is not None
    assert "Excluded" in note
    assert "latitude" in note or "incident_id" in note


def test_weak_model_random_chance_warning():
    np.random.seed(42)
    n = 200
    df = pd.DataFrame({
        "random_noise_1": np.random.randn(n),
        "random_noise_2": np.random.randn(n),
        "target_binary": np.random.choice(["Yes", "No"], size=n, p=[0.5, 0.5])
    })
    store_dataset("test_file_weak", df)

    res = train_and_evaluate_model(
        file_id="test_file_weak",
        df=df,
        target_col="target_binary",
        feature_cols=["random_noise_1", "random_noise_2"],
        model_name="Logistic Regression"
    )

    note = res["data_quality_note"]
    assert note is not None
    assert "close to the naive majority-class baseline" in note

