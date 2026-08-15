import difflib
import math
import time
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np

from app.analytics.chart_engine import get_column_classifications, is_free_text_column
from app.analytics.kpi_engine import check_numeric_coercion
from app.analytics.profiling import dataset_health

EXCLUDED_TARGET_TYPES = {"IDENTIFIER", "COORDINATE", "FREE_TEXT", "EXCLUDED"}

BOOL_TRUE_VARIANTS = {"true", "t", "yes", "y", "1", "1.0"}
BOOL_FALSE_VARIANTS = {"false", "f", "no", "n", "0", "0.0"}
GENDER_FEMALE_VARIANTS = {"female", "f", "woman", "women"}
GENDER_MALE_VARIANTS = {"male", "m", "man", "men"}


def is_name_like_column(col_name: str) -> bool:
    """Detect if a column explicitly represents personal names based on column name tokens/patterns."""
    col_lower = col_name.lower().strip()
    tokens = set(col_lower.replace("-", "_").split("_"))

    # Explicit name segments or keywords (e.g. first_name, last_name, officer_first_name, victim_name, full_name, etc.)
    if any(kw in col_lower for kw in ["first_name", "last_name", "full_name", "given_name", "family_name"]):
        return True
    if "name" in tokens or col_lower.endswith("_name") or col_lower.startswith("name_") or col_lower in {"name", "fullname"}:
        return True

    return False


def _safe_val(val: Any) -> Any:
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (float, np.floating)):
        if math.isnan(val) or math.isinf(val):
            return None
        return round(float(val), 2)
    if isinstance(val, (int, np.integer)):
        return int(val)
    return str(val)


def normalize_categorical_series(series: pd.Series) -> Tuple[pd.Series, int, Optional[str], List[str]]:
    """
    Lightweight normalization for target candidate evaluation and data aggregation:
    1. Strip whitespace & lowercase
    2. Map boolean-equivalent strings to canonical 'Yes' / 'No'
    3. Map gender variants to 'Female' / 'Male'
    4. Fuzzy merge close typo variants (e.g. 'Arres Made' vs 'Arrest Made')
    5. Conservative prefix matching for short unmerged abbreviations (<4 chars):
       - If exactly 1 canonical target starts with abbreviation -> merge into that target.
       - If >1 canonical target starts with abbreviation -> leave unmerged, flag as ambiguous.
    Returns: (normalized_series, raw_nunique, data_quality_note, ambiguous_abbreviations)
    """
    valid = series.dropna().astype(str)
    raw_nunique = int(valid.nunique())
    if valid.empty:
        return valid, raw_nunique, None, []

    cleaned = valid.str.strip().str.lower()
    cleaned_nunique = int(cleaned.nunique())

    if cleaned_nunique > 100:
        # High cardinality even after case/whitespace cleaning (>100 unique)
        return cleaned.str.title(), raw_nunique, None, []

    canonical_map: Dict[str, str] = {}
    unique_cleaned = list(cleaned.unique())

    bool_matches = sum(1 for x in unique_cleaned if x in BOOL_TRUE_VARIANTS or x in BOOL_FALSE_VARIANTS)
    is_bool_col = bool_matches >= len(unique_cleaned) * 0.7 if len(unique_cleaned) > 0 else False

    gender_matches = sum(1 for x in unique_cleaned if x in GENDER_FEMALE_VARIANTS or x in GENDER_MALE_VARIANTS)
    is_gender_col = gender_matches >= len(unique_cleaned) * 0.7 if len(unique_cleaned) > 0 else False

    for val in unique_cleaned:
        if is_bool_col:
            if val in BOOL_TRUE_VARIANTS:
                canonical_map[val] = "Yes"
                continue
            if val in BOOL_FALSE_VARIANTS:
                canonical_map[val] = "No"
                continue
        if is_gender_col:
            if val in GENDER_FEMALE_VARIANTS:
                canonical_map[val] = "Female"
                continue
            if val in GENDER_MALE_VARIANTS:
                canonical_map[val] = "Male"
                continue
        canonical_map[val] = val.title()

    normalized = cleaned.map(canonical_map)

    # Fuzzy Typo Clustering (difflib close matches for top unique strings >= 4 chars)
    norm_unique = list(normalized.value_counts().index)[:50]
    fuzzy_map: Dict[str, str] = {}
    for i in range(len(norm_unique)):
        val1 = norm_unique[i]
        if val1 in fuzzy_map:
            continue
        for j in range(i + 1, len(norm_unique)):
            val2 = norm_unique[j]
            if val2 in fuzzy_map:
                continue
            if len(val1) >= 4 and len(val2) >= 4:
                similarity = difflib.SequenceMatcher(None, val1.lower(), val2.lower()).ratio()
                if similarity >= 0.85:
                    fuzzy_map[val2] = val1

    if fuzzy_map:
        normalized = normalized.replace(fuzzy_map)

    # Prefix-Match Pass for short unmerged abbreviations (<4 chars)
    current_canonical = list(normalized.value_counts().index)
    prefix_map: Dict[str, str] = {}
    ambiguous_abbreviations: List[str] = []

    for val in current_canonical:
        val_lower = val.lower().strip()
        if len(val_lower) < 4:
            longer_targets = [
                target for target in current_canonical
                if target.lower().strip() != val_lower
                and target.lower().strip().startswith(val_lower)
            ]

            if len(longer_targets) == 1:
                prefix_map[val] = longer_targets[0]
            elif len(longer_targets) > 1:
                ambiguous_abbreviations.append(val)

    if prefix_map:
        normalized = normalized.replace(prefix_map)

    norm_nunique = int(normalized.nunique())
    note = None
    if raw_nunique > norm_nunique:
        note = (
            f"Raw column has {raw_nunique} case/spelling variants that normalize to {norm_nunique} categories. "
            f"Recommend cleaning before modeling."
        )
    if ambiguous_abbreviations:
        amb_str = ", ".join(ambiguous_abbreviations)
        amb_note = f"Found ambiguous abbreviations ({amb_str}) matching multiple categories."
        note = f"{note} {amb_note}" if note else amb_note

    return normalized, raw_nunique, note, ambiguous_abbreviations


