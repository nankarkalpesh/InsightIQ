import io
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.security import get_password_hash, verify_password
from app.auth.jwt import create_access_token, decode_access_token
from app.core.database import SessionLocal
from app.models.db_models import User, DatasetModel

client = TestClient(app)


def test_password_hashing_and_verification():
    raw_pass = "SecurePass123!"
    hashed = get_password_hash(raw_pass)
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_encode_and_decode():
    payload = {"sub": "user_123_abc", "email": "test@example.com"}
    token = create_access_token(payload)
    assert isinstance(token, str) and len(token) > 20

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user_123_abc"
    assert decoded["email"] == "test@example.com"

    # Tampered token
    assert decode_access_token("invalid.jwt.token") is None


def test_signup_login_and_me_flow():
    unique_id = uuid.uuid4().hex[:8]
    email = f"auth_user_{unique_id}@example.com"
    password = "MySecretPassword123"
    display_name = "Auth Test User"

    # 1. Signup
    signup_res = client.post("/api/auth/signup", json={
        "email": email,
        "password": password,
        "display_name": display_name
    })
    assert signup_res.status_code == 200
    s_data = signup_res.json()
    assert "access_token" in s_data
    signup_token = s_data["access_token"]
    assert s_data["user"]["email"] == email.lower()
    assert s_data["user"]["display_name"] == display_name

    # 2. Duplicate signup error
    dup_res = client.post("/api/auth/signup", json={
        "email": email,
        "password": password
    })
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"].lower()

    # 3. Login success
    login_res = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_res.status_code == 200
    l_data = login_res.json()
    assert "access_token" in l_data
    login_token = l_data["access_token"]

    # Verify both signup and login tokens decode to the same user
    signup_decoded = decode_access_token(signup_token)
    login_decoded = decode_access_token(login_token)
    assert signup_decoded is not None and login_decoded is not None
    assert signup_decoded["email"] == login_decoded["email"] == email.lower()
    assert signup_decoded["sub"] == login_decoded["sub"]

    # 4. Login wrong password
    bad_login = client.post("/api/auth/login", json={
        "email": email,
        "password": "WrongPasswordHere"
    })
    assert bad_login.status_code == 401

    # 5. GET /api/auth/me authenticated (with both tokens)
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {signup_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["user"]["email"] == email.lower()

    me_login_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {login_token}"})
    assert me_login_res.status_code == 200
    assert me_login_res.json()["user"]["email"] == email.lower()

    # 6. GET /api/auth/me unauthenticated
    unauth_me = client.get("/api/auth/me")
    assert unauth_me.status_code == 401


def test_logged_in_upload_persists_to_db():
    unique_id = uuid.uuid4().hex[:8]
    email = f"persistence_user_{unique_id}@example.com"
    password = "PassWord123!"
    s_res = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert s_res.status_code == 200
    token = s_res.json()["access_token"]
    user_id = s_res.json()["user"]["id"]

    csv_data = "crime_type,suspect_age,property_loss_usd\nTheft,25,$1500\nBurglary,34,$3200\n"
    files = {"file": ("test_persisted.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}

    upload_res = client.post("/api/upload", files=files, headers={"Authorization": f"Bearer {token}"})
    assert upload_res.status_code == 201
    up_data = upload_res.json()
    file_id = up_data["file_id"]

    # Verify DB persistence
    db = SessionLocal()
    try:
        ds_rec = db.query(DatasetModel).filter(DatasetModel.id == file_id).first()
        assert ds_rec is not None
        assert ds_rec.user_id == user_id
        assert ds_rec.filename == "test_persisted.csv"
        assert ds_rec.row_count == 2
    finally:
        db.close()

    # Verify GET /api/user/datasets
    user_ds_res = client.get("/api/user/datasets", headers={"Authorization": f"Bearer {token}"})
    assert user_ds_res.status_code == 200
    ds_list = user_ds_res.json()["datasets"]
    assert any(d["file_id"] == file_id for d in ds_list)

    # Verify GET /api/user/datasets/{file_id}/resume
    resume_res = client.get(f"/api/user/datasets/{file_id}/resume", headers={"Authorization": f"Bearer {token}"})
    assert resume_res.status_code == 200
    r_data = resume_res.json()
    assert r_data["dataset"]["file_id"] == file_id
    assert "health" in r_data["dataset"]
    assert "dashboard_config" in r_data


def test_anonymous_upload_works_without_regression():
    csv_data = "item,quantity\nApple,10\nBanana,20\n"
    files = {"file": ("test_guest.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}

    # Upload WITHOUT Authorization header
    upload_res = client.post("/api/upload", files=files)
    assert upload_res.status_code == 201
    up_data = upload_res.json()
    assert "file_id" in up_data
    assert up_data["filename"] == "test_guest.csv"
    assert up_data["row_count"] == 2


def test_dashboard_and_ds_state_persistence_and_resume():
    unique_id = uuid.uuid4().hex[:8]
    email = f"state_user_{unique_id}@example.com"
    password = "PassWord123!"
    s_res = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert s_res.status_code == 200
    token = s_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    csv_data = "target_col,feature1,feature2\n1,10,20\n0,15,25\n1,12,22\n0,14,24\n1,11,21\n0,13,23\n1,10,20\n0,15,25\n1,12,22\n0,14,24\n"
    files = {"file": ("test_state.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}

    upload_res = client.post("/api/upload", files=files, headers=headers)
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    # 1. Save Dashboard config
    dash_items = [{"id": "kpi_test", "type": "kpi", "kpiData": {"kpi_name": "Test KPI"}}]
    save_dash_res = client.post(f"/api/user/datasets/{file_id}/dashboard", json={"items": dash_items}, headers=headers)
    assert save_dash_res.status_code == 200

    # 2. Save DS State
    ds_payload = {
        "target_column": "target_col",
        "features": ["feature1", "feature2"],
        "model_name": "Random Forest Classifier",
        "metrics": {"accuracy": 0.95}
    }
    save_ds_res = client.post(f"/api/user/datasets/{file_id}/ds-state", json=ds_payload, headers=headers)
    assert save_ds_res.status_code == 200

    # 3. Save Chat message
    chat_res = client.post(
        f"/api/dataset/{file_id}/chat",
        json={"message": "Hello dataset chat!"},
        headers=headers
    )
    assert chat_res.status_code == 200

    # 4. Resume dataset and check full associated state restoration
    resume_res = client.get(f"/api/user/datasets/{file_id}/resume", headers=headers)
    assert resume_res.status_code == 200
    r_data = resume_res.json()

    assert r_data["dataset"]["file_id"] == file_id
    assert r_data["dashboard_config"] == dash_items
    assert len(r_data["training_runs"]) >= 1
    latest_run = r_data["training_runs"][0]
    assert latest_run["target_column"] == "target_col"
    assert latest_run["features"] == ["feature1", "feature2"]
    assert latest_run["model_name"] == "Random Forest Classifier"
    assert len(r_data["chat_history"]) >= 2


def test_resumed_dataset_chat_after_session_eviction():
    from app.core.session import remove_dataset, _dataset_sessions
    unique_id = uuid.uuid4().hex[:8]
    user_a_email = f"evict_user_a_{unique_id}@example.com"
    user_b_email = f"evict_user_b_{unique_id}@example.com"
    password = "PassWord123!"

    # Signup User A and User B
    s_a = client.post("/api/auth/signup", json={"email": user_a_email, "password": password})
    token_a = s_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    s_b = client.post("/api/auth/signup", json={"email": user_b_email, "password": password})
    token_b = s_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A uploads dataset
    csv_data = "city,revenue,customers\nChicago,5000,120\nNew York,9000,210\nBoston,4000,85\n"
    files = {"file": ("test_evict.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}

    upload_res = client.post("/api/upload", files=files, headers=headers_a)
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    # Manually evict dataset from Python in-memory session (simulating server restart / session expiry)
    remove_dataset(file_id)
    assert file_id not in _dataset_sessions

    # 1. Resume dataset for User A -> auto-hydrates cleanly from disk & PostgreSQL
    resume_res = client.get(f"/api/user/datasets/{file_id}/resume", headers=headers_a)
    assert resume_res.status_code == 200
    assert resume_res.json()["dataset"]["file_id"] == file_id

    # 2. Data Chat for User A on the resumed dataset after eviction -> auto-hydrates and responds cleanly
    remove_dataset(file_id) # Evict again
    chat_res = client.post(
        f"/api/dataset/{file_id}/chat",
        json={"message": "Summarize this dataset and total revenue"},
        headers=headers_a
    )
    assert chat_res.status_code == 200
    c_data = chat_res.json()
    assert "response_text" in c_data and len(c_data["response_text"]) > 0
    assert "not found or expired" not in c_data["response_text"].lower()
    assert c_data["response_text"].strip() != "Analysis complete."
    assert "total revenue" in c_data["response_text"].lower() or "dataset" in c_data["response_text"].lower() or len(c_data["response_text"]) > 20

    # 3. Security Data Isolation: User B trying to access User A's file_id -> denied with 404 / 403
    user_b_chat = client.post(
        f"/api/dataset/{file_id}/chat",
        json={"message": "Show me User A's data"},
        headers=headers_b
    )
    assert user_b_chat.status_code in [403, 404]


def test_persistent_storage_blob_hydration_and_groq_fallback(monkeypatch):
    import os
    from app.core.session import remove_dataset, _dataset_sessions
    from app.core.storage import get_local_cache_path
    from app.ai.ollama_client import get_groq_model_candidates, chat_groq

    monkeypatch.delenv("GROQ_MODEL", raising=False)

    unique_id = uuid.uuid4().hex[:8]
    email = f"blob_user_{unique_id}@example.com"
    password = "PassWord123!"
    s_res = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert s_res.status_code == 200
    token = s_res.json()["access_token"]
    user_id = s_res.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    csv_data = "incident_id,crime_category,victims_count\nINC001,Theft,2\nINC002,Burglary,1\nINC003,Fraud,4\n"
    files = {"file": ("test_blob_persistence.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}

    upload_res = client.post("/api/upload", files=files, headers=headers)
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    # 1. Simulate Render filesystem wipe (clear in-memory cache AND delete local file on disk)
    remove_dataset(file_id)
    assert file_id not in _dataset_sessions
    local_disk_file = get_local_cache_path(file_id, "test_blob_persistence.csv", user_id)
    if os.path.exists(local_disk_file):
        os.remove(local_disk_file)
    assert os.path.exists(local_disk_file) is False

    # 2. Call overview after disk wipe -> Auto-hydrates 100% from PostgreSQL Blob table!
    overview_res = client.get(f"/api/dataset/{file_id}/overview", headers=headers)
    assert overview_res.status_code == 200
    o_data = overview_res.json()
    assert o_data["health"]["total_rows"] == 3
    assert o_data["health"]["total_columns"] == 3

    # 3. Verify Groq model candidates fallback chain contains only supported production models
    import app.ai.ollama_client as oc
    oc._cached_working_groq_model = None
    candidates = get_groq_model_candidates("openai/gpt-oss-120b")
    assert len(candidates) >= 2
    assert "openai/gpt-oss-120b" in candidates
    assert "openai/gpt-oss-20b" in candidates
    for deprecated in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama3-70b-8192", "mixtral-8x7b-32768"]:
        assert deprecated not in candidates


def test_access_token_expiration_and_refresh_success():
    from datetime import timedelta
    unique_id = uuid.uuid4().hex[:8]
    email = f"ref_user_{unique_id}@example.com"
    password = "PassWord123!"

    # 1. Signup user
    s_res = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert s_res.status_code == 200
    s_data = s_res.json()
    user_id = s_data["user"]["id"]
    refresh_token = s_data["refresh_token"]

    # 2. Simulate expired access token
    expired_token = create_access_token({"sub": user_id, "email": email}, expires_delta=timedelta(seconds=-10))

    # Calling /me with expired token fails with 401
    me_expired = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert me_expired.status_code == 401

    # 3. Refresh token exchange succeeds
    ref_res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 200
    ref_data = ref_res.json()
    assert "access_token" in ref_data
    assert "refresh_token" in ref_data
    new_access_token = ref_data["access_token"]

    # 4. Use new access token -> successfully authenticated!
    me_new = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_access_token}"})
    assert me_new.status_code == 200
    assert me_new.json()["user"]["email"] == email.lower()


def test_refresh_token_expired_or_revoked_forces_logout():
    unique_id = uuid.uuid4().hex[:8]
    email = f"revoke_user_{unique_id}@example.com"
    password = "PassWord123!"

    s_res = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert s_res.status_code == 200
    refresh_token = s_res.json()["refresh_token"]

    # 1. Logout user (revokes refresh token)
    logout_res = client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert logout_res.status_code == 200

    # 2. Refresh with revoked token fails with 401
    ref_revoked = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_revoked.status_code == 401

    # 3. Refresh with completely bogus token fails with 401
    ref_bogus = client.post("/api/auth/refresh", json={"refresh_token": "bogus_fake_token_12345"})
    assert ref_bogus.status_code == 401


def test_render_restart_preserves_auth_and_tokens():
    from app.core.session import clear_all_sessions
    unique_id = uuid.uuid4().hex[:8]
    email = f"restart_user_{unique_id}@example.com"
    password = "PassWord123!"

    s_res = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert s_res.status_code == 200
    refresh_token = s_res.json()["refresh_token"]

    # Clear Python in-memory session (simulates server process restart / Render worker recycle)
    clear_all_sessions()

    # User refresh token remains valid in PostgreSQL / SQLite DB
    ref_res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 200
    assert "access_token" in ref_res.json()


def test_session_eviction_does_not_destroy_persistent_data():
    from app.core.session import clear_all_sessions
    unique_id = uuid.uuid4().hex[:8]
    email = f"evict_data_user_{unique_id}@example.com"
    password = "PassWord123!"

    s_res = client.post("/api/auth/signup", json={"email": email, "password": password})
    token = s_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    csv_data = "a,b,c\n1,2,3\n4,5,6\n"
    files = {"file": ("test_evict_data.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}

    upload_res = client.post("/api/upload", files=files, headers=headers)
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    # Save dashboard config
    dash_items = [{"id": "kpi_1", "type": "kpi"}]
    client.post(f"/api/user/datasets/{file_id}/dashboard", json={"items": dash_items}, headers=headers)

    # Evict in-memory sessions
    clear_all_sessions()

    # Resume dataset -> all DB records (dataset, dashboard, training runs) remain fully intact!
    resume_res = client.get(f"/api/user/datasets/{file_id}/resume", headers=headers)
    assert resume_res.status_code == 200
    r_data = resume_res.json()
    assert r_data["dataset"]["file_id"] == file_id
    assert r_data["dashboard_config"] == dash_items


def test_resumed_dataset_usable_after_token_refresh():
    unique_id = uuid.uuid4().hex[:8]
    email = f"resume_refresh_{unique_id}@example.com"
    password = "PassWord123!"

    s_res = client.post("/api/auth/signup", json={"email": email, "password": password})
    token_1 = s_res.json()["access_token"]
    refresh_token = s_res.json()["refresh_token"]

    csv_data = "val1,val2\n10,20\n30,40\n"
    files = {"file": ("test_usable.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}

    upload_res = client.post("/api/upload", files=files, headers={"Authorization": f"Bearer {token_1}"})
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    # Refresh token to get new access token
    ref_res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 200
    token_2 = ref_res.json()["access_token"]

    # Resumed dataset using refreshed access token works 100%
    preview_res = client.get(f"/api/dataset/{file_id}/preview", headers={"Authorization": f"Bearer {token_2}"})
    assert preview_res.status_code == 200
    assert preview_res.json()["total_rows"] == 2



