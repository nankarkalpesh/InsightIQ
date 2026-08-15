import math
from typing import Dict, List, Any, Optional, Set
import pandas as pd
import numpy as np

from app.analytics.dax_engine import (
    generate_sum_dax,
    generate_average_dax,
    generate_count_rows_dax,
    generate_distinct_count_dax,
    generate_ratio_dax
)
from app.analytics.profiling import dataset_health

COORDINATE_KEYWORDS = {"lat", "latitude", "lng", "lon", "longitude"}

MEASURE_KEYWORDS = {
    "amount", "price", "cost", "total", "sum", "revenue", "sales",
    "loss", "count", "qty", "quantity", "val", "value", "profit",
    "margin", "discount", "fee", "tax", "weight", "volume", "height",
    "width", "distance", "score", "points", "rate", "salary", "wage",
    "income", "expense", "budget", "balance", "fine", "penalty", "duration"
}

IDENTIFIER_KEYWORDS = {
    "id", "uuid", "key", "code", "pk", "index", "no", "number",
    "badge", "zip", "zipcode", "postal", "phone", "year", "fax", "ssn", "ein",
    "account", "serial", "ticket", "license", "vin"
}

STATUS_CATEGORICAL_KEYWORDS = {
    "status", "type", "category", "state", "mode", "flag", "level",
    "tier", "resolution", "result", "outcome", "group", "class"
}

DATETIME_KEYWORDS = {"date", "time", "datetime", "timestamp", "dt", "created", "updated"}

RATIO_PAIRS = [
    ("profit", "revenue", "Profit Margin", "Calculates net profit margin ratio relative to total revenue"),
    ("profit", "sales", "Profit Margin", "Calculates net profit margin ratio relative to total sales"),
    ("cost", "revenue", "Cost-to-Revenue Ratio", "Measures operating costs relative to total revenue"),
    ("cost", "sales", "Cost-to-Sales Ratio", "Measures operating costs relative to total sales"),
    ("discount", "sales", "Discount Rate", "Calculates total discount applied relative to total sales"),
    ("tax", "revenue", "Tax Rate", "Calculates tax paid relative to total revenue")
]

MAX_KPIS_LIMIT = 12


def _clean_kpi_value(val: Any) -> Any:
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        return round(float(val), 2)
    return str(val)


def check_numeric_coercion(series: pd.Series) -> Tuple[bool, Optional[str]]:
    """
    Check if a string/object series consists mostly of numeric values once common
    currency symbols ($, €, £, ¥), commas, percent signs, and whitespace are stripped.
    Returns: (is_coercible, data_quality_note)
    """
    if pd.api.types.is_numeric_dtype(series):
        return False, None

    valid = series.dropna().astype(str).str.strip()
    if valid.empty:
        return False, None

    non_empty = valid[valid != ""]
    if non_empty.empty:
        return False, None

    sample = non_empty.head(500)
    cleaned = sample.str.replace(r'[\$,€£¥%\s]', '', regex=True)

    coerced = pd.to_numeric(cleaned, errors='coerce')
    success_count = int(coerced.notna().sum())
    total_sample = len(sample)

    if total_sample > 0 and (success_count / total_sample) >= 0.75:
        col_name = str(series.name) if series.name else "Column"
        pct = int(round((success_count / total_sample) * 100))
        note = (
            f"Column '{col_name}' is stored as text/object but {pct}% of non-null values "
            f"can be coerced to numeric after stripping currency symbols and formatting (e.g. $, commas). "
            f"Requires type conversion to numeric before modeling."
        )
        return True, note

    return False, None


