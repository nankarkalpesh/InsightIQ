import io
import json
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from fastapi import Response, HTTPException

from app.core.session import get_trained_model, get_dataset
from app.core.exceptions import FileNotFoundErrorCustom


def _get_validated_model(file_id: str, training_run_id: str) -> Dict[str, Any]:
    """Helper to fetch and validate training run session for a dataset."""
    try:
        model_data = get_trained_model(training_run_id)
    except FileNotFoundErrorCustom:
        raise HTTPException(
            status_code=404,
            detail=f"Training run '{training_run_id}' not found or expired. Please train a model first."
        )

    if model_data.get("file_id") != file_id:
        raise HTTPException(
            status_code=404,
            detail=f"Training run '{training_run_id}' does not belong to dataset '{file_id}'."
        )

    return model_data


def export_trained_model(file_id: str, training_run_id: str) -> Response:
    """Serialize and return fitted sklearn pipeline as a downloadable .joblib file."""
    model_data = _get_validated_model(file_id, training_run_id)
    pipeline = model_data["pipeline"]
    model_name = model_data["model_name"]

    buf = io.BytesIO()
    joblib.dump(pipeline, buf)
    buf.seek(0)

    slug = model_name.lower().replace(" ", "_")
    filename = f"model_{slug}_{training_run_id}.joblib"

    return Response(
        content=buf.getvalue(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


def export_predictions_csv(file_id: str, training_run_id: str) -> Response:
    """Generate and return test set/full dataset predictions as a downloadable CSV."""
    model_data = _get_validated_model(file_id, training_run_id)
    df = get_dataset(file_id)

    pipeline = model_data["pipeline"]
    target_col = model_data["target"]
    features = model_data["features"]
    problem_type = model_data["problem_type"]

    # Filter rows with valid target values
    df_clean = df.dropna(subset=[target_col]).copy()
    X = df_clean[features]
    y_actual = df_clean[target_col]

    preds = pipeline.predict(X)

    export_df = df_clean[features].copy()
    export_df[f"actual_{target_col}"] = y_actual.values
    export_df[f"predicted_{target_col}"] = preds

    if "classification" in problem_type and hasattr(pipeline, "predict_proba"):
        try:
            probas = pipeline.predict_proba(X)
            max_probas = np.max(probas, axis=1)
            export_df["prediction_confidence"] = np.round(max_probas, 4)
        except Exception:
            pass

    csv_text = export_df.to_csv(index=False)
    filename = f"predictions_{training_run_id}.csv"

    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


def export_metrics_json(file_id: str, training_run_id: str) -> Response:
    """Return complete training response metadata as a downloadable JSON file."""
    model_data = _get_validated_model(file_id, training_run_id)
    full_response = model_data.get("full_response", {
        "training_run_id": training_run_id,
        "file_id": file_id,
        "target": model_data["target"],
        "model_name": model_data["model_name"],
        "problem_type": model_data["problem_type"],
        "feature_importance": model_data.get("feature_importance", [])
    })

    json_text = json.dumps(full_response, indent=2)
    filename = f"metrics_{training_run_id}.json"

    return Response(
        content=json_text,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


def export_reproduction_code(file_id: str, training_run_id: str) -> Response:
    """Generate standalone, runnable Python code to reproduce the exact training pipeline."""
    model_data = _get_validated_model(file_id, training_run_id)

    target = model_data["target"]
    features = model_data["features"]
    model_name = model_data["model_name"]
    problem_type = model_data["problem_type"]
    is_classification = "classification" in problem_type

    model_code_map = {
        "Logistic Regression": "LogisticRegression(max_iter=1000, random_state=42)",
        "Random Forest": "RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=42)",
        "Gradient Boosting": "GradientBoostingClassifier(random_state=42)",
        "Decision Tree": "DecisionTreeClassifier(random_state=42)",
        "SVM": "SVC(probability=True, random_state=42)",
        "Linear Regression": "LinearRegression()",
        "Random Forest Regressor": "RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=42)",
        "Gradient Boosting Regressor": "GradientBoostingRegressor(random_state=42)",
        "Decision Tree Regressor": "DecisionTreeRegressor(random_state=42)",
    }

    instantiation = model_code_map.get(model_name, "RandomForestClassifier(random_state=42)")

    imports = [
        "import pandas as pd",
        "import numpy as np",
        "from sklearn.model_selection import train_test_split",
        "from sklearn.compose import ColumnTransformer",
        "from sklearn.pipeline import Pipeline",
        "from sklearn.impute import SimpleImputer",
        "from sklearn.preprocessing import StandardScaler, OneHotEncoder",
    ]

    if "Logistic" in model_name:
        imports.append("from sklearn.linear_model import LogisticRegression")
    elif "Linear" in model_name:
        imports.append("from sklearn.linear_model import LinearRegression")
    elif "Random Forest" in model_name and is_classification:
        imports.append("from sklearn.ensemble import RandomForestClassifier")
    elif "Random Forest" in model_name:
        imports.append("from sklearn.ensemble import RandomForestRegressor")
    elif "Gradient" in model_name and is_classification:
        imports.append("from sklearn.ensemble import GradientBoostingClassifier")
    elif "Gradient" in model_name:
        imports.append("from sklearn.ensemble import GradientBoostingRegressor")
    elif "Decision" in model_name and is_classification:
        imports.append("from sklearn.tree import DecisionTreeClassifier")
    elif "Decision" in model_name:
        imports.append("from sklearn.tree import DecisionTreeRegressor")
    elif "SVM" in model_name:
        imports.append("from sklearn.svm import SVC")

    if is_classification:
        imports.append("from sklearn.metrics import accuracy_score, classification_report")
    else:
        imports.append("from sklearn.metrics import mean_squared_error, r2_score")

    imports_str = "\n".join(sorted(list(set(imports))))

    code_template = f'''"""
InsightIQ Machine Learning Pipeline Reproduction Script
Generated for Training Run: {training_run_id}
Model: {model_name}
Target Column: {target}
"""

{imports_str}

# 1. Configuration
TARGET_COL = "{target}"
FEATURE_COLS = {json.dumps(features, indent=4)}
MODEL_NAME = "{model_name}"


def train_pipeline(csv_file_path: str):
    print(f"Loading dataset from: {{csv_file_path}}")
    df = pd.read_csv(csv_file_path)

    # Filter dataset
    df_clean = df.dropna(subset=[TARGET_COL]).copy()
    X = df_clean[FEATURE_COLS]
    y = df_clean[TARGET_COL]

    # Identify numeric and categorical feature columns
    numeric_cols = [c for c in FEATURE_COLS if pd.api.types.is_numeric_dtype(X[c])]
    categorical_cols = [c for c in FEATURE_COLS if c not in numeric_cols]

    print(f"Features: {{len(numeric_cols)}} numeric, {{len(categorical_cols)}} categorical")

    # 2. Build ColumnTransformer Preprocessor
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

    preprocessor = ColumnTransformer(transformers=transformers)

    # 3. Build Estimator Pipeline
    model = {instantiation}
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('model', model)
    ])

    # 4. Train / Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print(f"Training on {{len(X_train)}} samples, testing on {{len(X_test)}} samples...")
    pipeline.fit(X_train, y_train)

    # 5. Evaluate Model
    y_pred = pipeline.predict(X_test)
    {"print('Test Accuracy:', accuracy_score(y_test, y_pred))" if is_classification else "print('Test R2 Score:', r2_score(y_test, y_pred))"}
    {"print('\\nClassification Report:\\n', classification_report(y_test, y_pred))" if is_classification else "print('Test RMSE:', np.sqrt(mean_squared_error(y_test, y_pred)))"}

    return pipeline


if __name__ == "__main__":
    import sys
    dataset_path = sys.argv[1] if len(sys.argv) > 1 else "your_dataset.csv"
    train_pipeline(dataset_path)
'''

    slug = model_name.lower().replace(" ", "_")
    filename = f"train_{slug}_{training_run_id}.py"

    return Response(
        content=code_template,
        media_type="text/x-python",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
