import io
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.session import clear_all_sessions
from app.analytics.chart_data import get_chart_data

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown_session():
    clear_all_sessions()
    yield
    clear_all_sessions()


def test_get_chart_data_bar_aggregation_sum_and_average():
    data = {
        "category": ["Tech", "Health", "Tech", "Retail", "Health"],
        "sales": [100.0, 200.0, 300.0, 400.0, 500.0],
        "score": [10.0, 20.0, 30.0, 40.0, 50.0]
    }
    df = pd.DataFrame(data)

    # SUM aggregation on sales by category
    sum_result = get_chart_data(df, x_axis="category", y_axis="sales", aggregation="SUM", chart_type="bar")
    assert sum_result["total_points"] == 3
    points_map = {p["name"]: p["value"] for p in sum_result["data"]}

    # Tech sum = 100 + 300 = 400
    assert points_map["Tech"] == 400.0
    # Health sum = 200 + 500 = 700
    assert points_map["Health"] == 700.0
    # Retail sum = 400
    assert points_map["Retail"] == 400.0

    # AVERAGE aggregation on score by category
    avg_result = get_chart_data(df, x_axis="category", y_axis="score", aggregation="AVERAGE", chart_type="column")
    avg_map = {p["name"]: p["value"] for p in avg_result["data"]}

    # Tech avg score = (10 + 30) / 2 = 20.0
    assert avg_map["Tech"] == 20.0
    # Health avg score = (20 + 50) / 2 = 35.0
    assert avg_map["Health"] == 35.0


def test_get_chart_data_top_n_limit():
    data = {
        "category": [f"Cat_{i}" for i in range(1, 21)],
        "sales": [float(i * 10) for i in range(1, 21)]
    }
    df = pd.DataFrame(data)

    result = get_chart_data(df, x_axis="category", y_axis="sales", aggregation="SUM", chart_type="bar", top_n=5)
    assert result["total_points"] == 5
    assert len(result["data"]) == 5
    # Should be sorted descending, top value = 200.0 (Cat_20)
    assert result["data"][0]["name"] == "Cat_20"
    assert result["data"][0]["value"] == 200.0


def test_get_chart_data_line_date_grouping():
    data = {
        "date_str": ["2024-01-15", "2024-01-20", "2024-02-10", "2024-02-14", "2024-03-01"],
        "sales": [10.0, 20.0, 30.0, 40.0, 50.0]
    }
    df = pd.DataFrame(data)

    # Group by month
    month_res = get_chart_data(df, x_axis="date_str", y_axis="sales", aggregation="SUM", chart_type="line", date_granularity="month")
    assert month_res["total_points"] == 3
    months_map = {p["name"]: p["value"] for p in month_res["data"]}

    assert months_map["2024-01"] == 30.0
    assert months_map["2024-02"] == 70.0
    assert months_map["2024-03"] == 50.0


def test_get_chart_data_scatter_sampling_cap():
    # 600 numeric data points
    data = {
        "height": list(range(100, 700)),
        "weight": [i * 0.5 for i in range(100, 700)]
    }
    df = pd.DataFrame(data)

    result = get_chart_data(df, x_axis="height", y_axis="weight", aggregation="NONE", chart_type="scatter")
    assert result["total_points"] == 500
    assert len(result["data"]) == 500
    assert "x" in result["data"][0]
    assert "y" in result["data"][0]


def test_chart_data_api_endpoint():
    csv_data = "category,sales\nLaptop,1200.0\nPhone,800.0\nLaptop,400.0\nPhone,300.0\nTablet,500.0\n"
    file_bytes = io.BytesIO(csv_data.encode("utf-8"))

    upload_res = client.post(
        "/api/upload",
        files={"file": ("sales.csv", file_bytes, "text/csv")}
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    # Query GET /api/dataset/{file_id}/chart-data
    res = client.get(
        f"/api/dataset/{file_id}/chart-data",
        params={
            "x_axis": "category",
            "y_axis": "sales",
            "aggregation": "SUM",
            "chart_type": "bar",
            "top_n": 10
        }
    )
    assert res.status_code == 200
    res_json = res.json()

    assert res_json["file_id"] == file_id
    assert res_json["x_axis"] == "category"
    assert res_json["y_axis"] == "sales"
    assert res_json["total_points"] == 3
    assert len(res_json["data"]) == 3
