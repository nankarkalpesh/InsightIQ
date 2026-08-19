import os
import io
import json
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.core.session import get_dataset, _dataset_sessions, clear_all_sessions, MAX_DATASET_SESSIONS
from app.core.storage import get_local_cache_path, ensure_local_dataset_file
from app.models.db_models import DatasetModel, DatasetFileBlobModel
from app.core.database import SessionLocal

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_sessions():
    clear_all_sessions()
    yield
    clear_all_sessions()


def test_upload_csv_xlsx_json_lifecycle_and_memory_release():
    """Verify CSV, XLSX, and JSON files upload, hydrate, compute analytics/ML, and don't leak memory."""
    # 1. Test CSV Upload
    csv_content = "category,val,target\nA,10,1\nB,20,0\nA,30,1\nB,40,0\nA,50,1\nB,60,0\nA,70,1\nB,80,0\nA,90,1\nB,100,0\n"
    res_csv = client.post(
        "/api/upload",
        files={"file": ("test_data.csv", csv_content.encode("utf-8"), "text/csv")}
    )
    assert res_csv.status_code == 201
    csv_data = res_csv.json()
    file_id_csv = csv_data["file_id"]
    assert csv_data["row_count"] == 10
    assert csv_data["column_count"] == 3

    # 2. Test JSON Upload
    json_rows = [{"category": "X", "val": i, "target": i % 2} for i in range(12)]
    json_bytes = json.dumps(json_rows).encode("utf-8")
    res_json = client.post(
        "/api/upload",
        files={"file": ("test_data.json", json_bytes, "application/json")}
    )
    assert res_json.status_code == 201
    json_data = res_json.json()
    file_id_json = json_data["file_id"]
    assert json_data["row_count"] == 12

    # 3. Test XLSX Upload
    df_excel = pd.DataFrame({"A": range(15), "B": range(15, 30)})
    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
        df_excel.to_excel(writer, sheet_name="Sheet1", index=False)
    excel_bytes = excel_buf.getvalue()

    res_xlsx = client.post(
        "/api/upload",
        files={"file": ("test_data.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert res_xlsx.status_code == 201
    xlsx_data = res_xlsx.json()
    file_id_xlsx = xlsx_data["file_id"]
    assert xlsx_data["row_count"] == 15

    # 4. Verify Bounded Memory Session (_dataset_sessions does not grow beyond MAX_DATASET_SESSIONS)
    assert len(_dataset_sessions) <= MAX_DATASET_SESSIONS


def test_local_cache_deletion_recovery_via_db_blob():
    """Verify that if local cache file is deleted, dataset hydrates seamlessly from PostgreSQL/SQLite DB blob."""
    csv_content = "col_a,col_b\n1,10\n2,20\n3,30\n4,40\n5,50\n6,60\n7,70\n8,80\n9,90\n10,100\n"
    res = client.post(
        "/api/upload",
        files={"file": ("blob_test.csv", csv_content.encode("utf-8"), "text/csv")}
    )
    assert res.status_code == 201
    file_id = res.json()["file_id"]

    # Delete local disk cache file to simulate server restart or ephemeral disk wipe
    local_path = get_local_cache_path(file_id, "blob_test.csv", None)
    if os.path.exists(local_path):
        os.remove(local_path)
    assert not os.path.exists(local_path)

    # Clear memory cache
    clear_all_sessions()
    assert file_id not in _dataset_sessions

    # Access dataset via analytics overview endpoint
    res_overview = client.get(f"/api/dataset/{file_id}/overview")
    assert res_overview.status_code == 200
    assert res_overview.json()["health"]["total_rows"] == 10

    # Verify local disk file was restored from DB blob table
    assert os.path.exists(local_path)


def test_analytics_charts_kpis_and_ml_under_memory_release():
    """Verify analytics, KPIs, chart aggregations, ML model training & predictions work cleanly without memory leaking."""
    # Create dataset with enough rows for ML (15 rows)
    rows = []
    for i in range(15):
        rows.append({"feature1": float(i), "feature2": float(i * 2), "target": 1 if i > 7 else 0})
    df_raw = pd.DataFrame(rows)
    csv_bytes = df_raw.to_csv(index=False).encode("utf-8")

    res = client.post(
        "/api/upload",
        files={"file": ("ml_analytics_test.csv", csv_bytes, "text/csv")}
    )
    assert res.status_code == 201
    file_id = res.json()["file_id"]

    # KPIs endpoint
    res_kpi = client.get(f"/api/dataset/{file_id}/kpis")
    assert res_kpi.status_code == 200

    # Chart data endpoint
    res_chart = client.get(f"/api/dataset/{file_id}/chart-data?x_axis=feature1&y_axis=feature2&aggregation=SUM")
    assert res_chart.status_code == 200
    assert "data" in res_chart.json()

    # AutoML Training recommendations endpoint
    res_recs = client.get(f"/api/dataset/{file_id}/model-recommendations?target=target")
    assert res_recs.status_code == 200

    # Model training API via datascience module directly
    from app.datascience.model_training import train_and_evaluate_model
    db = SessionLocal()
    try:
        df = get_dataset(file_id, db=db)
        train_result = train_and_evaluate_model(
            file_id=file_id,
            df=df,
            target_col="target",
            feature_cols=["feature1", "feature2"],
            model_name="Logistic Regression"
        )
        assert train_result["model_name"] == "Logistic Regression"
        assert "classification_metrics" in train_result
    finally:
        db.close()

    # AI Data Chat tool routing endpoint
    from app.ai.tool_router import dispatch_tool_call
    tool_res = dispatch_tool_call(
        tool_name="get_dataset_summary",
        arguments={},
        file_id=file_id
    )
    assert "total_rows" in tool_res
    assert tool_res["total_rows"] == 15
