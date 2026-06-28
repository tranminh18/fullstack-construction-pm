"""Test auth: đăng ký, đăng nhập, chặn truy cập khi thiếu/ sai token."""
from conftest import PASSWORD, auth_header


def test_register_and_login(client, session):
    resp = client.post(
        "/register",
        json={"email": "new@test.com", "full_name": "New User", "password": PASSWORD},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "new@test.com"
    # vai trò mặc định là worker
    assert resp.json()["role"] == "worker"

    header = auth_header(client, "new@test.com")
    assert "Authorization" in header


def test_duplicate_email_rejected(client):
    payload = {"email": "dup@test.com", "full_name": "Dup", "password": PASSWORD}
    assert client.post("/register", json=payload).status_code == 200
    assert client.post("/register", json=payload).status_code == 400


def test_protected_endpoint_requires_token(client):
    assert client.get("/projects/").status_code == 401


def test_wrong_password_rejected(client):
    client.post(
        "/register",
        json={"email": "x@test.com", "full_name": "X", "password": PASSWORD},
    )
    resp = client.post("/token", data={"username": "x@test.com", "password": "wrong"})
    assert resp.status_code == 401


def test_refresh_token_issues_new_access_token(client):
    client.post(
        "/register",
        json={"email": "r@test.com", "full_name": "R", "password": PASSWORD},
    )
    tokens = client.post("/token", data={"username": "r@test.com", "password": PASSWORD}).json()
    resp = client.post("/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    new_access = resp.json()["access_token"]
    # access token mới phải dùng được
    me = client.get("/projects/", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200


def test_access_token_rejected_at_refresh_endpoint(client):
    client.post(
        "/register",
        json={"email": "a@test.com", "full_name": "A", "password": PASSWORD},
    )
    tokens = client.post("/token", data={"username": "a@test.com", "password": PASSWORD}).json()
    # Dùng access token ở /refresh phải bị từ chối (sai loại token)
    resp = client.post("/refresh", json={"refresh_token": tokens["access_token"]})
    assert resp.status_code == 401


def test_refresh_token_rejected_at_protected_endpoint(client):
    client.post(
        "/register",
        json={"email": "b@test.com", "full_name": "B", "password": PASSWORD},
    )
    tokens = client.post("/token", data={"username": "b@test.com", "password": PASSWORD}).json()
    # Refresh token không được dùng để truy cập tài nguyên
    resp = client.get("/projects/", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert resp.status_code == 401


def test_me_returns_current_user(client):
    client.post(
        "/register",
        json={"email": "me@test.com", "full_name": "Me User", "password": PASSWORD},
    )
    header = auth_header(client, "me@test.com")
    resp = client.get("/me", headers=header)
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@test.com"
    assert resp.json()["full_name"] == "Me User"
