from http import HTTPStatus
import pytest
# from fastapi.testclient import TestClient # Remover importação síncrona
from fastapi import FastAPI

# Importações para ambiente de teste assíncrono
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database import Base, get_db

# Importar httpx para cliente assíncrono
from httpx import AsyncClient
from sqlalchemy import delete # Importar delete para limpeza de DB

from app.main import app # Usar a instância principal do app, já configurada

# Importar modelos e schemas necessários para criar dados de teste
from src.schemas.user import UserCreate
from src.schemas.client import ClientCreate, ClientUpdate
from src.models.user import User as UserModel # Importar modelo de usuário
from src.models.client import Client as ClientModel # Importar modelo de cliente
from src.services.user_service import create_user # Importar serviço de usuário

# Configuração do banco de dados de teste (SQLite em memória - ASSÍNCRONO)
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
testing_engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=testing_engine, class_=AsyncSession
)

# Sobrescrever get_db para usar o banco de testes
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

# Criar as tabelas no banco de testes antes de rodar os testes
import pytest
@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    async with testing_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with testing_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Usar httpx.AsyncClient
@pytest.fixture(scope="session")
async def client():
    # Usar a instância 'app' global para o cliente de teste
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

version_prefix = "/api/v1/clients"

# Fixture assíncrona para criar um usuário de teste e retornar o objeto User
@pytest.fixture
async def authenticated_user(client: AsyncClient):
    async with TestingSessionLocal() as db:
        await db.execute(delete(ClientModel))
        await db.execute(delete(UserModel))
        await db.commit()
        user_data = UserCreate(
            username="testclientuser",
            email="testclient@example.com",
            password="testpassword",
            is_admin=True  # Definir como admin
        )
        user = await create_user(db=db, user=user_data)
        await db.commit()
        await db.refresh(user)
        return user

# Fixture assíncrona para obter o token de autenticação
@pytest.fixture
async def authenticated_user_token_str(client: AsyncClient, authenticated_user: UserModel): # Depende de authenticated_user (objeto User)
    token_response = await client.post("/api/v1/auth/token", data={
        "username": authenticated_user.username, # Usar username do objeto User
        "password": "testpassword" # Senha hardcoded para o usuário de teste
    })
    assert token_response.status_code == 200
    token_data = token_response.json()
    return token_data["access_token"]

# Atualizar testes existentes para usar httpx.AsyncClient e fixtures assíncronas

# Remover a limpeza de DB dentro de cada teste, usar a fixture authenticated_user que limpa antes de cada uso
# Remover a criação de usuário dentro de cada teste, usar a fixture authenticated_user
# Remover a obtenção de token dentro de cada teste, usar a fixture authenticated_user_token_str
# Usar client: AsyncClient em vez de client: TestClient