def check_regression_sanity(col_name: str, series: pd.Series) -> Tuple[Dict[str, Any], Optional[str]]:
    """Perform range sanity checks on regression target candidates to detect implausible values/outliers."""
    col_lower = col_name.lower().strip()
    valid = series.dropna()

    min_val = _safe_val(valid.min())
    max_val = _safe_val(valid.max())
    mean_val = _safe_val(valid.mean())
    std_val = _safe_val(valid.std() if len(valid) > 1 else 0.0)

    dist_summary = {
        "min": min_val,
        "max": max_val,
        "mean": mean_val,
        "std": std_val
    }

    note = None
    if "age" in col_lower:
        if (min_val is not None and min_val < 0) or (max_val is not None and max_val > 120):
            note = f"Contains implausible values (min={min_val}, max={max_val}) — recommend cleaning outliers before using as a regression target."
    elif any(kw in col_lower for kw in ["sales", "revenue", "price", "amount", "cost", "count", "quantity", "stolen", "damage", "units", "weight", "height"]):
        if min_val is not None and min_val < 0:
            note = f"Contains implausible negative values (min={min_val}, max={max_val}) — recommend checking for data entry errors or outliers."
    elif any(kw in col_lower for kw in ["pct", "percent", "percentage", "rate", "ratio"]):
        if (min_val is not None and min_val < 0) or (max_val is not None and max_val > 100):
            note = f"Contains out-of-bounds percentage/rate values (min={min_val}, max={max_val}) — recommend auditing scale before regression modeling."

    return dist_summary, note


