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
        return round(f, 2)
    except (ValueError, TypeError):
        return None


def get_chart_data(
    df: pd.DataFrame,
    x_axis: str,
    y_axis: str,
    aggregation: str = "SUM",
    chart_type: str = "bar",
    top_n: Optional[int] = None,
    date_granularity: Optional[str] = None
) -> dict:
    """Compute aggregated data points for a chart configuration from the DataFrame."""
    if df.empty or x_axis not in df.columns:
        return {"data": [], "total_points": 0}

    # 1. SCATTER PLOT (raw x/y points, capped at 500 points)
    if chart_type == "scatter":
        if y_axis not in df.columns:
            return {"data": [], "total_points": 0}

        scatter_df = df[[x_axis, y_axis]].dropna()
        scatter_df[x_axis] = pd.to_numeric(scatter_df[x_axis], errors="coerce")
        scatter_df[y_axis] = pd.to_numeric(scatter_df[y_axis], errors="coerce")
        scatter_df = scatter_df.dropna()

        if len(scatter_df) > 500:
            scatter_df = scatter_df.head(500)

        points = []
        for _, row in scatter_df.iterrows():
            x_val = _safe_float(row[x_axis])
            y_val = _safe_float(row[y_axis])
            if x_val is not None and y_val is not None:
                points.append({"x": x_val, "y": y_val})

        return {"data": points, "total_points": len(points)}

    # 2. LINE CHART WITH DATE GRANULARITY
    is_date_col = pd.api.types.is_datetime64_any_dtype(df[x_axis]) or "date" in x_axis.lower() or "time" in x_axis.lower()
    if chart_type == "line" or is_date_col or date_granularity:
        cols_to_select = [x_axis]
        if y_axis in df.columns and y_axis != x_axis:
            cols_to_select.append(y_axis)
        temp_df = df[cols_to_select].copy()
        try:
            temp_df["_dt_col"] = pd.to_datetime(temp_df[x_axis], errors="coerce")
            temp_df = temp_df.dropna(subset=["_dt_col"])

            if not temp_df.empty:
                gran = (date_granularity or "month").lower()
                if gran == "year":
                    temp_df["_period"] = temp_df["_dt_col"].dt.strftime("%Y")
                elif gran == "day":
                    temp_df["_period"] = temp_df["_dt_col"].dt.strftime("%Y-%m-%d")
                else:  # month default
                    temp_df["_period"] = temp_df["_dt_col"].dt.strftime("%Y-%m")

                if y_axis == "count" or aggregation == "COUNT":
                    grouped = temp_df.groupby("_period").size()
                elif y_axis in temp_df.columns:
                    temp_df[y_axis] = pd.to_numeric(temp_df[y_axis], errors="coerce")
                    if aggregation == "AVERAGE":
                        grouped = temp_df.groupby("_period")[y_axis].mean()
                    elif aggregation == "DISTINCTCOUNT":
                        grouped = temp_df.groupby("_period")[y_axis].nunique()
                    else:  # SUM
                        grouped = temp_df.groupby("_period")[y_axis].sum()
                else:
                    grouped = temp_df.groupby("_period").size()

                grouped = grouped.sort_index()
                points = []
                for period_str, val in grouped.items():
                    clean_v = _safe_float(val)
                    if clean_v is not None:
                        points.append({"name": str(period_str), "value": clean_v})

                return {"data": points, "total_points": len(points)}
        except Exception:
            pass

    # 3. STANDARD BAR / COLUMN / DONUT / TABLE GROUPING
    cols_to_select = [x_axis]
    if y_axis in df.columns and y_axis != x_axis:
        cols_to_select.append(y_axis)
    temp_df = df[cols_to_select].copy()
    temp_df = temp_df.dropna(subset=[x_axis])

    if y_axis == "count" or aggregation == "COUNT":
        grouped = temp_df.groupby(x_axis).size()
    elif y_axis in temp_df.columns:
        temp_df[y_axis] = pd.to_numeric(temp_df[y_axis], errors="coerce")
        if aggregation == "AVERAGE":
            grouped = temp_df.groupby(x_axis)[y_axis].mean()
        elif aggregation == "DISTINCTCOUNT":
            grouped = temp_df.groupby(x_axis)[y_axis].nunique()
        else:  # SUM
            grouped = temp_df.groupby(x_axis)[y_axis].sum()
    else:
        grouped = temp_df.groupby(x_axis).size()

    # Sort descending by aggregated value
    grouped = grouped.sort_values(ascending=False)

    if top_n is not None and top_n > 0:
        grouped = grouped.head(top_n)

    points = []
    for name_val, val in grouped.items():
        clean_v = _safe_float(val)
        if clean_v is not None:
            points.append({"name": str(name_val), "value": clean_v})

    return {"data": points, "total_points": len(points)}
