"""Pytest fixtures: app dùng SQLite in-memory, tách biệt mỗi test."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import main
from app.db import get_session
from app.models import User, UserRole
from app.security import get_password_hash

PASSWORD = "password123"


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    main.app.dependency_overrides[get_session] = get_session_override
    client = TestClient(main.app)
    yield client
    main.app.dependency_overrides.clear()


def _make_user(session: Session, email: str, role: UserRole) -> User:
    user = User(
        email=email,
        full_name=email.split("@")[0],
        role=role,
        hashed_password=get_password_hash(PASSWORD),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def users(session: Session) -> dict[UserRole, User]:
    """Một user cho mỗi vai trò nghiệp vụ."""
    return {
        role: _make_user(session, f"{role.value}@test.com", role)
        for role in UserRole
    }


def auth_header(client: TestClient, email: str) -> dict:
    resp = client.post("/token", data={"username": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