def detect_ml_problem_hints(df: pd.DataFrame) -> dict:
    """Evaluate columns to find viable ML target candidates (classification & regression)."""
    t0 = time.perf_counter()
    total_rows = len(df)
    if total_rows == 0 or len(df.columns) == 0:
        return {
            "total_candidates": 0,
            "execution_time_ms": round((time.perf_counter() - t0) * 1000, 2),
            "message": "Dataset is empty. No machine learning targets can be recommended.",
            "candidates": []
        }

    classified = get_column_classifications(df)
    candidates: List[dict] = []

    for col in df.columns:
        col_str = str(col)
        col_type = classified.get(col_str, "EXCLUDED")

        if col_type in EXCLUDED_TARGET_TYPES or is_name_like_column(col_str):
            continue

        raw_series = df[col_str].dropna()
        if raw_series.empty:
            continue

        raw_nunique = int(raw_series.nunique())
        is_cat_type = (
            col_type == "CATEGORICAL"
            or pd.api.types.is_object_dtype(raw_series)
            or pd.api.types.is_bool_dtype(raw_series)
            or isinstance(raw_series.dtype, pd.CategoricalDtype)
            or (not pd.api.types.is_float_dtype(raw_series) and raw_nunique <= 20)
        )

        # 1. CATEGORICAL / BINARY / MULTICLASS TARGET WITH NORMALIZATION
        if is_cat_type:
            norm_series, raw_nunique, quality_note, _ = normalize_categorical_series(raw_series)
            norm_nunique = int(norm_series.nunique())

            if 2 <= norm_nunique <= 20:
                val_counts = norm_series.value_counts()
                dist_summary = {str(k): int(v) for k, v in val_counts.to_dict().items()}

                problem_type = "binary_classification" if norm_nunique == 2 else "multiclass_classification"

                top_freq_ratio = float(val_counts.iloc[0] / len(norm_series)) if len(norm_series) > 0 else 0.0
                balance_score = round(1.0 - abs(top_freq_ratio - (1.0 / norm_nunique)), 2)

                rank_score = round((10.0 if norm_nunique == 2 else 7.0) * balance_score, 2)

                reason = (
                    f"Excellent binary classification target with {norm_nunique} distinct classes."
                    if norm_nunique == 2
                    else f"Solid multiclass classification target with {norm_nunique} distinct categories."
                )

                candidates.append({
                    "column": col_str,
                    "problem_type": problem_type,
                    "unique_value_count": norm_nunique,
                    "raw_unique_value_count": raw_nunique if raw_nunique != norm_nunique else None,
                    "distribution": dist_summary,
                    "reason": reason,
                    "rank_score": rank_score,
                    "data_quality_note": quality_note
                })
                continue

        # 2. NUMERIC REGRESSION TARGET WITH SANITY CHECK
        if col_type == "MEASURE" and pd.api.types.is_numeric_dtype(raw_series):
            std_val = float(raw_series.std()) if len(raw_series) > 1 else 0.0
            if std_val > 1e-6:
                dist_summary, quality_note = check_regression_sanity(col_str, raw_series)

                rank_score = 5.0
                reason = f"Numeric measure with continuous distribution (mean={dist_summary['mean']}, std={dist_summary['std']}). Ideal for regression modeling."

                candidates.append({
                    "column": col_str,
                    "problem_type": "regression",
                    "unique_value_count": int(raw_series.nunique()),
                    "raw_unique_value_count": None,
                    "distribution": dist_summary,
                    "reason": reason,
                    "rank_score": rank_score,
                    "data_quality_note": quality_note
                })

    candidates.sort(key=lambda c: c["rank_score"], reverse=True)

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    message = None
    if not candidates:
        message = "No viable machine learning target columns found (all columns are IDs, coordinates, or descriptions)."

    return {
        "total_candidates": len(candidates),
        "execution_time_ms": elapsed_ms,
        "message": message,
        "candidates": candidates
    }


