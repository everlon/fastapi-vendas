from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db

from app.main import app

test_username = "everlon"
test_password = "secret"

# Configuração do banco de dados de teste.
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Substituir a dependência get_db com a versão de teste
app.dependency_overrides[get_db] = override_get_db

Base.metadata.create_all(bind=engine)

client = TestClient(app)

version_prefix = "/api/v1/auth"


@pytest.fixture
def get_access_token():
    response = client.post(f"{version_prefix}/token", data={"username": test_username, "password": test_password})
    assert response.status_code == HTTPStatus.OK
    access_token = response.json().get("access_token")
    assert access_token is not None
    return access_token

def test_login():
    response = client.post(f"{version_prefix}/token", data={"username": test_username, "password": test_password})
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_get_current_user(get_access_token):
    headers = {"Authorization": f"Bearer {get_access_token}"}
    response = client.get(f"{version_prefix}/users/me", headers=headers)
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["username"] == test_username
