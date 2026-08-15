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
    token = s_data["access_token"]
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
    assert l_data["access_token"] == token

    # 4. Login wrong password
    bad_login = client.post("/api/auth/login", json={
        "email": email,
        "password": "WrongPasswordHere"
    })
    assert bad_login.status_code == 401

    # 5. GET /api/auth/me authenticated
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["user"]["email"] == email.lower()

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
