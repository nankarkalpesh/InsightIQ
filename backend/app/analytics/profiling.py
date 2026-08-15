import math
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np


def _safe_float(val: Any) -> Optional[float]:
    if pd.isna(val) or val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 4)
    except (ValueError, TypeError):
        return None


def dataset_health(df: pd.DataFrame) -> dict:
    total_rows = len(df)
    total_cols = len(df.columns)
    total_cells = total_rows * total_cols

    if total_cells == 0:
        return {
            "total_rows": total_rows,
            "total_columns": total_cols,
            "missing_cells": 0,
            "missing_percentage": 0.0,
            "duplicate_rows": 0,
            "duplicate_percentage": 0.0,
            "quality_score": 100.0,
            "constant_columns": [],
            "likely_id_columns": []
        }

    missing_cells = int(df.isna().sum().sum())
    missing_percentage = round(float((missing_cells / total_cells) * 100), 2)

    duplicate_rows = int(df.duplicated().sum())
    duplicate_percentage = round(float((duplicate_rows / total_rows) * 100), 2) if total_rows > 0 else 0.0

    # Quality score formula (0 - 100)
    missing_penalty = min(50.0, missing_percentage * 0.5)
    duplicate_penalty = min(30.0, duplicate_percentage * 0.5)
    quality_score = max(0.0, round(100.0 - missing_penalty - duplicate_penalty, 1))

    constant_columns: List[str] = []
    likely_id_columns: List[str] = []

    id_name_keywords = {"id", "uuid", "key", "code", "pk", "index"}

    for col in df.columns:
        col_str = str(col)
        series = df[col]
        nunique = series.nunique(dropna=False)

        if nunique <= 1:
            constant_columns.append(col_str)

        nunique_valid = series.nunique(dropna=True)
        valid_count = series.count()

        if total_rows > 0 and valid_count > 0:
            is_100_unique = (nunique_valid == total_rows)
            uniqueness_ratio = nunique_valid / total_rows
            col_name_lower = col_str.lower().strip()

            has_id_keyword = any(kw in col_name_lower for kw in id_name_keywords)
            has_id_suffix = (
                col_name_lower.endswith("_id")
                or col_name_lower.endswith("_number")
                or col_name_lower.endswith("_no")
                or col_name_lower.endswith("_code")
                or col_name_lower == "id"
            )
            is_string = pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series)
            if is_string:
                lower_nunique = series.astype(str).str.strip().str.lower().nunique(dropna=True)
                is_low_cardinality = lower_nunique <= 5
            else:
                is_low_cardinality = False

            if is_100_unique and not is_low_cardinality and (has_id_keyword or has_id_suffix or (is_string and total_rows >= 15)):
                likely_id_columns.append(col_str)
            elif (has_id_keyword or has_id_suffix) and uniqueness_ratio >= 0.8:
                likely_id_columns.append(col_str)

    return {
        "total_rows": total_rows,
        "total_columns": total_cols,
        "missing_cells": missing_cells,
        "missing_percentage": missing_percentage,
        "duplicate_rows": duplicate_rows,
        "duplicate_percentage": duplicate_percentage,
        "quality_score": quality_score,
        "constant_columns": constant_columns,
        "likely_id_columns": likely_id_columns
    }


def column_schema(df: pd.DataFrame) -> List[dict]:
    schema_list = []
    total_rows = len(df)

    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        null_percentage = round(float((null_count / total_rows) * 100), 2) if total_rows > 0 else 0.0
        unique_count = int(series.nunique(dropna=True))

        first_valid_idx = series.first_valid_index()
        sample_value = None
        if first_valid_idx is not None:
            raw_val = series.loc[first_valid_idx]
            if isinstance(raw_val, (pd.Timestamp, np.datetime64)):
                sample_value = str(raw_val)
            elif isinstance(raw_val, (int, float, bool, str)):
                sample_value = raw_val if not pd.isna(raw_val) else None
            else:
                sample_value = str(raw_val)

        schema_list.append({
            "name": str(col),
            "dtype": str(series.dtype),
            "unique_count": unique_count,
            "null_count": null_count,
            "null_percentage": null_percentage,
            "sample_value": sample_value
        })

    return schema_list


def column_statistics(df: pd.DataFrame) -> dict:
    numeric_stats = {}
    categorical_stats = {}
    datetime_stats = {}

    for col in df.columns:
        series = df[col]
        col_name = str(col)

        # Datetime
        if pd.api.types.is_datetime64_any_dtype(series):
            valid_dt = series.dropna()
            if not valid_dt.empty:
                min_dt = valid_dt.min()
                max_dt = valid_dt.max()
                delta = (max_dt - min_dt).total_seconds() / 86400.0
                datetime_stats[col_name] = {
                    "min": str(min_dt),
                    "max": str(max_dt),
                    "range_days": round(delta, 2)
                }
            else:
                datetime_stats[col_name] = {
                    "min": None,
                    "max": None,
                    "range_days": None
                }

        # Numeric
        elif pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            valid_num = series.dropna()
            if not valid_num.empty:
                numeric_stats[col_name] = {
                    "mean": _safe_float(valid_num.mean()),
                    "median": _safe_float(valid_num.median()),
                    "min": _safe_float(valid_num.min()),
                    "max": _safe_float(valid_num.max()),
                    "std": _safe_float(valid_num.std()) if len(valid_num) > 1 else 0.0
                }
            else:
                numeric_stats[col_name] = {
                    "mean": None,
                    "median": None,
                    "min": None,
                    "max": None,
                    "std": None
                }

        # Categorical / text / bool
        else:
            valid_series = series.dropna().astype(str)
            top_counts = valid_series.value_counts().head(5)
            top_list = [
                {"value": str(val), "count": int(cnt)}
                for val, cnt in top_counts.items()
            ]
            categorical_stats[col_name] = {
                "top_values": top_list
            }

    return {
        "numeric": numeric_stats,
        "categorical": categorical_stats,
        "datetime": datetime_stats
    }


def generate_insights(df: pd.DataFrame) -> List[str]:
    insights = []
    health = dataset_health(df)
    total_rows = health["total_rows"]
    total_cols = health["total_columns"]

    insights.append(f"Dataset contains {total_rows:,} rows and {total_cols} columns.")
    insights.append(f"Overall data quality score is {health['quality_score']}/100.")

    if health["missing_cells"] == 0:
        insights.append("No missing values found across the dataset.")
    else:
        insights.append(f"{health['missing_percentage']}% of total data cells ({health['missing_cells']:,} cells) contain missing values.")

    schema = column_schema(df)
    high_null_cols = [c for c in schema if c["null_percentage"] >= 20.0]
    for col_info in high_null_cols:
        insights.append(f"Column '{col_info['name']}' has a high missing rate of {col_info['null_percentage']}% ({col_info['null_count']} nulls).")

    if health["duplicate_rows"] > 0:
        insights.append(f"Found {health['duplicate_rows']:,} duplicate rows ({health['duplicate_percentage']}% of dataset).")
    else:
        insights.append("No duplicate rows detected.")

    for c_col in health["constant_columns"]:
        insights.append(f"Column '{c_col}' is constant with only 1 unique value across all rows.")

    for id_col in health["likely_id_columns"]:
        insights.append(f"Column '{id_col}' appears to be a unique identifier column.")

    return insights
