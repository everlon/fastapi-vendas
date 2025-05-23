from http import HTTPStatus
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Importações para ambiente de teste assíncrono
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database import Base, get_db

from app.main import app

# Importar roteadores diretamente para o ambiente de teste local
from src.routers.auth_controller import router as auth_router
from src.routers.client_controller import router as client_router
from src.routers.user_controller import router as user_router # Importar router de usuário

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
test_app.include_router(client_router, prefix="/api/v1/clients")
test_app.include_router(user_router, prefix="/api/v1/users") # Incluir router de usuário

# Sobrescrever a dependência get_db com a versão assíncrona de teste
test_app.dependency_overrides[get_db] = override_get_db

client = TestClient(test_app)

version_prefix = "/api/v1/clients"

# Função auxiliar para obter token de login (assíncrona)
async def login_token():
    # Efetuar login para obter Token (usando um usuário de teste existente)
    # A criação do usuário de teste deve ser feita no teste individualmente.
    response = client.post("/api/v1/auth/token", data={"username": "everlon", "password": "secret"})
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    return {"Authorization": f"Bearer {data['access_token']}"}


async def test_create_client():
    # Limpa o DB e cria tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Criar o usuário de teste para autenticação
    user_data = {"username": "everlon", "password": "secret"}
    create_user_response = client.post("/api/v1/users/", json=user_data)
    assert create_user_response.status_code == HTTPStatus.CREATED

    client_data = {
        "name": "Cliente Teste 1",
        "email": "cliente1@test.com",
        "phone": "11987654321",
        "address": "Rua Teste, 123"
    }
    response = client.post(f"{version_prefix}/", json=client_data, headers=await login_token())
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["email"] == client_data["email"]


async def test_list_clients():
    # Limpa o DB e cria tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Criar o usuário de teste para autenticação
    user_data = {"username": "everlon", "password": "secret"}
    create_user_response = client.post("/api/v1/users/", json=user_data)
    assert create_user_response.status_code == HTTPStatus.CREATED

    # Criar alguns clientes para a lista
    client.post(f"{version_prefix}/", json={"name": "Cliente Teste List 1", "email": "list1@test.com"}, headers=await login_token())
    client.post(f"{version_prefix}/", json={"name": "Cliente Teste List 2", "email": "list2@test.com"}, headers=await login_token())

    response = client.get(f"{version_prefix}/", headers=await login_token())
    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json(), dict)
    assert "clients" in response.json()
    assert response.json()["total"] >= 2 # Deve haver pelo menos os 2 que criamos + outros se houver


async def test_get_client_by_id():
    # Limpa o DB e cria tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Criar o usuário de teste para autenticação
    user_data = {"username": "everlon", "password": "secret"}
    create_user_response = client.post("/api/v1/users/", json=user_data)
    assert create_user_response.status_code == HTTPStatus.CREATED

    # Criar um cliente para buscar
    create_response = client.post(f"{version_prefix}/", json={"name": "Cliente Teste Get", "email": "get@test.com"}, headers=await login_token())
    assert create_response.status_code == HTTPStatus.CREATED
    client_id = create_response.json()["id"]

    response = client.get(f"{version_prefix}/{client_id}", headers=await login_token())
    assert response.status_code == HTTPStatus.OK
    assert response.json()["email"] == "get@test.com"


async def test_update_client():
    # Limpa o DB e cria tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Criar o usuário de teste para autenticação
    user_data = {"username": "everlon", "password": "secret"}
    create_user_response = client.post("/api/v1/users/", json=user_data)
    assert create_user_response.status_code == HTTPStatus.CREATED

    # Criar um cliente para atualizar
    create_response = client.post(f"{version_prefix}/", json={"name": "Cliente Teste Update", "email": "update@test.com", "phone": "11111111111"}, headers=await login_token())
    assert create_response.status_code == HTTPStatus.CREATED
    client_id = create_response.json()["id"]

    update_data = {
        "phone": "22222222222",
        "address": "Novo Endereço, 456"
    }
    response = client.put(f"{version_prefix}/{client_id}", json=update_data, headers=await login_token())
    assert response.status_code == HTTPStatus.OK
    assert response.json()["phone"] == "22222222222"
    assert response.json()["address"] == "Novo Endereço, 456"


async def test_delete_client():
    # Limpa o DB e cria tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Criar o usuário de teste para autenticação
    user_data = {"username": "everlon", "password": "secret"}
    create_user_response = client.post("/api/v1/users/", json=user_data)
    assert create_user_response.status_code == HTTPStatus.CREATED

    # Criar um cliente para deletar
    create_response = client.post(f"{version_prefix}/", json={"name": "Cliente Teste Delete", "email": "delete@test.com"}, headers=await login_token())
    assert create_response.status_code == HTTPStatus.CREATED
    client_id = create_response.json()["id"]

    response = client.delete(f"{version_prefix}/{client_id}", headers=await login_token())
    assert response.status_code == HTTPStatus.NO_CONTENT # Espera 204 No Content para deleção bem sucedida

    # Verificar se o cliente foi realmente deletado (busca deve retornar 404)
    get_response = client.get(f"{version_prefix}/{client_id}", headers=await login_token())
    assert get_response.status_code == HTTPStatus.NOT_FOUND 