@pytest.mark.asyncio
async def test_create_client(client: AsyncClient, authenticated_user_token_str: str):
    client_data = {
        "name": "Cliente Teste",
        "email": "cliente@teste.com",
        "phone": "11999999999",
        "cpf": "52998224725",
        "address": {
            "street": "Rua Teste",
            "number": "123",
            "complement": "Apto 45",
            "neighborhood": "Centro",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234567"
        }
    }

    response = await client.post(
        f"{version_prefix}/",
        json=client_data,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.CREATED
    created_client = response.json()
    
    assert created_client["name"] == client_data["name"]
    assert created_client["email"] == client_data["email"]
    assert created_client["phone"] == client_data["phone"]
    assert created_client["cpf"] == client_data["cpf"]
    assert created_client["address"]["street"] == client_data["address"]["street"]
    assert created_client["address"]["number"] == client_data["address"]["number"]
    assert created_client["address"]["complement"] == client_data["address"]["complement"]
    assert created_client["address"]["neighborhood"] == client_data["address"]["neighborhood"]
    assert created_client["address"]["city"] == client_data["address"]["city"]
    assert created_client["address"]["state"] == client_data["address"]["state"]
    assert created_client["address"]["zip_code"] == client_data["address"]["zip_code"]

# Novo teste para criar cliente com email duplicado
@pytest.mark.asyncio
async def test_create_client_duplicate_email(client: AsyncClient, authenticated_user_token_str: str):
    # Criar primeiro cliente
    client_data1 = {
        "name": "Cliente 1",
        "email": "cliente1@teste.com",
        "phone": "11999999999",
        "cpf": "52998224725",
        "address": {
            "street": "Rua Teste 1",
            "number": "123",
            "complement": "Apto 1",
            "neighborhood": "Centro",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234567"
        }
    }

    response1 = await client.post(
        f"{version_prefix}/",
        json=client_data1,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response1.status_code == HTTPStatus.CREATED

    # Tentar criar segundo cliente com mesmo email
    client_data2 = {
        "name": "Cliente 2",
        "email": "cliente1@teste.com",  # Mesmo email
        "phone": "11988888888",
        "cpf": "12345678909",
        "address": {
            "street": "Rua Teste 2",
            "number": "456",
            "complement": "Apto 2",
            "neighborhood": "Centro",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234567"
        }
    }

    response2 = await client.post(
        f"{version_prefix}/",
        json=client_data2,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response2.status_code == HTTPStatus.BAD_REQUEST
    assert "Email já cadastrado" in response2.json()["detail"]

# Novo teste para criar cliente com CPF duplicado
@pytest.mark.asyncio
async def test_create_client_duplicate_cpf(client: AsyncClient, authenticated_user_token_str: str):
    # Criar primeiro cliente
    client_data1 = {
        "name": "Cliente 1",
        "email": "cliente1@teste.com",
        "phone": "11999999999",
        "cpf": "52998224725",
        "address": {
            "street": "Rua Teste 1",
            "number": "123",
            "complement": "Apto 1",
            "neighborhood": "Centro",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234567"
        }
    }

    response1 = await client.post(
        f"{version_prefix}/",
        json=client_data1,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response1.status_code == HTTPStatus.CREATED

    # Tentar criar segundo cliente com mesmo CPF
    client_data2 = {
        "name": "Cliente 2",
        "email": "cliente2@teste.com",
        "phone": "11988888888",
        "cpf": "52998224725",  # Mesmo CPF
        "address": {
            "street": "Rua Teste 2",
            "number": "456",
            "complement": "Apto 2",
            "neighborhood": "Centro",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234567"
        }
    }

    response2 = await client.post(
        f"{version_prefix}/",
        json=client_data2,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response2.status_code == HTTPStatus.BAD_REQUEST
    assert "CPF já cadastrado" in response2.json()["detail"]

@pytest.mark.asyncio
async def test_list_clients(client: AsyncClient, authenticated_user_token_str: str):
    # Criar alguns clientes para testar a listagem
    clients_data = [
        {
            "name": "Cliente A",
            "email": "cliente.a@teste.com",
            "phone": "11999999999",
            "cpf": "52998224725",
            "address": {
                "street": "Rua A",
                "number": "123",
                "complement": "Apto 1",
                "neighborhood": "Centro",
                "city": "São Paulo",
                "state": "SP",
                "zip_code": "01234567"
            }
        },
        {
            "name": "Cliente B",
            "email": "cliente.b@teste.com",
            "phone": "11988888888",
            "cpf": "12345678909",
            "address": {
                "street": "Rua B",
                "number": "456",
                "complement": "Apto 2",
                "neighborhood": "Centro",
                "city": "São Paulo",
                "state": "SP",
                "zip_code": "01234567"
            }
        }
    ]

    for client_data in clients_data:
        response = await client.post(
            f"{version_prefix}/",
            json=client_data,
            headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
        )
        assert response.status_code == HTTPStatus.CREATED

    # Testar listagem básica
    response = await client.get(
        f"{version_prefix}/",
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "clients" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert len(data["clients"]) >= 2

    # Testar busca por nome
    response = await client.get(
        f"{version_prefix}/?search=Cliente A",
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert all("Cliente A" in c["name"] for c in data["clients"])

    # Testar busca por email
    response = await client.get(
        f"{version_prefix}/?search=cliente.a@teste.com",
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert all("cliente.a@teste.com" in c["email"] for c in data["clients"])

@pytest.mark.asyncio
async def test_get_client_by_id(client: AsyncClient, authenticated_user_token_str: str):
    # Criar um cliente para buscar
    client_data = {
        "name": "Cliente para Buscar",
        "email": "cliente.buscar@teste.com",
        "phone": "11999999999",
        "cpf": "52998224725",
        "address": {
            "street": "Rua Busca",
            "number": "123",
            "complement": "Apto 45",
            "neighborhood": "Centro",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234567"
        }
    }

    create_response = await client.post(
        f"{version_prefix}/",
        json=client_data,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert create_response.status_code == HTTPStatus.CREATED
    created_client = create_response.json()
    client_id = created_client["id"]

    # Buscar o cliente
    response = await client.get(
        f"{version_prefix}/{client_id}",
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "client" in data
    client = data["client"]
    
    assert client["id"] == client_id
    assert client["name"] == client_data["name"]
    assert client["email"] == client_data["email"]
    assert client["phone"] == client_data["phone"]
    assert client["cpf"] == client_data["cpf"]
    assert client["address"]["street"] == client_data["address"]["street"]
    assert client["address"]["number"] == client_data["address"]["number"]
    assert client["address"]["complement"] == client_data["address"]["complement"]
    assert client["address"]["neighborhood"] == client_data["address"]["neighborhood"]
    assert client["address"]["city"] == client_data["address"]["city"]
    assert client["address"]["state"] == client_data["address"]["state"]
    assert client["address"]["zip_code"] == client_data["address"]["zip_code"]

@pytest.mark.asyncio
async def test_get_client_not_found(client: AsyncClient, authenticated_user_token_str: str):
    response = await client.get(
        f"{version_prefix}/99999",
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "Cliente não encontrado" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_client(client: AsyncClient, authenticated_user_token_str: str):
    # Criar um cliente para atualizar
    client_data = {
        "name": "Cliente para Atualizar",
        "email": "cliente.atualizar@teste.com",
        "phone": "11999999999",
        "cpf": "52998224725",
        "address": {
            "street": "Rua Original",
            "number": "123",
            "complement": "Apto 1",
            "neighborhood": "Centro",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234567"
        }
    }

    create_response = await client.post(
        f"{version_prefix}/",
        json=client_data,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert create_response.status_code == HTTPStatus.CREATED
    created_client = create_response.json()
    client_id = created_client["id"]

    # Atualizar o cliente
    update_data = {
        "name": "Cliente Atualizado",
        "phone": "11988888888",
        "address": {
            "street": "Rua Nova",
            "number": "456",
            "complement": "Apto 2",
            "neighborhood": "Centro",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234567"
        }
    }

    response = await client.put(
        f"{version_prefix}/{client_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.OK
    updated_client = response.json()

    assert updated_client["id"] == client_id
    assert updated_client["name"] == update_data["name"]
    assert updated_client["phone"] == update_data["phone"]
    assert updated_client["email"] == client_data["email"]  # Não deve ter mudado
    assert updated_client["cpf"] == client_data["cpf"]  # Não deve ter mudado
    assert updated_client["address"]["street"] == update_data["address"]["street"]
    assert updated_client["address"]["number"] == update_data["address"]["number"]
    assert updated_client["address"]["complement"] == update_data["address"]["complement"]
    assert updated_client["address"]["neighborhood"] == update_data["address"]["neighborhood"]
    assert updated_client["address"]["city"] == update_data["address"]["city"]
    assert updated_client["address"]["state"] == update_data["address"]["state"]
    assert updated_client["address"]["zip_code"] == update_data["address"]["zip_code"]

@pytest.mark.asyncio
async def test_update_client_not_found(client: AsyncClient, authenticated_user_token_str: str):
    update_data = {
        "name": "Cliente Atualizado",
        "phone": "11988888888"
    }

    response = await client.put(
        f"{version_prefix}/99999",
        json=update_data,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "Cliente não encontrado" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_client(client: AsyncClient, authenticated_user_token_str: str):
    # Criar um cliente para deletar
    client_data = {
        "name": "Cliente para Deletar",
        "email": "cliente.deletar@teste.com",
        "phone": "11999999999",
        "cpf": "52998224725",
        "address": {
            "street": "Rua Deletar",
            "number": "123",
            "complement": "Apto 1",
            "neighborhood": "Centro",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234567"
        }
    }

    create_response = await client.post(
        f"{version_prefix}/",
        json=client_data,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert create_response.status_code == HTTPStatus.CREATED
    created_client = create_response.json()
    client_id = created_client["id"]

    # Deletar o cliente
    response = await client.delete(
        f"{version_prefix}/{client_id}",
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.NO_CONTENT

    # Verificar se o cliente foi realmente deletado
    get_response = await client.get(
        f"{version_prefix}/{client_id}",
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert get_response.status_code == HTTPStatus.NOT_FOUND

@pytest.mark.asyncio
async def test_delete_client_not_found(client: AsyncClient, authenticated_user_token_str: str):
    response = await client.delete(
        f"{version_prefix}/99999",
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "Cliente não encontrado" in response.json()["detail"] 