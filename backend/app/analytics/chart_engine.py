from typing import List, Dict, Any, Optional, Set, Tuple
import pandas as pd
import numpy as np

from app.analytics.kpi_engine import classify_column
from app.analytics.profiling import dataset_health

MAX_CHARTS_LIMIT = 8
MAX_SAME_TYPE_AGG = 2

EXCLUDED_AXIS_TYPES = {"IDENTIFIER", "COORDINATE", "FREE_TEXT"}

AVERAGE_MEASURE_KEYWORDS = {
    "age", "rate", "score", "rating", "pct", "percent", "percentage",
    "ratio", "speed", "temp", "temperature", "bmi", "height", "weight",
    "gpa", "sat", "index_score", "probability"
}


def get_default_aggregation(col_name: str) -> str:
    """Determine default aggregation for numeric measure (AVERAGE for age/demographic/rate/score vs SUM for amount/sales/cost)."""
    col_lower = col_name.lower().strip()
    tokens = set(col_lower.replace("-", "_").split("_"))
    if any(t in AVERAGE_MEASURE_KEYWORDS for t in tokens):
        return "AVERAGE"
    for kw in AVERAGE_MEASURE_KEYWORDS:
        if col_lower == kw or col_lower.startswith(kw + "_") or col_lower.endswith("_" + kw):
            return "AVERAGE"
    return "SUM"


def is_free_text_column(series: pd.Series) -> bool:
    """Detect free-text columns (long descriptions, comments, or notes)."""
    valid = series.dropna().astype(str)
    if valid.empty:
        return False
    avg_len = valid.str.len().mean()
    avg_words = valid.str.split().str.len().mean()
    return avg_len > 50 or avg_words > 6


def get_column_classifications(df: pd.DataFrame) -> Dict[str, str]:
    health = dataset_health(df)
    constant_cols = set(health["constant_columns"])
    likely_id_cols = set(health["likely_id_columns"])

    classified: Dict[str, str] = {}
    for col in df.columns:
        col_str = str(col)
        if col_str in constant_cols:
            classified[col_str] = "EXCLUDED"
            continue

        base_cls = classify_column(df[col], col_str, likely_id_cols)
        if base_cls == "CATEGORICAL" and is_free_text_column(df[col]):
            classified[col_str] = "FREE_TEXT"
        else:
            classified[col_str] = base_cls

    return classified


