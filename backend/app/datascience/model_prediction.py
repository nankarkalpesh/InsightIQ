import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from fastapi import HTTPException

from app.core.session import get_trained_model
from app.core.exceptions import FileNotFoundErrorCustom


def make_prediction(
    file_id: str,
    training_run_id: str,
    input_values: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run prediction on a single user input row using a stored trained pipeline.
    """
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

    features: List[str] = model_data["features"]
    missing_features = [
        f for f in features
        if f not in input_values or input_values[f] is None or str(input_values[f]).strip() == ""
    ]

    if missing_features:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required feature value(s): {', '.join(missing_features)}."
        )

    # Coerce input dict into 1-row DataFrame
    row_dict = {}
    for f in features:
        val = input_values[f]
        # Convert numeric strings if possible
        try:
            val_num = float(val)
            row_dict[f] = val_num
        except (ValueError, TypeError):
            row_dict[f] = str(val)

    input_df = pd.DataFrame([row_dict])
    pipeline = model_data["pipeline"]
    problem_type: str = model_data["problem_type"]

    is_classification = "classification" in problem_type

    if is_classification:
        try:
            raw_pred = pipeline.predict(input_df)[0]
            predicted_class = str(raw_pred)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to execute prediction pipeline on input features: {str(e)}"
            )

        probabilities: Optional[List[Dict[str, Any]]] = None
        model_step = pipeline.named_steps.get("model")
        if hasattr(model_step, "predict_proba") or hasattr(pipeline, "predict_proba"):
            try:
                raw_probas = pipeline.predict_proba(input_df)[0]
                classes = getattr(pipeline, "classes_", getattr(model_step, "classes_", []))
                if len(classes) == len(raw_probas):
                    prob_list = [
                        {"label": str(c), "probability": round(float(p), 4)}
                        for c, p in zip(classes, raw_probas)
                    ]
                    probabilities = sorted(prob_list, key=lambda x: x["probability"], reverse=True)
            except Exception:
                probabilities = None

        return {
            "training_run_id": training_run_id,
            "problem_type": problem_type,
            "predicted_class": predicted_class,
            "probabilities": probabilities,
            "predicted_value": None
        }
    else:
        try:
            raw_val = float(pipeline.predict(input_df)[0])
            predicted_value = round(raw_val, 4)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to execute regression prediction: {str(e)}"
            )

        return {
            "training_run_id": training_run_id,
            "problem_type": problem_type,
            "predicted_class": None,
            "probabilities": None,
            "predicted_value": predicted_value
        }
