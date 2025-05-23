from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database import Base, get_db

from app.main import app
from src.routers.auth_controller import router as auth_router
from src.routers.user_controller import router as user_router

test_username = "everlon"
test_password = "secret"

# Configuração do banco de dados de teste (SQLite em memória - ASSÍNCRONO)
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sobrescrever get_db para os testes assíncronos
async def override_get_db():
    async with TestingSessionLocal() as db:
        yield db

# Criar nova instância do FastAPI para os testes (incluindo roteadores)
test_app = FastAPI()
test_app.include_router(auth_router, prefix="/api/v1/auth")
test_app.include_router(user_router, prefix="/api/v1/users")

# Sobrescrever a dependência get_db com a versão assíncrona de teste
test_app.dependency_overrides[get_db] = override_get_db

client = TestClient(test_app)

version_prefix = "/api/v1/auth"


@pytest.fixture
async def get_access_token():
    # Limpa o DB e cria tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Criar o usuário de teste para autenticação
    user_data = {"username": test_username, "password": test_password}
    create_user_response = client.post("/api/v1/users/", json=user_data)
    assert create_user_response.status_code == HTTPStatus.CREATED

    # Efetuar login para obter Token
    response = client.post(f"{version_prefix}/token", data={"username": test_username, "password": test_password})
    assert response.status_code == HTTPStatus.OK
    access_token = response.json().get("access_token")
    assert access_token is not None
    return access_token


async def test_login():
    # Limpa o DB e cria tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Criar o usuário de teste para autenticação
    user_data = {"username": test_username, "password": test_password}
    create_user_response = client.post("/api/v1/users/", json=user_data)
    assert create_user_response.status_code == HTTPStatus.CREATED

    response = client.post(f"{version_prefix}/token", data={"username": test_username, "password": test_password})
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_get_current_user(get_access_token):
    headers = {"Authorization": f"Bearer {get_access_token}"}
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["username"] == test_username