def evaluate_feature_candidates(df: pd.DataFrame, target_col: str) -> dict:
    """Classify remaining columns into recommended vs excluded feature categories for a chosen target."""
    total_rows = len(df)
    if total_rows == 0 or target_col not in df.columns:
        return {
            "target": target_col,
            "total_features": 0,
            "recommended_count": 0,
            "features": []
        }

    health = dataset_health(df)
    constant_cols = set(health["constant_columns"])
    likely_id_cols = set(health["likely_id_columns"])
    classified = get_column_classifications(df)

    target_clean = target_col.lower().replace("_", "").replace("-", "")
    features: List[dict] = []
    recommended_count = 0

    for col in df.columns:
        col_str = str(col)
        if col_str == target_col:
            continue

        col_clean = col_str.lower().replace("_", "").replace("-", "")

        # Determine column data type & distinct value metadata
        is_cat = not pd.api.types.is_numeric_dtype(df[col_str])
        distinct_vals: Optional[List[str]] = None
        min_val: Optional[float] = None
        max_val: Optional[float] = None
        mean_val: Optional[float] = None

        if is_cat:
            raw_unique = df[col_str].dropna().unique()
            distinct_vals = [str(x).strip() for x in raw_unique if str(x).strip() != ""][:50]
        else:
            try:
                s_valid = df[col_str].dropna()
                if len(s_valid) > 0:
                    min_val = round(float(s_valid.min()), 2)
                    max_val = round(float(s_valid.max()), 2)
                    mean_val = round(float(s_valid.mean()), 2)
            except Exception:
                pass

        # 1. Target Leakage check
        if target_clean in col_clean and col_clean != target_clean:
            features.append({
                "name": col_str,
                "column": col_str,
                "is_categorical": is_cat,
                "distinct_values": distinct_vals,
                "min_val": min_val,
                "max_val": max_val,
                "mean_val": mean_val,
                "status": "excluded_leakage",
                "reason": f"Potential target leakage: Column name '{col_str}' closely resembles target '{target_col}'."
            })
            continue

        # 2. Personal name check
        if is_name_like_column(col_str):
            features.append({
                "name": col_str,
                "column": col_str,
                "is_categorical": is_cat,
                "distinct_values": distinct_vals,
                "min_val": min_val,
                "max_val": max_val,
                "mean_val": mean_val,
                "status": "excluded_identifier_like_name",
                "reason": f"Column '{col_str}' appears to contain personal names. Excluded to prevent overfitting and privacy issues."
            })
            continue

        # 3. Coordinate check
        if classified.get(col_str) == "COORDINATE":
            features.append({
                "name": col_str,
                "column": col_str,
                "is_categorical": is_cat,
                "distinct_values": distinct_vals,
                "min_val": min_val,
                "max_val": max_val,
                "mean_val": mean_val,
                "status": "excluded_coordinate",
                "reason": f"Column '{col_str}' contains spatial coordinates (latitude/longitude)."
            })
            continue

        # 4. Datetime check
        if classified.get(col_str) == "DATETIME" or pd.api.types.is_datetime64_any_dtype(df[col_str]):
            features.append({
                "name": col_str,
                "column": col_str,
                "is_categorical": is_cat,
                "distinct_values": distinct_vals,
                "min_val": min_val,
                "max_val": max_val,
                "mean_val": mean_val,
                "status": "excluded_datetime",
                "reason": f"Column '{col_str}' contains timestamp/date values. Raw timestamps require explicit feature engineering (day/month/hour extraction)."
            })
            continue

        # 5. Free text check
        if classified.get(col_str) == "FREE_TEXT":
            features.append({
                "name": col_str,
                "column": col_str,
                "is_categorical": is_cat,
                "distinct_values": distinct_vals,
                "min_val": min_val,
                "max_val": max_val,
                "mean_val": mean_val,
                "status": "excluded_free_text",
                "reason": f"Column '{col_str}' contains unstructured free-text descriptions or narrative logs."
            })
            continue

        # 6. Identifier check
        if col_str in likely_id_cols or classified.get(col_str) == "IDENTIFIER":
            features.append({
                "name": col_str,
                "column": col_str,
                "is_categorical": is_cat,
                "distinct_values": distinct_vals,
                "min_val": min_val,
                "max_val": max_val,
                "mean_val": mean_val,
                "status": "excluded_identifier",
                "reason": f"Column '{col_str}' contains unique row identifiers or codes. Excluded to prevent overfitting."
            })
            continue

        # 7. Constant column check
        if col_str in constant_cols or df[col_str].nunique(dropna=True) <= 1:
            features.append({
                "name": col_str,
                "column": col_str,
                "is_categorical": is_cat,
                "distinct_values": distinct_vals,
                "min_val": min_val,
                "max_val": max_val,
                "mean_val": mean_val,
                "status": "excluded_high_missing",
                "reason": f"Column '{col_str}' has 0 variance or constant value across all rows."
            })
            continue

        # 7. High missing values (>50%)
        null_count = int(df[col_str].isna().sum())
        null_pct = round((null_count / total_rows) * 100, 1)
        if null_pct > 50.0:
            features.append({
                "name": col_str,
                "column": col_str,
                "is_categorical": is_cat,
                "distinct_values": distinct_vals,
                "min_val": min_val,
                "max_val": max_val,
                "mean_val": mean_val,
                "status": "excluded_high_missing",
                "reason": f"Column '{col_str}' has {null_pct}% missing values (exceeds 50% threshold)."
            })
            continue

        # 8. High cardinality categorical (>50 unique or >50% of rows) with numeric-coercion detection
        nunique = int(df[col_str].nunique(dropna=True))
        if pd.api.types.is_string_dtype(df[col_str]) or pd.api.types.is_object_dtype(df[col_str]):
            is_coercible, quality_note = check_numeric_coercion(df[col_str])
            if is_coercible:
                recommended_count += 1
                features.append({
                    "name": col_str,
                    "column": col_str,
                    "is_categorical": False,
                    "distinct_values": None,
                    "min_val": min_val,
                    "max_val": max_val,
                    "mean_val": mean_val,
                    "status": "recommended",
                    "reason": "Valid predictive feature candidate (MEASURE via numeric coercion).",
                    "data_quality_note": quality_note
                })
                continue

            if nunique > 50 or (total_rows > 20 and nunique / total_rows > 0.5):
                features.append({
                    "name": col_str,
                    "column": col_str,
                    "is_categorical": is_cat,
                    "distinct_values": distinct_vals,
                    "min_val": min_val,
                    "max_val": max_val,
                    "mean_val": mean_val,
                    "status": "excluded_high_cardinality",
                    "reason": f"Categorical column '{col_str}' has high cardinality ({nunique} unique values)."
                })
                continue

        # Recommended Feature
        recommended_count += 1
        features.append({
            "name": col_str,
            "column": col_str,
            "is_categorical": is_cat,
            "distinct_values": distinct_vals,
            "min_val": min_val,
            "max_val": max_val,
            "mean_val": mean_val,
            "status": "recommended",
            "reason": f"Valid predictive feature candidate ({classified.get(col_str, 'FEATURE')})."
        })

    return {
        "target": target_col,
        "total_features": len(features),
        "recommended_count": recommended_count,
        "features": features
    }
