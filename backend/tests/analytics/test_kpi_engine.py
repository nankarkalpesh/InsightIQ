import io
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.session import clear_all_sessions, store_dataset
from app.analytics.kpi_engine import recommend_kpis, classify_column
from app.analytics.dax_engine import (
    generate_sum_dax,
    generate_average_dax,
    generate_count_rows_dax,
    generate_distinct_count_dax,
    generate_ratio_dax
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown_session():
    clear_all_sessions()
    yield
    clear_all_sessions()


def test_dax_engine_generators():
    table = "SalesData"
    
    sum_dax = generate_sum_dax(table, "revenue", "Total Revenue")
    assert sum_dax == "Total Revenue = SUM('SalesData'[revenue])"

    avg_dax = generate_average_dax(table, "unit_price", "Average Unit Price")
    assert avg_dax == "Average Unit Price = AVERAGE('SalesData'[unit_price])"

    rows_dax = generate_count_rows_dax(table, "Total Records")
    assert rows_dax == "Total Records = COUNTROWS('SalesData')"

    distinct_dax = generate_distinct_count_dax(table, "customer_id", "Unique Customer Id")
    assert distinct_dax == "Unique Customer Id = DISTINCTCOUNT('SalesData'[customer_id])"

    ratio_dax = generate_ratio_dax(table, "profit", "sales", "Profit Margin")
    assert ratio_dax == "Profit Margin = DIVIDE(SUM('SalesData'[profit]), SUM('SalesData'[sales]), 0)"


def test_classify_column_coordinate_badge_number_and_measures():
    s_coord = pd.Series([41.8781, 41.8782, 41.8785])
    assert classify_column(s_coord, "latitude") == "COORDINATE"
    assert classify_column(s_coord, "longitude") == "COORDINATE"
    assert classify_column(s_coord, "block_lat") == "COORDINATE"
    assert classify_column(s_coord, "start_lng") == "COORDINATE"

    s_badge = pd.Series([101, 102, 103])
    assert classify_column(s_badge, "badge_number") == "IDENTIFIER"
    assert classify_column(s_badge, "officer_no") == "IDENTIFIER"

    s_amount = pd.Series([100.0, 200.0, 300.0])
    assert classify_column(s_amount, "total_amount") == "MEASURE"
    assert classify_column(s_amount, "damage_value") == "MEASURE"


def test_kpi_recommendation_numeric_and_categorical():
    data = {
        "customer_id": ["C1", "C2", "C3", "C4", "C5"],
        "category": ["Tech", "Health", "Tech", "Retail", "Health"],
        "sales": [100.0, 200.0, 150.0, 300.0, 250.0],
        "profit": [20.0, 50.0, 30.0, 60.0, 40.0]
    }
    df = pd.DataFrame(data)
    result = recommend_kpis(df, table_name="Dataset")

    assert result["total_kpis"] > 0
    assert result["total_kpis"] <= 12
    kpi_names = [k["kpi_name"] for k in result["kpis"]]

    assert "Total Records" in kpi_names
    total_rec_kpi = next(k for k in result["kpis"] if k["kpi_name"] == "Total Records")
    assert total_rec_kpi["value"] == 5

    assert "Total Sales" in kpi_names
    total_sales_kpi = next(k for k in result["kpis"] if k["kpi_name"] == "Total Sales")
    assert total_sales_kpi["value"] == 1000.0

    assert "Average Profit" in kpi_names
    avg_profit_kpi = next(k for k in result["kpis"] if k["kpi_name"] == "Average Profit")
    assert avg_profit_kpi["value"] == 40.0

    assert "Profit Margin" in kpi_names
    margin_kpi = next(k for k in result["kpis"] if k["kpi_name"] == "Profit Margin")
    assert margin_kpi["value"] == 0.2


def test_kpi_recommendation_coordinates_never_in_required_columns():
    data = {
        "incident_id": ["CR-101", "CR-102", "CR-103", "CR-104"],
        "badge_number": [501, 502, 503, 504],
        "latitude": [41.8781, 41.8782, 41.8785, 41.8790],
        "longitude": [-87.6298, -87.6295, -87.6290, -87.6285],
        "incident_datetime": ["2024-01-01 10:00", "2024-01-01 11:30", "2024-01-02 09:15", "2024-01-02 14:00"],
        "year": [2024, 2024, 2024, 2024],
        "zip_code": [60601, 60601, 60602, 60602],
        "damage_amount": [1500.0, 2500.0, 500.0, 4200.0]
    }
    df = pd.DataFrame(data)
    result = recommend_kpis(df, table_name="CrimeDataset")

    # Confirm latitude and longitude NEVER appear in ANY KPI's required_columns anywhere in output
    for kpi in result["kpis"]:
        req_cols = [c.lower() for c in kpi["required_columns"]]
        assert "latitude" not in req_cols, f"latitude found in required_columns of KPI '{kpi['kpi_name']}'"
        assert "longitude" not in req_cols, f"longitude found in required_columns of KPI '{kpi['kpi_name']}'"

    kpi_names = [k["kpi_name"] for k in result["kpis"]]
    assert "Unique Latitude" not in kpi_names
    assert "Unique Longitude" not in kpi_names
    assert "Total Latitude" not in kpi_names
    assert "Total Longitude" not in kpi_names
    assert "Average Latitude" not in kpi_names
    assert "Average Longitude" not in kpi_names

    # MUST contain real additive measures like Total Damage Amount & valid distinct counts like Unique Badge Number
    assert "Total Damage Amount" in kpi_names
    assert "Unique Badge Number" in kpi_names


def test_kpi_recommendation_capping_limit():
    data = {"id": list(range(1, 10))}
    for i in range(1, 20):
        data[f"measure_{i}"] = [i * 10] * 9

    df = pd.DataFrame(data)
    result = recommend_kpis(df, table_name="LargeDataset")

    assert result["total_kpis"] <= 12
    assert len(result["kpis"]) <= 12
    assert len(result["kpis"]) == result["total_kpis"]


def test_kpi_recommendation_no_numeric_columns():
    data = {
        "user_name": ["Alice", "Bob", "Charlie"],
        "city": ["NYC", "LA", "NYC"],
        "status": ["Active", "Active", "Pending"]
    }
    df = pd.DataFrame(data)
    result = recommend_kpis(df, table_name="Dataset")

    assert result["message"] is not None
    assert "No numeric measure columns detected" in result["message"]

    kpi_names = [k["kpi_name"] for k in result["kpis"]]
    assert "Total Records" in kpi_names
    assert "Unique City" in kpi_names
    assert not any("Total " in name and name != "Total Records" for name in kpi_names)


def test_get_dataset_kpis_api_endpoint():
    csv_data = "id,product,units,price\n101,Laptop,2,1200.0\n102,Phone,5,800.0\n103,Tablet,3,400.0\n"
    file_bytes = io.BytesIO(csv_data.encode("utf-8"))

    upload_res = client.post(
        "/api/upload",
        files={"file": ("inventory.csv", file_bytes, "text/csv")}
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    kpi_res = client.get(f"/api/dataset/{file_id}/kpis")
    assert kpi_res.status_code == 200
    res_json = kpi_res.json()

    assert res_json["file_id"] == file_id
    assert res_json["total_kpis"] <= 12
    kpis = res_json["kpis"]
    kpi_map = {k["kpi_name"]: k for k in kpis}

    assert "Total Records" in kpi_map
    assert kpi_map["Total Records"]["value"] == 3

    assert "Total Price" in kpi_map
    assert kpi_map["Total Price"]["value"] == 2400.0


def test_get_dataset_kpis_missing_file_id_returns_404():
    res = client.get("/api/dataset/non_existent_kpi_file_id/kpis")
    assert res.status_code == 404
    json_body = res.json()
    assert "detail" in json_body
    assert json_body["detail"]["error_code"] == "FILE_NOT_FOUND"
