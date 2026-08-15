from typing import Dict, List, Any, Optional
import pandas as pd

from app.datascience.ml_profiling import detect_ml_problem_hints, evaluate_feature_candidates


def recommend_models(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: Optional[List[str]] = None
) -> dict:
    """
    Deterministic ML model recommendations based on:
    - Target problem_type (binary_classification, multiclass_classification, or regression)
    - Dataset row count
    - User-selected feature count and feature type mix (numeric vs categorical)
    """
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset.")

    row_count = len(df)
    if row_count == 0:
        raise ValueError("Dataset is empty. Cannot recommend ML models.")

    # 1. Determine problem_type
    problem_type: Optional[str] = None

    # Check AI target candidates first
    hints = detect_ml_problem_hints(df)
    for cand in hints.get("candidates", []):
        if cand["column"] == target_col:
            problem_type = cand["problem_type"]
            break

    # Direct fallback classification if not in AI target candidates
    if not problem_type:
        target_series = df[target_col].dropna()
        nunique = int(target_series.nunique())

        if nunique == 2:
            problem_type = "binary_classification"
        elif 2 < nunique <= 50 and not pd.api.types.is_float_dtype(target_series):
            problem_type = "multiclass_classification"
        elif pd.api.types.is_numeric_dtype(target_series) and nunique > 20:
            problem_type = "regression"
        elif 2 < nunique <= 50:
            problem_type = "multiclass_classification"
        else:
            raise ValueError(
                f"Target column '{target_col}' is not a valid classification or regression target "
                f"(has {nunique} unique values). Please select a target candidate from /target-candidates first."
            )

    # 2. Feature Analysis (using user-selected features or AI recommended features fallback)
    selected_features: List[str] = []

    if feature_cols:
        # Filter provided feature_cols to ensure they exist in df and are not the target
        selected_features = [
            str(c) for c in feature_cols if str(c) in df.columns and str(c) != target_col
        ]

    if not selected_features:
        feature_eval = evaluate_feature_candidates(df, target_col)
        selected_features = [
            f["column"] for f in feature_eval.get("features", []) if f["status"] == "recommended"
        ]

    if not selected_features:
        selected_features = [str(c) for c in df.columns if str(c) != target_col]

    # Calculate feature type mix on selected_features ONLY
    num_numeric = 0
    num_categorical = 0

    for c in selected_features:
        s = df[c].dropna()
        if pd.api.types.is_numeric_dtype(s):
            num_numeric += 1
        else:
            num_categorical += 1

    total_features = len(selected_features)

    # 3. Small dataset warning note
    data_quality_note: Optional[str] = None
    if row_count < 50:
        data_quality_note = (
            f"Small dataset warning: Dataset has only {row_count} records. "
            f"Model predictions and evaluation metrics may be unreliable due to small sample size."
        )

    # 4. Build Model Recommendations Catalog
    models: List[dict] = []

    is_classification = problem_type in ("binary_classification", "multiclass_classification")

    if is_classification:
        # Logistic Regression
        lr_score = 85.0
        if num_numeric > 0:
            lr_score += 3.0
        if num_categorical > num_numeric:
            lr_score -= 5.0

        models.append({
            "model_name": "Logistic Regression",
            "problem_type": problem_type,
            "suitability_score": round(min(100.0, max(0.0, lr_score)), 1),
            "why": f"Provides an interpretable linear decision boundary for predicting '{target_col}' using {total_features} features across {row_count} records.",
            "advantages": [
                "Highly interpretable with direct odds-ratio coefficient weights",
                "Fast training and low memory overhead",
                "Low risk of overfitting on structured tabular data"
            ],
            "limitations": [
                "Assumes linear decision boundaries between features and log-odds",
                "May struggle with complex non-linear feature interactions"
            ],
            "recommended_for_baseline": True
        })

        # Random Forest
        rf_score = 92.0
        if num_categorical > 0 and num_numeric > 0:
            rf_score += 4.0
        if row_count >= 500:
            rf_score += 2.0

        models.append({
            "model_name": "Random Forest",
            "problem_type": problem_type,
            "suitability_score": round(min(100.0, max(0.0, rf_score)), 1),
            "why": f"Handles the mix of {num_numeric} numeric and {num_categorical} categorical features across {row_count} rows without requiring feature scaling.",
            "advantages": [
                "Captures non-linear relationships and complex feature interactions",
                "Resistant to outliers and collinear features",
                "Provides built-in feature importance rankings"
            ],
            "limitations": [
                "Less interpretable than linear models ('black-box')",
                "Higher compute and memory consumption during inference"
            ],
            "recommended_for_baseline": False
        })

        # Gradient Boosting
        gb_score = 90.0
        if row_count >= 1000:
            gb_score += 4.0
        if row_count < 100:
            gb_score -= 8.0

        models.append({
            "model_name": "Gradient Boosting",
            "problem_type": problem_type,
            "suitability_score": round(min(100.0, max(0.0, gb_score)), 1),
            "why": f"Sequentially optimizes decision trees, offering state-of-the-art accuracy for structured tabular data with {row_count} records.",
            "advantages": [
                "Top predictive accuracy on tabular classification benchmarks",
                "Effectively handles class imbalance and non-linear patterns",
                "Provides granular feature importance rankings"
            ],
            "limitations": [
                "Prone to overfitting if hyperparameters are not tuned",
                "Slower training times compared to single trees or linear models"
            ],
            "recommended_for_baseline": False
        })

        # Decision Tree
        models.append({
            "model_name": "Decision Tree",
            "problem_type": problem_type,
            "suitability_score": 75.0,
            "why": f"Simple rule-based decision tree for classifying '{target_col}' into distinct categories.",
            "advantages": [
                "Completely transparent and easy to visualize as decision rules",
                "No feature scaling or normalization required",
                "Handles both numeric and categorical features natively"
            ],
            "limitations": [
                "High variance and prone to overfitting single trees",
                "Sensitive to small perturbations in training data"
            ],
            "recommended_for_baseline": False
        })

        # SVM (Only if row_count < 10,000)
        if row_count < 10000:
            svm_score = 72.0
            if row_count > 5000:
                svm_score -= 10.0

            models.append({
                "model_name": "SVM",
                "problem_type": problem_type,
                "suitability_score": round(min(100.0, max(0.0, svm_score)), 1),
                "why": f"Finds optimal maximum-margin hyperplanes for classifying '{target_col}'.",
                "advantages": [
                    "Effective in high-dimensional feature spaces",
                    "Robust against overfitting in small-to-medium sample regimes"
                ],
                "limitations": [
                    "Scales quadratically to cubically O(N^2 - N^3) with row count",
                    "Requires feature scaling and probability calibration"
                ],
                "recommended_for_baseline": False
            })

    else:
        # Regression Problem Type
        # Linear Regression
        lin_score = 82.0
        if num_numeric > num_categorical:
            lin_score += 3.0

        models.append({
            "model_name": "Linear Regression",
            "problem_type": "regression",
            "suitability_score": round(min(100.0, max(0.0, lin_score)), 1),
            "why": f"Provides an interpretable linear baseline predicting continuous target '{target_col}' using {total_features} features.",
            "advantages": [
                "Highly interpretable coefficient weights",
                "Fast computation with explicit statistical confidence intervals",
                "Minimal risk of overfitting"
            ],
            "limitations": [
                "Assumes strictly linear relationship between features and target",
                "Sensitive to extreme numeric outliers and multicollinearity"
            ],
            "recommended_for_baseline": True
        })

        # Random Forest Regressor
        rf_reg_score = 92.0
        if num_categorical > 0 and num_numeric > 0:
            rf_reg_score += 4.0
        if row_count >= 500:
            rf_reg_score += 2.0

        models.append({
            "model_name": "Random Forest Regressor",
            "problem_type": "regression",
            "suitability_score": round(min(100.0, max(0.0, rf_reg_score)), 1),
            "why": f"Ensemble of decision trees capturing non-linear interactions across {total_features} features to predict continuous '{target_col}'.",
            "advantages": [
                "Captures complex non-linear patterns without manual feature transformations",
                "Resistant to outliers and non-normal target distributions",
                "Provides built-in feature importance metrics"
            ],
            "limitations": [
                "Cannot extrapolate predictions beyond the training target range",
                "Larger model footprint and memory requirements"
            ],
            "recommended_for_baseline": False
        })

        # Gradient Boosting Regressor
        gb_reg_score = 90.0
        if row_count >= 1000:
            gb_reg_score += 4.0
        if row_count < 100:
            gb_reg_score -= 8.0

        models.append({
            "model_name": "Gradient Boosting Regressor",
            "problem_type": "regression",
            "suitability_score": round(min(100.0, max(0.0, gb_reg_score)), 1),
            "why": f"Iteratively minimizes squared error loss to deliver high regression accuracy on {row_count} records.",
            "advantages": [
                "Top-tier predictive accuracy for tabular regression tasks",
                "Captures high-order feature interactions automatically",
                "Flexible loss function optimization"
            ],
            "limitations": [
                "Requires hyperparameter tuning to prevent overfitting",
                "Longer training times on large datasets"
            ],
            "recommended_for_baseline": False
        })

        # Decision Tree Regressor
        models.append({
            "model_name": "Decision Tree Regressor",
            "problem_type": "regression",
            "suitability_score": 72.0,
            "why": f"Single decision tree mapping features to piecewise constant target estimates for '{target_col}'.",
            "advantages": [
                "Simple rule-based interpretability",
                "No feature scaling required"
            ],
            "limitations": [
                "Piecewise constant predictions lack smooth curve fitting",
                "Prone to high variance and overfitting"
            ],
            "recommended_for_baseline": False
        })

    # Sort by suitability_score descending
    models.sort(key=lambda m: m["suitability_score"], reverse=True)

    return {
        "target": target_col,
        "problem_type": problem_type,
        "total_models": len(models),
        "data_quality_note": data_quality_note,
        "recommendations": models
    }