def recommend_charts(df: pd.DataFrame) -> dict:
    total_rows = len(df)
    if total_rows == 0 or len(df.columns) == 0:
        return {
            "total_charts": 0,
            "message": "Dataset is empty. No chart recommendations can be generated.",
            "charts": []
        }

    classified = get_column_classifications(df)

    measures = [c for c, cls in classified.items() if cls == "MEASURE"]
    datetimes = [c for c, cls in classified.items() if cls == "DATETIME"]
    categoricals = [c for c, cls in classified.items() if cls == "CATEGORICAL"]

    valid_axis_cols = {c for c, cls in classified.items() if cls not in EXCLUDED_AXIS_TYPES and cls != "EXCLUDED"}

    candidate_charts: List[dict] = []

    # 1. Line Charts (Datetime + Measure)
    for dt_col in datetimes:
        if dt_col not in valid_axis_cols:
            continue
        for m_col in measures:
            if m_col not in valid_axis_cols:
                continue
            agg = get_default_aggregation(m_col)
            agg_label = "Average" if agg == "AVERAGE" else "Total"
            m_title = m_col.replace("_", " ").title()

            candidate_charts.append({
                "chart_type": "line",
                "title": f"{agg_label} {m_title} Over Time",
                "x_axis": dt_col,
                "y_axis": m_col,
                "legend": None,
                "aggregation": agg,
                "suggested_filters": [],
                "sort": "x_asc",
                "top_n": None,
                "date_granularity": "month" if total_rows > 30 else "day",
                "reason": f"Line chart tracks chronological trend of '{m_col}' using {agg} aggregation."
            })

    # 2. Bar / Column, Donut, and Table Charts (Categorical + Measure)
    donut_count = 0
    for cat_col in categoricals:
        if cat_col not in valid_axis_cols:
            continue
        nunique = int(df[cat_col].nunique(dropna=True))
        cat_title = cat_col.replace("_", " ").title()

        # Extremely high-cardinality categorical (>100 unique or >50% unique rows) -> Recommend Table Chart only
        if nunique > 100 or (total_rows > 20 and nunique / total_rows > 0.5):
            for m_col in measures[:2]:
                if m_col not in valid_axis_cols:
                    continue
                candidate_charts.append({
                    "chart_type": "table",
                    "title": f"{cat_title} Performance Matrix",
                    "x_axis": cat_col,
                    "y_axis": m_col,
                    "legend": None,
                    "aggregation": get_default_aggregation(m_col),
                    "suggested_filters": [],
                    "sort": "value_desc",
                    "top_n": None,
                    "date_granularity": None,
                    "reason": f"Table view presents high-cardinality dimension '{cat_col}' ({nunique} unique values) without cluttering charts."
                })
            continue

        # Normal to Medium/High Cardinality Categoricals (2 to 100 unique values)
        for m_col in measures:
            if m_col not in valid_axis_cols:
                continue
            agg = get_default_aggregation(m_col)
            agg_label = "Average" if agg == "AVERAGE" else "Total"
            m_title = m_col.replace("_", " ").title()

            # Donut chart: 2-6 unique values, max 1 per dataset
            if 2 <= nunique <= 6 and donut_count < 1:
                candidate_charts.append({
                    "chart_type": "donut",
                    "title": f"{m_title} Share by {cat_title}",
                    "x_axis": cat_col,
                    "y_axis": m_col,
                    "legend": cat_col,
                    "aggregation": agg,
                    "suggested_filters": [],
                    "sort": "value_desc",
                    "top_n": None,
                    "date_granularity": None,
                    "reason": f"Donut chart highlights proportion breakdown of '{m_col}' across low-cardinality category '{cat_col}'."
                })
                donut_count += 1

            # Column chart for 2-7 unique values
            if 2 <= nunique <= 7:
                candidate_charts.append({
                    "chart_type": "column",
                    "title": f"{agg_label} {m_title} by {cat_title}",
                    "x_axis": cat_col,
                    "y_axis": m_col,
                    "legend": None,
                    "aggregation": agg,
                    "suggested_filters": [],
                    "sort": "value_desc",
                    "top_n": None,
                    "date_granularity": None,
                    "reason": f"Column chart compares {agg_label.lower()} '{m_col}' across '{cat_col}' categories."
                })
            # Bar chart for 8-20 unique values
            elif 8 <= nunique <= 20:
                candidate_charts.append({
                    "chart_type": "bar",
                    "title": f"{agg_label} {m_title} by {cat_title}",
                    "x_axis": cat_col,
                    "y_axis": m_col,
                    "legend": None,
                    "aggregation": agg,
                    "suggested_filters": [],
                    "sort": "value_desc",
                    "top_n": None,
                    "date_granularity": None,
                    "reason": f"Bar chart compares {agg_label.lower()} '{m_col}' across '{cat_col}' categories."
                })
            # High-cardinality Bar chart (21 to 100 unique values) WITH top_n = 10 limit
            elif 21 <= nunique <= 100:
                candidate_charts.append({
                    "chart_type": "bar",
                    "title": f"Top 10 {cat_title} by {agg_label} {m_title}",
                    "x_axis": cat_col,
                    "y_axis": m_col,
                    "legend": None,
                    "aggregation": agg,
                    "suggested_filters": [],
                    "sort": "value_desc",
                    "top_n": 10,
                    "date_granularity": None,
                    "reason": f"Horizontal bar chart shows top 10 categories for high-cardinality dimension '{cat_col}'."
                })

    # 3. Scatter Charts (Measure + Measure)
    if len(measures) >= 2:
        for i in range(len(measures)):
            m1 = measures[i]
            if m1 not in valid_axis_cols:
                continue
            for j in range(i + 1, len(measures)):
                m2 = measures[j]
                if m2 not in valid_axis_cols:
                    continue
                m1_title = m1.replace("_", " ").title()
                m2_title = m2.replace("_", " ").title()
                candidate_charts.append({
                    "chart_type": "scatter",
                    "title": f"{m1_title} vs {m2_title}",
                    "x_axis": m1,
                    "y_axis": m2,
                    "legend": None,
                    "aggregation": "NONE",
                    "suggested_filters": [],
                    "sort": "none",
                    "top_n": None,
                    "date_granularity": None,
                    "reason": f"Scatter plot evaluates correlation and numerical distribution between '{m1}' and '{m2}'."
                })

    # 4. Fallback: Record count chart if no numeric measures exist
    if not measures:
        for cat_col in categoricals:
            if cat_col not in valid_axis_cols:
                continue
            cat_title = cat_col.replace("_", " ").title()
            candidate_charts.append({
                "chart_type": "column",
                "title": f"Record Count by {cat_title}",
                "x_axis": cat_col,
                "y_axis": "count",
                "legend": None,
                "aggregation": "COUNT",
                "suggested_filters": [],
                "sort": "value_desc",
                "top_n": None,
                "date_granularity": None,
                "reason": f"Column chart compares total record frequency across '{cat_col}' categories."
            })

    # Strict Validation: Remove any chart using EXCLUDED columns
    filtered_candidates = []
    for c in candidate_charts:
        x_cls = classified.get(c["x_axis"], "EXCLUDED")
        y_cls = classified.get(c["y_axis"], "EXCLUDED") if c["y_axis"] != "count" else "MEASURE"
        if x_cls in EXCLUDED_AXIS_TYPES or x_cls == "EXCLUDED":
            continue
        if y_cls in EXCLUDED_AXIS_TYPES or y_cls == "EXCLUDED":
            continue
        filtered_candidates.append(c)

    # Diversity & Variety Selection:
    # Max 2 charts per (chart_type, aggregation) pair in the final list
    final_charts: List[dict] = []
    pair_counts: Dict[Tuple[str, str], int] = {}
    seen_titles: Set[str] = set()

    # Priority order across different chart types to maximize variety:
    # line -> column -> scatter -> donut -> bar -> table
    type_priority = ["line", "column", "scatter", "donut", "bar", "table"]

    # Interleave candidates by chart type
    by_type: Dict[str, List[dict]] = {}
    for c in filtered_candidates:
        by_type.setdefault(c["chart_type"], []).append(c)

    for round_idx in range(6):
        for ctype in type_priority:
            if ctype in by_type and len(by_type[ctype]) > round_idx:
                candidate = by_type[ctype][round_idx]
                title = candidate["title"]
                pair_key = (candidate["chart_type"], candidate["aggregation"])

                if title not in seen_titles and pair_counts.get(pair_key, 0) < MAX_SAME_TYPE_AGG:
                    seen_titles.add(title)
                    pair_counts[pair_key] = pair_counts.get(pair_key, 0) + 1
                    final_charts.append(candidate)
                    if len(final_charts) >= MAX_CHARTS_LIMIT:
                        break
        if len(final_charts) >= MAX_CHARTS_LIMIT:
            break

    # If limit not reached, append remaining valid candidates while strictly respecting MAX_SAME_TYPE_AGG limit
    if len(final_charts) < MAX_CHARTS_LIMIT:
        for c in filtered_candidates:
            title = c["title"]
            pair_key = (c["chart_type"], c["aggregation"])
            if title not in seen_titles and pair_counts.get(pair_key, 0) < MAX_SAME_TYPE_AGG:
                seen_titles.add(title)
                pair_counts[pair_key] = pair_counts.get(pair_key, 0) + 1
                final_charts.append(c)
                if len(final_charts) >= MAX_CHARTS_LIMIT:
                    break

    message: Optional[str] = None
    if not final_charts:
        message = "No suitable columns found for chart recommendations."

    return {
        "total_charts": len(final_charts),
        "message": message,
        "charts": final_charts
    }
