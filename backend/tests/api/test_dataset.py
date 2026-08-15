import io
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.session import clear_all_sessions

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown_session():
    clear_all_sessions()
    yield
    clear_all_sessions()


def test_dataset_overview_and_preview_flow():
    # 1. Upload sample CSV file
    csv_content = (
        "id,name,score,category\n"
        "1,Alice,88.5,A\n"
        "2,Bob,92.0,B\n"
        "3,Charlie,75.0,A\n"
        "4,Diana,95.5,A\n"
        "5,Eve,81.0,B\n"
    )
    file_bytes = io.BytesIO(csv_content.encode("utf-8"))

    upload_res = client.post(
        "/api/upload",
        files={"file": ("students.csv", file_bytes, "text/csv")}
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    # 2. Get dataset overview
    overview_res = client.get(f"/api/dataset/{file_id}/overview")
    assert overview_res.status_code == 200
    overview_data = overview_res.json()

    assert overview_data["file_id"] == file_id
    assert overview_data["health"]["total_rows"] == 5
    assert overview_data["health"]["total_columns"] == 4
    assert overview_data["health"]["quality_score"] == 100.0
    assert len(overview_data["schema"]) == 4
    assert "score" in overview_data["statistics"]["numeric"]
    assert len(overview_data["insights"]) > 0

    # 3. Get paginated preview (page 1, page_size 2)
    preview_res = client.get(f"/api/dataset/{file_id}/preview?page=1&page_size=2")
    assert preview_res.status_code == 200
    p1_data = preview_res.json()

    assert p1_data["file_id"] == file_id
    assert p1_data["page"] == 1
    assert p1_data["page_size"] == 2
    assert p1_data["total_rows"] == 5
    assert p1_data["total_pages"] == 3
    assert len(p1_data["data"]) == 2
    assert p1_data["data"][0]["name"] == "Alice"
    assert p1_data["data"][1]["name"] == "Bob"

    # 4. Get paginated preview (page 2, page_size 2)
    preview_p2 = client.get(f"/api/dataset/{file_id}/preview?page=2&page_size=2")
    assert preview_p2.status_code == 200
    p2_data = preview_p2.json()
    assert len(p2_data["data"]) == 2
    assert p2_data["data"][0]["name"] == "Charlie"


def test_dataset_overview_missing_file_id_returns_404():
    res = client.get("/api/dataset/non_existent_file_id_12345/overview")
    assert res.status_code == 404
    json_body = res.json()
    assert "detail" in json_body
    assert json_body["detail"]["error_code"] == "FILE_NOT_FOUND"


def test_dataset_preview_missing_file_id_returns_404():
    res = client.get("/api/dataset/non_existent_file_id_12345/preview")
    assert res.status_code == 404
    json_body = res.json()
    assert "detail" in json_body
    assert json_body["detail"]["error_code"] == "FILE_NOT_FOUND"
