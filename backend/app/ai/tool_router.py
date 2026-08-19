import difflib
from typing import Dict, List, Any, Callable, Optional
import pandas as pd
import numpy as np

from app.core.session import get_dataset
from app.analytics.profiling import dataset_health, _safe_float
from app.analytics.chart_engine import get_column_classifications, recommend_charts
from app.datascience.ml_profiling import normalize_categorical_series
from app.analytics.kpi_engine import _to_numeric_series


def resolve_column_name(df_columns: List[str], raw_name: str) -> Optional[str]:
    """
    Robust column name resolver mapping LLM variations (e.g. 'weapons used', 'suspect age', 'crime types')
    to exact DataFrame column names in the dataset ('weapon_used', 'suspect_age', 'crime_type').
    """
    if not raw_name or not isinstance(raw_name, str):
        return None

    cols = [str(c) for c in df_columns]
    # 1. Exact match
    if raw_name in cols:
        return raw_name

    # 2. Case-insensitive / strip
    clean_raw = raw_name.strip().lower()
    for col in cols:
        if col.strip().lower() == clean_raw:
            return col

    # 3. Replace underscores, spaces, hyphens
    norm_raw = clean_raw.replace("_", " ").replace("-", " ").strip()
    for col in cols:
        norm_col = col.strip().lower().replace("_", " ").replace("-", " ").strip()
        if norm_col == norm_raw:
            return col

    # 4. Singular / Plural pass (strip trailing 's')
    raw_singular = norm_raw[:-1] if norm_raw.endswith("s") else norm_raw
    for col in cols:
        norm_col = col.strip().lower().replace("_", " ").replace("-", " ").strip()
        col_singular = norm_col[:-1] if norm_col.endswith("s") else norm_col
        if col_singular == raw_singular:
            return col

    # 5. Substring / Containment pass
    for col in cols:
        norm_col = col.strip().lower().replace("_", " ").replace("-", " ").strip()
        if norm_raw in norm_col or norm_col in norm_raw:
            return col

    # 6. Fuzzy match cutoff 0.65
    matches = difflib.get_close_matches(norm_raw, [c.strip().lower().replace("_", " ") for c in cols], n=1, cutoff=0.65)
    if matches:
        matched_clean = matches[0]
        for col in cols:
            if col.strip().lower().replace("_", " ") == matched_clean:
                return col

    return None


TOOL_REGISTRY: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_dataset_summary",
            "description": "Use this tool whenever asked for total row count, column count, dataset overview, column list, or dataset health score.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "The unique identifier (file_id) of the dataset."
                    }
                },
                "required": ["file_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_statistic",
            "description": "Use this tool whenever asked for a summary statistic (mean, median, sum, min, max, std, count, unique_count, average) for a column. Do not calculate manually.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "The unique identifier of the dataset."
                    },
                    "column_name": {
                        "type": "string",
                        "description": "The exact column name to calculate the statistic for."
                    },
                    "statistic": {
                        "type": "string",
                        "description": "The statistic to compute: 'mean', 'median', 'sum', 'min', 'max', 'std', 'count', or 'unique_count'.",
                        "enum": ["mean", "median", "sum", "min", "max", "std", "count", "unique_count"]
                    }
                },
                "required": ["file_id", "column_name", "statistic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "aggregate_data",
            "description": "Use this tool whenever asked to group dataset rows by a categorical dimension column and aggregate total/mean/count/median of a value column.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "The unique identifier of the dataset."
                    },
                    "group_by_column": {
                        "type": "string",
                        "description": "The categorical dimension column to group by."
                    },
                    "value_column": {
                        "type": "string",
                        "description": "The target value column to aggregate (use 'count' or a numeric column name)."
                    },
                    "aggregation": {
                        "type": "string",
                        "description": "The aggregation function: 'sum', 'mean', 'count', or 'median'.",
                        "enum": ["sum", "mean", "count", "median"]
                    }
                },
                "required": ["file_id", "group_by_column", "value_column", "aggregation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_top_categories",
            "description": "Use this tool whenever asked for top categories, value counts, category distribution, top weapons used by percentage, top crime types, or percentages of a categorical column.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "The unique identifier of the dataset."
                    },
                    "column_name": {
                        "type": "string",
                        "description": "The categorical column name (e.g. 'weapon_used', 'crime_type', 'district') to compute frequencies and percentages for."
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Optional number of top categories to return (default 10)."
                    }
                },
                "required": ["file_id", "column_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_chart",
            "description": "Use this tool whenever asked what chart or visualization would work best for specific columns or data dimensions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "The unique identifier of the dataset."
                    },
                    "columns_of_interest": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Optional list of column names to prioritize for chart recommendation."
                    }
                },
                "required": ["file_id"]
            }
        }
    }
]

