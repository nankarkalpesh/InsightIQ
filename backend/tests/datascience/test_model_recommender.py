import pytest
import pandas as pd
import numpy as np

from app.datascience.model_recommender import recommend_models


@pytest.fixture
def classification_df():
    np.random.seed(42)
    n = 200
    return pd.DataFrame({
        "feature_num1": np.random.randn(n),
        "feature_num2": np.random.exponential(2.0, n),
        "feature_cat": np.random.choice(["TypeA", "TypeB", "TypeC"], n),
        "is_fraud": np.random.choice([0, 1], n)
    })


@pytest.fixture
def regression_df():
    np.random.seed(42)
    n = 200
    return pd.DataFrame({
        "feature_num": np.random.randn(n),
        "feature_cat": np.random.choice(["RegionA", "RegionB"], n),
        "sales": np.random.uniform(100.0, 5000.0, n)
    })


def test_binary_classification_models_only(classification_df):
    result = recommend_models(classification_df, "is_fraud")

    assert result["target"] == "is_fraud"
    assert result["problem_type"] == "binary_classification"

    model_names = [m["model_name"] for m in result["recommendations"]]
    assert "Logistic Regression" in model_names
    assert "Random Forest" in model_names
    assert "Gradient Boosting" in model_names
    assert "Decision Tree" in model_names
    assert "SVM" in model_names

    # Ensure NO regression models are recommended
    assert "Linear Regression" not in model_names
    assert "Random Forest Regressor" not in model_names
    assert "Gradient Boosting Regressor" not in model_names


def test_regression_models_only(regression_df):
    result = recommend_models(regression_df, "sales")

    assert result["target"] == "sales"
    assert result["problem_type"] == "regression"

    model_names = [m["model_name"] for m in result["recommendations"]]
    assert "Linear Regression" in model_names
    assert "Random Forest Regressor" in model_names
    assert "Gradient Boosting Regressor" in model_names
    assert "Decision Tree Regressor" in model_names

    # Ensure NO classification models are recommended
    assert "Logistic Regression" not in model_names
    assert "Random Forest" not in model_names
    assert "SVM" not in model_names


def test_svm_excluded_for_large_datasets():
    np.random.seed(42)
    n = 10500
    large_df = pd.DataFrame({
        "feat1": np.random.randn(n),
        "is_churn": np.random.choice([0, 1], n)
    })

    result = recommend_models(large_df, "is_churn")
    model_names = [m["model_name"] for m in result["recommendations"]]

    assert "SVM" not in model_names
    assert "Logistic Regression" in model_names
    assert "Random Forest" in model_names


def test_exactly_one_baseline_model(classification_df, regression_df):
    cls_result = recommend_models(classification_df, "is_fraud")
    cls_baselines = [m for m in cls_result["recommendations"] if m["recommended_for_baseline"]]
    assert len(cls_baselines) == 1
    assert cls_baselines[0]["model_name"] == "Logistic Regression"

    reg_result = recommend_models(regression_df, "sales")
    reg_baselines = [m for m in reg_result["recommendations"] if m["recommended_for_baseline"]]
    assert len(reg_baselines) == 1
    assert reg_baselines[0]["model_name"] == "Linear Regression"


def test_suitability_scores_differentiated(classification_df, regression_df):
    cls_result = recommend_models(classification_df, "is_fraud")
    cls_scores = [m["suitability_score"] for m in cls_result["recommendations"]]
    assert len(set(cls_scores)) > 1

    reg_result = recommend_models(regression_df, "sales")
    reg_scores = [m["suitability_score"] for m in reg_result["recommendations"]]
    assert len(set(reg_scores)) > 1


def test_small_dataset_warning():
    small_df = pd.DataFrame({
        "x": range(30),
        "y": [i % 2 for i in range(30)]
    })

    result = recommend_models(small_df, "y")
    assert result["data_quality_note"] is not None
    assert "Small dataset warning" in result["data_quality_note"]


def test_invalid_target_error(classification_df):
    with pytest.raises(ValueError, match="Target column 'non_existent' not found"):
        recommend_models(classification_df, "non_existent")
