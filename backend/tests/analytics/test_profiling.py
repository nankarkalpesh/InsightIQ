import numpy as np
import pandas as pd
import pytest

from app.analytics.profiling import (
    dataset_health,
    column_schema,
    column_statistics,
    generate_insights
)


def create_sample_df() -> pd.DataFrame:
    data = {
        "id": [1, 2, 3, 4, 1],
        "category": ["A", "B", "A", "C", "A"],
        "price": [10.5, 20.0, None, 40.0, 10.5],
        "constant_col": ["fixed", "fixed", "fixed", "fixed", "fixed"],
        "created_at": pd.to_datetime([
            "2026-01-01",
            "2026-01-02",
            "2026-01-05",
            "2026-01-10",
            "2026-01-01"
        ])
    }
    return pd.DataFrame(data)


def test_dataset_health_with_nulls_and_duplicates():
    df = create_sample_df()
    health = dataset_health(df)

    assert health["total_rows"] == 5
    assert health["total_columns"] == 5
    assert health["missing_cells"] == 1
    assert health["duplicate_rows"] == 1
    assert health["quality_score"] < 100.0
    assert "constant_col" in health["constant_columns"]
    assert "id" in health["likely_id_columns"]


def test_column_schema():
    df = create_sample_df()
    schema = column_schema(df)

    assert len(schema) == 5
    price_schema = next(col for col in schema if col["name"] == "price")
    assert price_schema["null_count"] == 1
    assert price_schema["null_percentage"] == 20.0
    assert price_schema["sample_value"] == 10.5

    const_schema = next(col for col in schema if col["name"] == "constant_col")
    assert const_schema["unique_count"] == 1
    assert const_schema["sample_value"] == "fixed"


def test_column_statistics_numeric_categorical_datetime():
    df = create_sample_df()
    stats = column_statistics(df)

    # Numeric stats check (price: 10.5, 20.0, 40.0, 10.5)
    assert "price" in stats["numeric"]
    p_stats = stats["numeric"]["price"]
    assert p_stats["min"] == 10.5
    assert p_stats["max"] == 40.0
    assert p_stats["mean"] == 20.25
    assert p_stats["median"] == 15.25

    # Categorical stats check (category: A=3, B=1, C=1)
    assert "category" in stats["categorical"]
    cat_top = stats["categorical"]["category"]["top_values"]
    assert len(cat_top) == 3
    assert cat_top[0]["value"] == "A"
    assert cat_top[0]["count"] == 3

    # Datetime stats check
    assert "created_at" in stats["datetime"]
    dt_stats = stats["datetime"]["created_at"]
    assert dt_stats["min"] == "2026-01-01 00:00:00"
    assert dt_stats["max"] == "2026-01-10 00:00:00"
    assert dt_stats["range_days"] == 9.0


def test_generate_insights():
    df = create_sample_df()
    insights = generate_insights(df)

    assert isinstance(insights, list)
    assert len(insights) >= 3
    assert any("5 rows and 5 columns" in text for text in insights)
    assert any("quality score" in text.lower() for text in insights)
    assert any("duplicate" in text.lower() for text in insights)
    assert any("constant" in text.lower() for text in insights)