# Alias TOOLS to TOOL_REGISTRY for backward compatibility
TOOLS = TOOL_REGISTRY


def get_dataset_summary(file_id: str, **kwargs) -> Dict[str, Any]:
    """
    Wrap existing profiling logic to summarize dataset metrics, health, missing values, and column schemas.
    """
    df = get_dataset(file_id)
    health = dataset_health(df)

    missing_dict = df.isnull().sum().to_dict()
    missing_info = {str(k): int(v) for k, v in missing_dict.items() if v > 0}

    return {
        "total_rows": health["total_rows"],
        "total_columns": health["total_columns"],
        "column_names": [str(col) for col in df.columns],
        "column_data_types": {str(c): str(df[c].dtype) for c in df.columns},
        "missing_values_by_column": missing_info if missing_info else "No missing values",
        "total_missing_cells": health["missing_cells"],
        "duplicate_rows": health["duplicate_rows"],
        "health_score": health["quality_score"]
    }


def calculate_statistic(
    file_id: str,
    column_name: str,
    statistic: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Compute a single summary statistic for a specified column.
    Auto-routes to aggregate_data if a group_by dimension parameter was supplied by LLM.
    """
    group_by = kwargs.get("group_by_column") or kwargs.get("group_by") or kwargs.get("dimension")
    if group_by:
        return aggregate_data(
            file_id=file_id,
            group_by_column=str(group_by),
            value_column=column_name,
            aggregation=statistic,
            **kwargs
        )

    df = get_dataset(file_id)

    # 1. Resolve column_name
    resolved_col = resolve_column_name(list(df.columns), column_name)
    if not resolved_col:
        return {
            "error": "column_not_found",
            "message": f"Column '{column_name}' does not exist in this dataset.",
            "available_columns": [str(c) for c in df.columns]
        }
    column_name = resolved_col

    # 2. Reject coordinate columns
    classified = get_column_classifications(df)
    col_cls = classified.get(column_name, "EXCLUDED")
    if col_cls == "COORDINATE":
        return {
            "error": "invalid_column_type",
            "message": f"Column '{column_name}' is a spatial coordinate column and cannot be used for numerical statistical calculations."
        }

    stat_lower = statistic.lower().strip()
    if stat_lower == "average":
        stat_lower = "mean"

    valid_stats = {"mean", "median", "sum", "min", "max", "std", "count", "unique_count"}

    if stat_lower not in valid_stats:
        return {
            "error": "invalid_statistic",
            "message": f"Statistic '{statistic}' is not supported. Supported statistics: {', '.join(sorted(valid_stats))}."
        }

    series = df[column_name]
    coerced_s = _to_numeric_series(series)
    is_coerced = not coerced_s.empty
    is_numeric = (pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)) or is_coerced

    # 3. For non-numeric columns requesting numeric statistics -> return structured error
    numeric_only_stats = {"mean", "median", "sum", "std"}
    if stat_lower in numeric_only_stats and not is_numeric:
        return {
            "error": "non_numeric_column",
            "message": f"Cannot calculate numeric statistic '{stat_lower}' on non-numeric column '{column_name}' (dtype: {series.dtype})."
        }

    # 4. Compute requested statistic
    valid_s = coerced_s if is_coerced else series.dropna()
    val: Any = None

    if stat_lower == "count":
        val = int(series.count())
    elif stat_lower == "unique_count":
        val = int(series.nunique(dropna=True))
    elif stat_lower == "sum":
        val = _safe_float(valid_s.sum()) if not valid_s.empty else 0.0
    elif stat_lower == "mean":
        val = _safe_float(valid_s.mean()) if not valid_s.empty else None
    elif stat_lower == "median":
        val = _safe_float(valid_s.median()) if not valid_s.empty else None
    elif stat_lower == "min":
        if valid_s.empty:
            val = None
        elif is_numeric:
            val = _safe_float(valid_s.min())
        else:
            val = str(valid_s.min())
    elif stat_lower == "max":
        if valid_s.empty:
            val = None
        elif is_numeric:
            val = _safe_float(valid_s.max())
        else:
            val = str(valid_s.max())
    elif stat_lower == "std":
        val = _safe_float(valid_s.std()) if len(valid_s) > 1 else 0.0

    return {
        "column": column_name,
        "statistic": stat_lower,
        "value": val,
        "dtype": str(series.dtype)
    }


def aggregate_data(
    file_id: str,
    group_by_column: str,
    value_column: Optional[str] = None,
    aggregation: str = "count",
    **kwargs
) -> Dict[str, Any]:
    """
    Group dataset by dimension column and aggregate target value column,
    applying categorical normalization to group_by_column before grouping.
    """
    df = get_dataset(file_id)

    # Allow value_column resolution from kwargs if LLM used column_name/column
    if not value_column:
        value_column = str(kwargs.get("column_name") or kwargs.get("column") or kwargs.get("target") or "count")

    # 1. Resolve group_by_column
    resolved_group = resolve_column_name(list(df.columns), group_by_column)
    if not resolved_group:
        return {
            "error": "column_not_found",
            "message": f"Group-by column '{group_by_column}' does not exist in this dataset.",
            "available_columns": [str(c) for c in df.columns]
        }
    group_by_column = resolved_group

    # 2. Check group_by_column safety (must not be coordinate, free-text, identifier, excluded)
    classified = get_column_classifications(df)
    cls = classified.get(group_by_column, "EXCLUDED")
    if cls in {"COORDINATE", "FREE_TEXT", "IDENTIFIER", "EXCLUDED"}:
        return {
            "error": "invalid_group_by_column",
            "message": f"Column '{group_by_column}' (classified as {cls}) cannot be used as a group-by dimension because it is a coordinate, free-text, unique identifier, or excluded column."
        }

    agg_lower = aggregation.lower().strip()
    valid_aggs = {"sum", "mean", "count", "median"}
    if agg_lower not in valid_aggs:
        return {
            "error": "invalid_aggregation",
            "message": f"Aggregation '{aggregation}' is not supported. Supported aggregations: sum, mean, count, median."
        }

    # 3. Validate and resolve value_column
    is_count_val = (value_column.lower().strip() == "count")
    if not is_count_val:
        resolved_val = resolve_column_name(list(df.columns), value_column)
        if resolved_val:
            value_column = resolved_val
        else:
            return {
                "error": "column_not_found",
                "message": f"Value column '{value_column}' does not exist in this dataset.",
                "available_columns": [str(c) for c in df.columns]
            }

    # 4. Normalize group_by_column before grouping using ml_profiling's normalize_categorical_series
    norm_series, _, _, ambiguous_abbs = normalize_categorical_series(df[group_by_column])
    cols_needed = [group_by_column]
    if value_column and value_column in df.columns and value_column != group_by_column:
        cols_needed.append(value_column)
    temp_df = df[cols_needed].copy()
    temp_df["_norm_group"] = norm_series
    temp_df = temp_df.dropna(subset=["_norm_group"])
    total_groups = int(temp_df["_norm_group"].nunique(dropna=True))

    if is_count_val or agg_lower == "count":
        grouped = temp_df.groupby("_norm_group").size()
    else:
        coerced_val_s = _to_numeric_series(temp_df[value_column])
        if coerced_val_s.empty:
            return {
                "error": "non_numeric_value_column",
                "message": f"Cannot compute numeric aggregation '{agg_lower}' on non-numeric column '{value_column}' (dtype: {temp_df[value_column].dtype})."
            }
        temp_df["_coerced_val"] = _to_numeric_series(temp_df[value_column])
        val_col_name = "_coerced_val"

        if agg_lower == "mean":
            grouped = temp_df.groupby("_norm_group")[val_col_name].mean()
        elif agg_lower == "median":
            grouped = temp_df.groupby("_norm_group")[val_col_name].median()
        else:  # sum
            grouped = temp_df.groupby("_norm_group")[val_col_name].sum()

    grouped = grouped.sort_values(ascending=False)
    top_grouped = grouped.head(20)

    results = []
    for g_val, val in top_grouped.items():
        clean_v = _safe_float(val) if isinstance(val, (float, np.floating)) else (int(val) if isinstance(val, (int, np.integer)) else _safe_float(val))
        results.append({
            "group": str(g_val),
            "value": clean_v
        })

    res = {
        "group_by_column": group_by_column,
        "value_column": value_column,
        "aggregation": agg_lower,
        "results": results,
        "total_groups": total_groups
    }
    if ambiguous_abbs:
        res["ambiguous_abbreviations"] = ambiguous_abbs
    return res


def find_top_categories(
    file_id: str,
    column_name: str,
    top_n: int = 10,
    **kwargs
) -> Dict[str, Any]:
    """
    Compute exact category frequencies, value counts, and percentage distribution
    for a categorical column, using normalize_categorical_series.
    """
    df = get_dataset(file_id)

    # 1. Resolve column_name
    resolved_col = resolve_column_name(list(df.columns), column_name)
    if not resolved_col:
        return {
            "error": "column_not_found",
            "message": f"Column '{column_name}' does not exist in this dataset.",
            "available_columns": [str(c) for c in df.columns]
        }
    column_name = resolved_col

    # 2. Reject coordinate / free text / identifier / excluded
    classified = get_column_classifications(df)
    cls = classified.get(column_name, "EXCLUDED")
    if cls in {"COORDINATE", "FREE_TEXT", "IDENTIFIER", "EXCLUDED"}:
        return {
            "error": "invalid_column_type",
            "message": f"Column '{column_name}' (classified as {cls}) cannot be evaluated for categorical distribution."
        }

    # 3. Apply normalization
    norm_series, raw_nunique, quality_note, ambiguous_abbs = normalize_categorical_series(df[column_name])
    valid_s = norm_series.dropna()
    total_valid = len(valid_s)

    if total_valid == 0:
        return {
            "column": column_name,
            "total_valid_rows": 0,
            "total_categories": 0,
            "categories": []
        }

    val_counts = valid_s.value_counts()
    total_categories = len(val_counts)

    try:
        if top_n is None or str(top_n).lower().strip() in {"null", "none", ""}:
            parsed_top_n = 10
        else:
            parsed_top_n = int(top_n)
    except (ValueError, TypeError):
        parsed_top_n = 10
    limit = max(1, min(parsed_top_n, 50))
    top_counts = val_counts.head(limit)

    categories_list = []
    for cat_name, cnt in top_counts.items():
        pct = round((cnt / total_valid) * 100, 2)
        categories_list.append({
            "category": str(cat_name),
            "count": int(cnt),
            "percentage": pct
        })

    res = {
        "column": column_name,
        "total_valid_rows": total_valid,
        "total_categories": total_categories,
        "categories": categories_list
    }
    if ambiguous_abbs:
        res["ambiguous_abbreviations"] = ambiguous_abbs
    return res


def recommend_chart(
    file_id: str,
    columns_of_interest: Optional[Union[List[str], str]] = None,
    column_name: Optional[str] = None,
    column: Optional[str] = None,
    columns: Optional[Union[List[str], str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Recommend chart configuration scoped optionally to user columns of interest.
    Fuzzy-resolves column names and dynamically constructs a chart config if the requested column
    is not in the top pre-computed recommendations.
    """
    df = get_dataset(file_id)

    # Consolidate candidate column inputs
    raw_cols: List[str] = []
    for candidate in [columns_of_interest, column_name, column, columns]:
        if candidate:
            if isinstance(candidate, list):
                raw_cols.extend([str(c) for c in candidate if c])
            elif isinstance(candidate, str):
                raw_cols.append(candidate)

    resolved_cols = set()
    for rc in raw_cols:
        r_col = resolve_column_name(list(df.columns), rc)
        if r_col:
            resolved_cols.add(r_col)

    rec = recommend_charts(df)
    charts = rec.get("charts", [])

    if resolved_cols:
        if charts:
            matching = []
            for c in charts:
                x_axis = str(c.get("x_axis", "")).strip()
                y_axis = str(c.get("y_axis", "")).strip()
                if x_axis in resolved_cols or y_axis in resolved_cols:
                    matching.append(c)
            if matching:
                selected_chart = matching[0]
                return {
                    "chart_type": selected_chart.get("chart_type", "bar"),
                    "x_axis": selected_chart.get("x_axis", ""),
                    "y_axis": selected_chart.get("y_axis", ""),
                    "aggregation": selected_chart.get("aggregation", "count"),
                    "reasoning": selected_chart.get("reason") or selected_chart.get("reasoning", "")
                }

        # If requested column is resolved but not in top default recommendations, generate custom chart config
        target_col = list(resolved_cols)[0]
        series = df[target_col]
        is_num = pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)

        if is_num:
            return {
                "chart_type": "bar",
                "x_axis": target_col,
                "y_axis": target_col,
                "aggregation": "mean",
                "reasoning": f"Custom recommendation for numeric measure '{target_col}'."
            }
        else:
            return {
                "chart_type": "bar",
                "x_axis": target_col,
                "y_axis": "count",
                "aggregation": "count",
                "reasoning": f"Custom recommendation for category distribution of '{target_col}'."
            }

    if not charts:
        return {
            "error": "no_charts_available",
            "message": "No suitable chart recommendations could be generated for this dataset."
        }

    selected_chart = charts[0]
    return {
        "chart_type": selected_chart.get("chart_type", ""),
        "x_axis": selected_chart.get("x_axis", ""),
        "y_axis": selected_chart.get("y_axis", ""),
        "aggregation": selected_chart.get("aggregation", ""),
        "reasoning": selected_chart.get("reason") or selected_chart.get("reasoning", "")
    }


_TOOL_MAP: Dict[str, Callable[..., Dict[str, Any]]] = {
    "get_dataset_summary": get_dataset_summary,
    "calculate_statistic": calculate_statistic,
    "aggregate_data": aggregate_data,
    "find_top_categories": find_top_categories,
    "recommend_chart": recommend_chart
}


def dispatch_tool_call(
    tool_name: str,
    arguments: Dict[str, Any],
    file_id: str
) -> Dict[str, Any]:
    """
    Dispatch a tool invocation requested by Ollama to its real backend implementation.
    The route's file_id parameter is authoritative and overrides whatever the LLM passed in arguments.
    """
    if tool_name not in _TOOL_MAP:
        raise ValueError(f"Tool '{tool_name}' is not registered in tool_router.")

    fn = _TOOL_MAP[tool_name]
    call_kwargs = dict(arguments or {})
    # Override file_id with authoritative file_id from route
    call_kwargs["file_id"] = file_id

    return fn(**call_kwargs)
