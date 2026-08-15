import io
import pandas as pd
import pytest
from collections import Counter
from fastapi.testclient import TestClient

from app.main import app
from app.core.session import clear_all_sessions
from app.analytics.chart_engine import recommend_charts, is_free_text_column, get_default_aggregation

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown_session():
    clear_all_sessions()
    yield
    clear_all_sessions()


def test_free_text_detection():
    short_series = pd.Series(["Tech", "Health", "Retail"])
    assert not is_free_text_column(short_series)

    long_series = pd.Series([
        "This is a long detailed description of an incident occurring at midnight near the central park entrance.",
        "Another very descriptive narrative text explaining full context, officer notes, and witness accounts in detail.",
        "Detailed forensic log text containing comprehensive notes, timestamps, and investigation progress update details."
    ])
    assert is_free_text_column(long_series)


def test_default_aggregation_for_age_and_measures():
    assert get_default_aggregation("victim_age") == "AVERAGE"
    assert get_default_aggregation("suspect_age") == "AVERAGE"
    assert get_default_aggregation("crime_rate") == "AVERAGE"
    assert get_default_aggregation("satisfaction_score") == "AVERAGE"

    assert get_default_aggregation("stolen_value") == "SUM"
    assert get_default_aggregation("damage_amount") == "SUM"
    assert get_default_aggregation("total_sales") == "SUM"
    assert get_default_aggregation("quantity") == "SUM"


def test_chart_recommendation_categorical_numeric_datetime():
    data = {
        "order_date": pd.date_range("2024-01-01", periods=10, freq="D").strftime("%Y-%m-%d"),
        "category": ["Tech", "Health", "Tech", "Retail", "Health", "Tech", "Retail", "Health", "Tech", "Retail"],
        "sales": [100.0, 200.0, 150.0, 300.0, 250.0, 180.0, 220.0, 310.0, 400.0, 190.0],
        "profit": [20.0, 50.0, 30.0, 60.0, 40.0, 35.0, 45.0, 70.0, 90.0, 38.0]
    }
    df = pd.DataFrame(data)
    result = recommend_charts(df)

    assert result["total_charts"] > 0
    assert result["total_charts"] <= 8
    charts = result["charts"]
    chart_types = [c["chart_type"] for c in charts]

    assert "line" in chart_types
    line_chart = next(c for c in charts if c["chart_type"] == "line")
    assert line_chart["x_axis"] == "order_date"
    assert line_chart["y_axis"] in ["sales", "profit"]

    assert any(c["chart_type"] in ["column", "donut"] for c in charts)

    assert "scatter" in chart_types
    scatter_chart = next(c for c in charts if c["chart_type"] == "scatter")
    assert set([scatter_chart["x_axis"], scatter_chart["y_axis"]]) == {"sales", "profit"}


def test_chart_recommendation_never_uses_coordinates_identifiers_or_freetext_as_axes():
    data = {
        "incident_id": ["CR-101", "CR-102", "CR-103", "CR-104", "CR-105"],
        "badge_number": [501, 502, 503, 504, 505],
        "latitude": [41.8781, 41.8782, 41.8785, 41.8790, 41.8795],
        "longitude": [-87.6298, -87.6295, -87.6290, -87.6285, -87.6280],
        "description": [
            "Comprehensive narrative detailing severe traffic collision at intersection with major structural damage.",
            "Officer notes regarding property theft from commercial building during late night patrol shift hours.",
            "Detailed investigation summary report regarding stolen vehicle recovery and suspect apprehension.",
            "Incident log entry describing emergency response to alarm trigger at financial institution.",
            "Patrol unit report regarding public disturbance resolution and verbal warning issued."
        ],
        "district": ["North", "South", "North", "East", "West"],
        "stolen_value": [1500.0, 2500.0, 500.0, 4200.0, 1100.0]
    }
    df = pd.DataFrame(data)
    result = recommend_charts(df)

    excluded_cols = {"incident_id", "badge_number", "latitude", "longitude", "description"}
    for chart in result["charts"]:
        assert chart["x_axis"] not in excluded_cols, f"Excluded column '{chart['x_axis']}' found as x_axis in chart '{chart['title']}'"
        assert chart["y_axis"] not in excluded_cols, f"Excluded column '{chart['y_axis']}' found as y_axis in chart '{chart['title']}'"
        if chart["legend"]:
            assert chart["legend"] not in excluded_cols, f"Excluded column '{chart['legend']}' found as legend in chart '{chart['title']}'"


def test_high_cardinality_categorical_top_n_limit_and_table():
    # 60 unique categories (high cardinality > 50)
    categories = [f"Location_{i}" for i in range(1, 61)]
    data = {
        "location": categories * 2,
        "victim_age": list(range(20, 80)) * 2,
        "stolen_value": [100.0 * i for i in range(1, 121)]
    }
    df = pd.DataFrame(data)
    result = recommend_charts(df)

    # Confirm no chart uses location as chart axis without top_n limit (or rendered as table)
    for chart in result["charts"]:
        if chart["x_axis"] == "location" and chart["chart_type"] in ["bar", "column", "donut"]:
            assert chart["top_n"] is not None and chart["top_n"] <= 20, f"Chart '{chart['title']}' has no top_n limit for high cardinality location"

    # Confirm age column defaults to AVERAGE
    age_charts = [c for c in result["charts"] if c["y_axis"] == "victim_age"]
    for c in age_charts:
        assert c["aggregation"] == "AVERAGE", f"Chart '{c['title']}' should use AVERAGE aggregation for victim_age"


def test_variety_limit_max_two_same_chart_type_and_aggregation():
    # Create dataset with 10 numeric measure columns and 5 categorical columns
    data = {"date": pd.date_range("2024-01-01", periods=20, freq="D").strftime("%Y-%m-%d")}
    for i in range(1, 6):
        data[f"cat_{i}"] = ["TypeA", "TypeB", "TypeC", "TypeD"] * 5
    for i in range(1, 10):
        data[f"measure_{i}"] = [i * 15.0] * 20

    df = pd.DataFrame(data)
    result = recommend_charts(df)

    assert result["total_charts"] <= 8
    charts = result["charts"]

    # Confirm no more than 2 charts share the exact same (chart_type, aggregation) pair
    pair_counts = Counter((c["chart_type"], c["aggregation"]) for c in charts)
    for pair, count in pair_counts.items():
        assert count <= 2, f"Pair {pair} appeared {count} times in recommendations (max allowed is 2)"


def test_get_dataset_charts_api_endpoint():
    csv_data = "date,category,units,price\n2024-01-01,Laptop,2,1200.0\n2024-01-02,Phone,5,800.0\n2024-01-03,Tablet,3,400.0\n"
    file_bytes = io.BytesIO(csv_data.encode("utf-8"))

    upload_res = client.post(
        "/api/upload",
        files={"file": ("inventory.csv", file_bytes, "text/csv")}
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    chart_res = client.get(f"/api/dataset/{file_id}/charts")
    assert chart_res.status_code == 200
    res_json = chart_res.json()

    assert res_json["file_id"] == file_id
    assert res_json["total_charts"] > 0
    assert res_json["total_charts"] <= 8
    charts = res_json["charts"]

    first_chart = charts[0]
    assert "chart_type" in first_chart
    assert "title" in first_chart
    assert "x_axis" in first_chart
    assert "y_axis" in first_chart
    assert "reason" in first_chart