def classify_column(series: pd.Series, col_name: str, likely_id_cols: Optional[Set[str]] = None) -> str:
    """Classify a DataFrame column into 'COORDINATE', 'MEASURE', 'IDENTIFIER', 'DATETIME', or 'CATEGORICAL'."""
    col_lower = col_name.lower().strip()
    tokens = set(col_lower.replace("-", "_").split("_"))
    likely_id_cols = likely_id_cols or set()

    # Rule 1: Spatial Coordinate check -> COORDINATE (excluded from ALL KPI types)
    if any(t in COORDINATE_KEYWORDS for t in tokens) or any(kw in col_lower for kw in COORDINATE_KEYWORDS):
        return "COORDINATE"

    # Rule 2: Datetime check
    if pd.api.types.is_datetime64_any_dtype(series) or any(t in DATETIME_KEYWORDS for t in tokens):
        return "DATETIME"

    is_numeric = pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)

    # Rule 3a: Count prefix/suffix for numeric series (e.g. num_arrests) -> MEASURE
    count_prefixes = ("num_", "number_of_", "no_of_", "count_of_", "n_")
    count_suffixes = ("_count", "_cnt", "_qty", "_quantity")
    if is_numeric and (col_lower.startswith(count_prefixes) or col_lower.endswith(count_suffixes)):
        return "MEASURE"

    # Rule 3b: Measure keywords take top priority if numeric
    has_measure_kw = any(kw in col_lower for kw in MEASURE_KEYWORDS) or any(t in MEASURE_KEYWORDS for t in tokens)
    if has_measure_kw and is_numeric:
        return "MEASURE"

    # Status / Categorical override for low-cardinality categorical fields (e.g. case_status)
    has_status_kw = any(kw in col_lower for kw in STATUS_CATEGORICAL_KEYWORDS) or any(t in STATUS_CATEGORICAL_KEYWORDS for t in tokens)
    nunique_val = int(series.nunique(dropna=True))
    if has_status_kw and nunique_val <= 50 and not (col_lower.endswith("_id") or col_lower == "id"):
        return "CATEGORICAL"

    # Rule 4: Identifier patterns & keywords
    has_id_kw = any(kw in col_lower for kw in IDENTIFIER_KEYWORDS) or any(t in IDENTIFIER_KEYWORDS for t in tokens)
    has_id_suffix = (
        col_lower.endswith("_id")
        or col_lower.endswith("_number")
        or col_lower.endswith("_no")
        or col_lower.endswith("_code")
        or col_lower.endswith("number")
    )

    if (has_id_kw or has_id_suffix or col_name in likely_id_cols) and not has_measure_kw:
        # Check if it's a numeric count column that shouldn't be an ID
        if is_numeric and not (has_id_suffix or col_lower.endswith("_id") or col_lower in {"id", "uuid", "pk", "key"} or col_name in likely_id_cols):
            return "MEASURE"
        return "IDENTIFIER"

    # Rule 5: Check numeric coercion for text/object columns (e.g. property_loss_usd)
    if not is_numeric:
        is_coercible, _ = check_numeric_coercion(series)
        if is_coercible:
            return "MEASURE"
        return "CATEGORICAL"

    # Rule 6: Value distribution & range heuristics
    valid_series = series.dropna()
    if valid_series.empty:
        return "CATEGORICAL"

    try:
        min_val = float(valid_series.min())
        max_val = float(valid_series.max())
        total_rows = len(series)

        # Coordinate heuristic check
        if "lat" in col_lower and min_val >= -90.0 and max_val <= 90.0:
            return "COORDINATE"
        if ("lon" in col_lower or "lng" in col_lower) and min_val >= -180.0 and max_val <= 180.0:
            return "COORDINATE"

        # 4-digit Year check [1800, 2100] for pure integers
        if (min_val >= 1800 and max_val <= 2100) and (valid_series % 1 == 0).all():
            return "IDENTIFIER"

        # Zip code range check [500, 99999] for integer zip codes
        if "zip" in col_lower and min_val >= 500 and max_val <= 99999:
            return "IDENTIFIER"

        # 100% unique integers in small-medium dataset -> ID only if ID keyword/suffix or sequential 1..N index
        if total_rows > 5 and valid_series.nunique() == total_rows and (valid_series % 1 == 0).all():
            if has_id_kw or has_id_suffix or col_name in likely_id_cols:
                return "IDENTIFIER"
            sorted_vals = valid_series.sort_values().values
            if len(sorted_vals) > 1 and (np.diff(sorted_vals) == 1).all() and sorted_vals[0] in (0, 1):
                return "IDENTIFIER"
    except (ValueError, TypeError):
        pass

    return "MEASURE"


