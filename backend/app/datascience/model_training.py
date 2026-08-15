import math
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

# Classification Estimators
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC

# Regression Estimators
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor

# Evaluation Metrics
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

from app.datascience.ml_profiling import detect_ml_problem_hints, evaluate_feature_candidates, normalize_categorical_series
from app.core.session import store_trained_model

CLASSIFICATION_MODELS = {
    "Logistic Regression": lambda: LogisticRegression(max_iter=1000, random_state=42),
    "Random Forest": lambda: RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=42),
    "Gradient Boosting": lambda: GradientBoostingClassifier(random_state=42),
    "Decision Tree": lambda: DecisionTreeClassifier(random_state=42),
    "SVM": lambda: SVC(probability=True, random_state=42),
}

REGRESSION_MODELS = {
    "Linear Regression": lambda: LinearRegression(),
    "Random Forest Regressor": lambda: RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=42),
    "Gradient Boosting Regressor": lambda: GradientBoostingRegressor(random_state=42),
    "Decision Tree Regressor": lambda: DecisionTreeRegressor(random_state=42),
}


def train_and_evaluate_model(
    file_id: str,
    df: pd.DataFrame,
    target_col: str,
    feature_cols: List[str],
    model_name: str
) -> dict:
    """
    Builds a scikit-learn Pipeline (ColumnTransformer preprocessing + estimator),
    performs train/test split, fits pipeline, evaluates on test set, calculates
    feature importances, and stores fitted pipeline in session.
    Filters out non-predictive / excluded feature candidates (e.g. coordinates, IDs)
    and attaches honest data_quality_notes for weak models or excluded columns.
    """
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset.")

    # Validate feature columns against ML profiling engine (drop non-predictive/excluded features like coordinates & IDs)
    feature_eval = evaluate_feature_candidates(df, target_col)
    eval_map = {f["column"]: f for f in feature_eval.get("features", [])}

    valid_features: List[str] = []
    dropped_features_info: List[str] = []

    for f in feature_cols:
        col_str = str(f)
        if col_str not in df.columns or col_str == target_col:
            continue
        c_info = eval_map.get(col_str)
        if c_info and c_info["status"].startswith("excluded"):
            dropped_features_info.append(f"{col_str} ({c_info['reason']})")
        else:
            valid_features.append(col_str)

    if not valid_features:
        exclusion_summary = "; ".join(dropped_features_info) if dropped_features_info else "No valid columns provided."
        raise ValueError(
            f"None of the provided features are valid for ML model training. "
            f"Exclusions: {exclusion_summary}"
        )

    # Drop NaNs in target column
    df_clean = df[[target_col] + valid_features].dropna(subset=[target_col]).copy()
    if len(df_clean) < 10:
        raise ValueError(
            f"Dataset has only {len(df_clean)} valid rows after dropping target NaNs. "
            f"At least 10 rows are required for model training."
        )

    # Normalize categorical target column if applicable (cleans dirty variants like "yes", "YES", "True", "1" -> "Yes")
    if not pd.api.types.is_numeric_dtype(df_clean[target_col]):
        norm_series, _, _, _ = normalize_categorical_series(df_clean[target_col])
        df_clean[target_col] = norm_series

    # 1. Determine problem_type
    problem_type: Optional[str] = None
    hints = detect_ml_problem_hints(df)
    for cand in hints.get("candidates", []):
        if cand["column"] == target_col:
            problem_type = cand["problem_type"]
            break

    if not problem_type:
        target_series = df_clean[target_col]
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
            raise ValueError(f"Target column '{target_col}' is not a valid classification or regression target.")

    is_classification = problem_type in ("binary_classification", "multiclass_classification")

    # 2. Instantiate Estimator
    if is_classification:
        if model_name not in CLASSIFICATION_MODELS:
            raise ValueError(
                f"Model '{model_name}' is not a recognized classification model. "
                f"Available: {list(CLASSIFICATION_MODELS.keys())}"
            )
        estimator = CLASSIFICATION_MODELS[model_name]()
    else:
        if model_name not in REGRESSION_MODELS:
            raise ValueError(
                f"Model '{model_name}' is not a recognized regression model. "
                f"Available: {list(REGRESSION_MODELS.keys())}"
            )
        estimator = REGRESSION_MODELS[model_name]()

    # 3. Build ColumnTransformer Preprocessor
    numeric_cols = [c for c in valid_features if pd.api.types.is_numeric_dtype(df_clean[c])]
    categorical_cols = [c for c in valid_features if c not in numeric_cols]

    transformers = []
    if numeric_cols:
        num_pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])
        transformers.append(('num', num_pipeline, numeric_cols))

    if categorical_cols:
        cat_pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('encoder', OneHotEncoder(max_categories=40, handle_unknown='ignore', sparse_output=False))
        ])
        transformers.append(('cat', cat_pipeline, categorical_cols))

    if not transformers:
        raise ValueError("No valid numeric or categorical features available for preprocessing.")

    preprocessor = ColumnTransformer(transformers=transformers)

    # Full Pipeline
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('model', estimator)
    ])

    # 4. Train/Test Split (80/20, fixed random_state=42)
    X = df_clean[valid_features]
    y = df_clean[target_col]

    stratify_val = None
    if is_classification:
        y_counts = y.value_counts()
        if (y_counts >= 2).all() and len(y_counts) > 1:
            stratify_val = y

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify_val
    )

    # 5. Fit Pipeline & Track Time
    t0 = time.perf_counter()
    pipeline.fit(X_train, y_train)
    training_time_seconds = round(time.perf_counter() - t0, 3)

    # 6. Evaluate on Test Set
    y_pred = pipeline.predict(X_test)

    classification_metrics = None
    regression_metrics = None

    if is_classification:
        acc = round(float(accuracy_score(y_test, y_pred)), 4)
        baseline_acc = round(float(y_test.value_counts(normalize=True).max()), 4)
        prec = round(float(precision_score(y_test, y_pred, average='weighted', zero_division=0)), 4)
        rec = round(float(recall_score(y_test, y_pred, average='weighted', zero_division=0)), 4)
        f1 = round(float(f1_score(y_test, y_pred, average='weighted', zero_division=0)), 4)

        labels = sorted(list(set(y_train).union(set(y_test))))
        cm = confusion_matrix(y_test, y_pred, labels=labels)

        roc_auc: Optional[float] = None
        if problem_type == "binary_classification" and hasattr(pipeline.named_steps['model'], "predict_proba"):
            try:
                proba = pipeline.predict_proba(X_test)
                if proba.shape[1] == 2:
                    roc_auc = round(float(roc_auc_score(y_test, proba[:, 1])), 4)
            except Exception:
                roc_auc = None

        classification_metrics = {
            "accuracy": acc,
            "baseline_accuracy": baseline_acc,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "confusion_matrix": {
                "labels": [str(l) for l in labels],
                "matrix": cm.tolist()
            },
            "roc_auc": roc_auc
        }

    else:
        mae = round(float(mean_absolute_error(y_test, y_pred)), 4)
        mse = round(float(mean_squared_error(y_test, y_pred)), 4)
        rmse = round(float(np.sqrt(mse)), 4)
        r2 = round(float(r2_score(y_test, y_pred)), 4)

        regression_metrics = {
            "mae": mae,
            "mse": mse,
            "rmse": rmse,
            "r2": r2
        }

    # 7. Extract Feature Importances
    feature_importance: List[dict] = []
    try:
        fitted_preprocessor = pipeline.named_steps['preprocessor']
        feature_names = fitted_preprocessor.get_feature_names_out()
        model_step = pipeline.named_steps['model']

        raw_importances = None
        if hasattr(model_step, "feature_importances_"):
            raw_importances = model_step.feature_importances_
        elif hasattr(model_step, "coef_"):
            coefs = np.abs(model_step.coef_)
            if coefs.ndim > 1:
                raw_importances = np.mean(coefs, axis=0)
            else:
                raw_importances = coefs

        if raw_importances is not None and len(feature_names) == len(raw_importances):
            feature_map: Dict[str, float] = {}
            for feat_name, imp_val in zip(feature_names, raw_importances):
                clean_name = feat_name.replace("num__", "").replace("cat__", "")
                raw_col = next((c for c in valid_features if clean_name.startswith(c)), clean_name)
                feature_map[raw_col] = feature_map.get(raw_col, 0.0) + float(imp_val)

            total_imp = sum(feature_map.values())
            if total_imp > 0:
                for k in feature_map:
                    feature_map[k] = feature_map[k] / total_imp

            feature_importance = [
                {"feature": k, "importance": round(v, 4)}
                for k, v in sorted(feature_map.items(), key=lambda x: x[1], reverse=True)
            ]
    except Exception:
        feature_importance = [{"feature": c, "importance": round(1.0 / len(valid_features), 4)} for c in valid_features]

    # 8. Build Data Quality Notes (Excluded features, category collapse stats, small dataset, weak model warnings)
    notes: List[str] = []

    if dropped_features_info:
        dropped_names = [d.split(" (")[0] for d in dropped_features_info]
        notes.append(f"Excluded {len(dropped_names)} non-predictive feature(s) from training: {', '.join(dropped_names)}.")

    # OneHotEncoder Capped Categories Collapse Reporting
    try:
        if categorical_cols and 'cat' in preprocessor.named_transformers_:
            encoder = preprocessor.named_transformers_['cat'].named_steps['encoder']
            infrequent_cats_list = getattr(encoder, "infrequent_categories_", None)
            if infrequent_cats_list is not None:
                for col_name, inf_cats in zip(categorical_cols, infrequent_cats_list):
                    if inf_cats is not None and len(inf_cats) > 0:
                        total_cat_count = len(df_clean[col_name].dropna().unique())
                        num_collapsed = len(inf_cats)
                        preserved_count = total_cat_count - num_collapsed
                        series_clean = df_clean[col_name].dropna().astype(str)
                        inf_set = set(str(x) for x in inf_cats)
                        row_count_inf = sum(1 for val in series_clean if val in inf_set)
                        row_pct_inf = round((row_count_inf / len(series_clean)) * 100, 1) if len(series_clean) > 0 else 0.0

                        notes.append(
                            f"Feature '{col_name}' has {total_cat_count} unique categories; top {preserved_count} were preserved "
                            f"and {num_collapsed} rare categories (affecting {row_pct_inf}% of rows) were grouped into 'Other' "
                            f"to maintain training performance."
                        )
    except Exception:
        pass

    if len(df_clean) < 50:
        notes.append(f"Small dataset warning: Model was trained on only {len(df_clean)} records.")

    if is_classification and classification_metrics:
        acc = classification_metrics["accuracy"]
        baseline_acc = classification_metrics["baseline_accuracy"]
        roc_auc = classification_metrics.get("roc_auc")
        labels = classification_metrics["confusion_matrix"]["labels"]
        num_classes = len(labels)

        is_weak = False
        if problem_type == "binary_classification":
            if 0.45 <= acc <= 0.55 or (roc_auc is not None and 0.45 <= roc_auc <= 0.55) or acc <= max(baseline_acc * 1.05, baseline_acc + 0.03):
                is_weak = True
        else:
            if acc <= max(baseline_acc * 1.15, baseline_acc + 0.05):
                is_weak = True

        if is_weak:
            acc_pct = round(acc * 100, 1)
            baseline_pct = round(baseline_acc * 100, 1)
            notes.append(
                f"This model achieves {acc_pct}% accuracy, which is close to the naive majority-class baseline "
                f"of {baseline_pct}% ({num_classes} classes). The selected features provide minimal predictive lift — "
                f"consider selecting different features or target."
            )
    elif regression_metrics:
        r2 = regression_metrics["r2"]
        if r2 <= 0.05:
            notes.append(
                "This model performs close to random chance (R² <= 0.05). The selected features may not "
                "meaningfully predict this target — consider a different target or feature set."
            )

    data_quality_note = " ".join(notes) if notes else None

    training_run_id = f"run_{uuid.uuid4().hex[:8]}"

    res_dict = {
        "training_run_id": training_run_id,
        "file_id": file_id,
        "target": target_col,
        "model_name": model_name,
        "problem_type": problem_type,
        "train_row_count": len(X_train),
        "test_row_count": len(X_test),
        "training_time_seconds": training_time_seconds,
        "classification_metrics": classification_metrics,
        "regression_metrics": regression_metrics,
        "feature_importance": feature_importance,
        "data_quality_note": data_quality_note
    }

    # 9. Store Fitted Pipeline in Memory Session Store
    store_trained_model(training_run_id, {
        "training_run_id": training_run_id,
        "file_id": file_id,
        "pipeline": pipeline,
        "target": target_col,
        "features": valid_features,
        "problem_type": problem_type,
        "model_name": model_name,
        "feature_importance": feature_importance,
        "full_response": res_dict
    })

    return res_dict
