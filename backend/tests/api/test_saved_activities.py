import io
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.db_models import DatasetModel, DatasetFileBlobModel, DashboardConfigModel, TrainingRunModel, ChatConversationModel
from app.core.session import remove_dataset, _dataset_sessions
from app.core.storage import get_local_cache_path
import os

client = TestClient(app)


def test_saved_activities_full_lifecycle_and_security(monkeypatch):
    # 1. Signup User A and User B
    id_a = uuid.uuid4().hex[:8]
    id_b = uuid.uuid4().hex[:8]
    email_a = f"user_a_{id_a}@example.com"
    email_b = f"user_b_{id_b}@example.com"
    password = "SecurePassword123!"

    s_a = client.post("/api/auth/signup", json={"email": email_a, "password": password})
    assert s_a.status_code == 200
    token_a = s_a.json()["access_token"]
    user_a_id = s_a.json()["user"]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    s_b = client.post("/api/auth/signup", json={"email": email_b, "password": password})
    assert s_b.status_code == 200
    token_b = s_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 2. User A uploads a dataset
    csv_data = "department,budget,employees\nSales,500000,25\nEngineering,1200000,45\nMarketing,300000,12\n"
    files = {"file": ("budget_analysis.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}

    upload_res = client.post("/api/upload", files=files, headers=headers_a)
    assert upload_res.status_code == 201
    file_id_a = upload_res.json()["file_id"]

    # 3. Guest (unauthenticated) attempts to call save-activity -> REJECTED 401
    guest_save = client.post(f"/api/user/datasets/{file_id_a}/save-activity")
    assert guest_save.status_code == 401

    # 4. User A explicitly saves activity -> SUCCESS
    save_res_a = client.post(
        f"/api/user/datasets/{file_id_a}/save-activity",
        json={
            "activity_name": "Q3 Departmental Budget Analysis",
            "dashboard_items": [{"id": "kpi_budget", "type": "kpi"}]
        },
        headers=headers_a
    )
    assert save_res_a.status_code == 200
    assert save_res_a.json()["status"] == "saved"
    assert "saved_at" in save_res_a.json()

    # 5. User A lists saved activities -> Returns Q3 Budget Analysis
    list_a = client.get("/api/user/datasets", headers=headers_a)
    assert list_a.status_code == 200
    ds_list = list_a.json()["datasets"]
    assert len(ds_list) >= 1
    target_item = next((item for item in ds_list if item["file_id"] == file_id_a), None)
    assert target_item is not None
    assert target_item["activity_name"] == "Q3 Departmental Budget Analysis"
    assert target_item["filename"] == "budget_analysis.csv"

    # 6. SECURITY ISOLATION: User B cannot list, open, or delete User A's activity
    list_b = client.get("/api/user/datasets", headers=headers_b)
    assert list_b.status_code == 200
    assert not any(item["file_id"] == file_id_a for item in list_b.json()["datasets"])

    open_b = client.get(f"/api/user/datasets/{file_id_a}/resume", headers=headers_b)
    assert open_b.status_code in (403, 404)

    delete_b = client.delete(f"/api/user/datasets/{file_id_a}", headers=headers_b)
    assert delete_b.status_code in (403, 404)

    # 7. BLOB HYDRATION: Simulate disk wipe & session eviction -> Activity fully restores from DB blob!
    remove_dataset(file_id_a)
    assert file_id_a not in _dataset_sessions
    local_disk_file = get_local_cache_path(file_id_a, "budget_analysis.csv", user_a_id)
    if os.path.exists(local_disk_file):
        os.remove(local_disk_file)
    assert not os.path.exists(local_disk_file)

    resume_a = client.get(f"/api/user/datasets/{file_id_a}/resume", headers=headers_a)
    assert resume_a.status_code == 200
    assert resume_a.json()["dataset"]["file_id"] == file_id_a
    assert resume_a.json()["dataset"]["health"]["total_rows"] == 3

    # 8. IDEMPOTENT REPEATED SAVES: Save again updates timestamps without duplicate records
    save_again = client.post(
        f"/api/user/datasets/{file_id_a}/save-activity",
        json={"activity_name": "Updated Q3 Budget Analysis"},
        headers=headers_a
    )
    assert save_again.status_code == 200
    list_again = client.get("/api/user/datasets", headers=headers_a)
    matching = [d for d in list_again.json()["datasets"] if d["file_id"] == file_id_a]
    assert len(matching) == 1
    assert matching[0]["activity_name"] == "Updated Q3 Budget Analysis"

    # 9. DELETE ACTIVITY: User A deletes activity -> removes DB record, blob, dashboard, disk file
    del_res = client.delete(f"/api/user/datasets/{file_id_a}", headers=headers_a)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify activity no longer present in listing or database
    list_after_del = client.get("/api/user/datasets", headers=headers_a)
    assert not any(item["file_id"] == file_id_a for item in list_after_del.json()["datasets"])

    db = SessionLocal()
    try:
        ds_rec = db.query(DatasetModel).filter(DatasetModel.id == file_id_a).first()
        assert ds_rec is None
        blob_rec = db.query(DatasetFileBlobModel).filter(DatasetFileBlobModel.file_id == file_id_a).first()
        assert blob_rec is None
    finally:
        db.close()