def _to_numeric_series(s: pd.Series) -> pd.Series:
    """Coerce series to numeric float64, stripping common formatting/currency symbols if stored as string."""
    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        return s.dropna()
    cleaned = s.dropna().astype(str).str.replace(r'[\$,€£¥%\s]', '', regex=True)
    return pd.to_numeric(cleaned, errors='coerce').dropna()


def recommend_kpis(df: pd.DataFrame, table_name: str = "Dataset") -> dict:
    total_rows = len(df)
    health = dataset_health(df)
    constant_cols = set(health["constant_columns"])
    likely_id_cols = set(health["likely_id_columns"])

    if total_rows == 0 or len(df.columns) == 0:
        return {
            "total_kpis": 0,
            "message": "Dataset is empty. No KPIs can be calculated.",
            "kpis": []
        }

    # Classify all non-constant columns
    classified: Dict[str, str] = {}
    for col in df.columns:
        col_str = str(col)
        if col_str in constant_cols:
            continue
        classified[col_str] = classify_column(df[col], col_str, likely_id_cols)

    measure_cols = [c for c, cls in classified.items() if cls == "MEASURE"]
    identifier_cols = [c for c, cls in classified.items() if cls == "IDENTIFIER"]
    categorical_cols = [c for c, cls in classified.items() if cls == "CATEGORICAL"]
    datetime_cols = [c for c, cls in classified.items() if cls == "DATETIME"]
    # COORDINATE columns are completely ignored and excluded from all KPI types!

    message: Optional[str] = None
    if not measure_cols:
        message = "No numeric measure columns detected for sum or average KPI recommendations."

    # Priority Rank Collections
    r1_records: List[dict] = []
    r2_ratios: List[dict] = []
    r3_sums: List[dict] = []
    r4_averages: List[dict] = []
    r5_distincts: List[dict] = []

    # 1. Baseline Row Count (Rank 1)
    r1_records.append({
        "kpi_name": "Total Records",
        "value": total_rows,
        "definition": "Total number of rows/records in the dataset",
        "required_columns": [],
        "calculation_logic": "COUNTROWS of all dataset records",
        "reason": "Provides baseline dataset volume metric",
        "dax": generate_count_rows_dax(table_name, "Total Records")
    })

    # 2. Ratio / Margin KPIs (Rank 2)
    if len(measure_cols) >= 2:
        col_map = {c.lower().strip(): c for c in measure_cols}
        for num_kw, den_kw, measure_title, desc in RATIO_PAIRS:
            num_match = next((col_map[k] for k in col_map if num_kw in k), None)
            den_match = next((col_map[k] for k in col_map if den_kw in k and k != num_match), None)

            if num_match and den_match:
                den_num_s = _to_numeric_series(df[den_match])
                num_num_s = _to_numeric_series(df[num_match])
                den_sum = float(den_num_s.sum()) if not den_num_s.empty else 0.0
                num_sum = float(num_num_s.sum()) if not num_num_s.empty else 0.0
                ratio_val = round(float(num_sum / den_sum), 4) if den_sum != 0 else 0.0

                r2_ratios.append({
                    "kpi_name": measure_title,
                    "value": ratio_val,
                    "definition": desc,
                    "required_columns": [num_match, den_match],
                    "calculation_logic": f"DIVIDE(SUM('{num_match}'), SUM('{den_match}'))",
                    "reason": f"Calculates relationship between '{num_match}' and '{den_match}'",
                    "dax": generate_ratio_dax(table_name, num_match, den_match, measure_title)
                })

    # 3. Sum & Average KPIs for valid measures (Rank 3 & Rank 4)
    for col in measure_cols:
        series = _to_numeric_series(df[col])
        if series.empty:
            continue

        col_title = col.replace("_", " ").title()

        # Sum KPI (Rank 3)
        total_val = _clean_kpi_value(series.sum())
        kpi_sum_name = f"Total {col_title}"
        r3_sums.append({
            "kpi_name": kpi_sum_name,
            "value": total_val,
            "definition": f"Total sum of all values in column '{col}'",
            "required_columns": [col],
            "calculation_logic": f"SUM of column '{col}'",
            "reason": f"Aggregates total volume for measure '{col}'",
            "dax": generate_sum_dax(table_name, col, kpi_sum_name)
        })

        # Average KPI (Rank 4)
        avg_val = _clean_kpi_value(series.mean())
        kpi_avg_name = f"Average {col_title}"
        r4_averages.append({
            "kpi_name": kpi_avg_name,
            "value": avg_val,
            "definition": f"Mean average value for column '{col}'",
            "required_columns": [col],
            "calculation_logic": f"AVERAGE of column '{col}'",
            "reason": f"Provides central tendency metric for measure '{col}'",
            "dax": generate_average_dax(table_name, col, kpi_avg_name)
        })

    # 4. Distinct Count KPIs (Rank 5) - Moderate cardinality dimensions first, then identifiers
    # 4a. Categorical / Dimension columns with moderate cardinality (2-500)
    for col in categorical_cols:
        series = df[col]
        nunique = int(series.nunique(dropna=True))
        if 1 < nunique <= max(500, total_rows):
            col_title = col.replace("_", " ").title()
            kpi_name = f"Unique {col_title}"
            r5_distincts.append({
                "kpi_name": kpi_name,
                "value": nunique,
                "definition": f"Number of distinct unique values in '{col}'",
                "required_columns": [col],
                "calculation_logic": f"DISTINCTCOUNT of column '{col}'",
                "reason": f"Measures entity diversity for column '{col}'",
                "dax": generate_distinct_count_dax(table_name, col, kpi_name)
            })

    # 4b. Identifier columns
    for col in identifier_cols:
        series = df[col]
        nunique = int(series.nunique(dropna=True))
        if 1 < nunique <= total_rows:
            col_title = col.replace("_", " ").title()
            kpi_name = f"Unique {col_title}"
            r5_distincts.append({
                "kpi_name": kpi_name,
                "value": nunique,
                "definition": f"Number of distinct unique values in '{col}'",
                "required_columns": [col],
                "calculation_logic": f"DISTINCTCOUNT of column '{col}'",
                "reason": f"Measures entity diversity for column '{col}'",
                "dax": generate_distinct_count_dax(table_name, col, kpi_name)
            })

    # 4c. Datetime columns (deprioritized: only if low cardinality, e.g. year/month bins)
    for col in datetime_cols:
        series = df[col]
        nunique = int(series.nunique(dropna=True))
        # Deprioritize near-unique timestamps (only include if nunique <= 100 and < 50% of total rows)
        if 1 < nunique <= 100 and (total_rows == 0 or nunique / total_rows < 0.5):
            col_title = col.replace("_", " ").title()
            kpi_name = f"Unique {col_title}"
            r5_distincts.append({
                "kpi_name": kpi_name,
                "value": nunique,
                "definition": f"Number of distinct unique values in '{col}'",
                "required_columns": [col],
                "calculation_logic": f"DISTINCTCOUNT of column '{col}'",
                "reason": f"Measures entity diversity for column '{col}'",
                "dax": generate_distinct_count_dax(table_name, col, kpi_name)
            })

    # Assemble ranked KPIs and apply cap limit (MAX_KPIS_LIMIT = 12)
    all_ranked_kpis = r1_records + r2_ratios + r3_sums + r4_averages + r5_distincts

    # Deduplicate by kpi_name while preserving order
    seen_names = set()
    unique_ranked_kpis = []
    for kpi in all_ranked_kpis:
        if kpi["kpi_name"] not in seen_names:
            seen_names.add(kpi["kpi_name"])
            unique_ranked_kpis.append(kpi)

    final_kpis = unique_ranked_kpis[:MAX_KPIS_LIMIT]

    return {
        "total_kpis": len(final_kpis),
        "message": message,
        "kpis": final_kpis
    }
