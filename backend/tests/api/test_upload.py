import io
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_csv_file():
    csv_data = "col1,col2\nval1,100\nval2,200\n"
    file_bytes = io.BytesIO(csv_data.encode("utf-8"))
    
    response = client.post(
        "/api/upload",
        files={"file": ("sample.csv", file_bytes, "text/csv")}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "sample.csv"
    assert data["file_type"] == "csv"
    assert data["row_count"] == 2
    assert data["column_count"] == 2
    assert data["requires_sheet_selection"] is False
    assert len(data["columns"]) == 2
    assert data["columns"][0]["name"] == "col1"


def test_upload_excel_multi_sheet_and_select():
    # Prepare Excel workbook in memory with 2 sheets
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame({"a": [1, 2]}).to_excel(writer, sheet_name="SheetA", index=False)
        pd.DataFrame({"b": [3, 4, 5]}).to_excel(writer, sheet_name="SheetB", index=False)
    output.seek(0)

    # 1. Upload Excel file without specifying sheet_name -> should prompt for selection
    response = client.post(
        "/api/upload",
        files={"file": ("multi_sheet.xlsx", output, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["requires_sheet_selection"] is True
    assert data["sheet_names"] == ["SheetA", "SheetB"]
    file_id = data["file_id"]

    # 2. Select sheet 'SheetB'
    select_response = client.post(
        "/api/upload/select-sheet",
        json={"file_id": file_id, "sheet_name": "SheetB"}
    )
    assert select_response.status_code == 200
    select_data = select_response.json()
    assert select_data["selected_sheet"] == "SheetB"
    assert select_data["row_count"] == 3
    assert select_data["column_count"] == 1
    assert select_data["columns"][0]["name"] == "b"


def test_upload_unsupported_file_extension():
    file_bytes = io.BytesIO(b"binary data")
    response = client.post(
        "/api/upload",
        files={"file": ("test.unsupported", file_bytes, "application/octet-stream")}
    )
    assert response.status_code == 400
    res_json = response.json()
    assert "detail" in res_json
    assert res_json["detail"]["error_code"] == "UNSUPPORTED_FILE_TYPE"


def test_upload_empty_file():
    file_bytes = io.BytesIO(b"")
    response = client.post(
        "/api/upload",
        files={"file": ("empty.csv", file_bytes, "text/csv")}
    )
    assert response.status_code == 400
    res_json = response.json()
    assert "detail" in res_json
    assert res_json["detail"]["error_code"] == "EMPTY_FILE"
