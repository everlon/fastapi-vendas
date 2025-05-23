from http import HTTPStatus
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from typing import Generator

from database import Base, get_db

from app.main import app

# Importar roteadores diretamente (se necessário para o ambiente de teste local)
from src.routers.auth_controller import router as auth_router
from src.routers.product_controller import router as product_router
from src.routers.user_controller import router as user_router

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
test_app.include_router(product_router, prefix="/api/v1/products")
test_app.include_router(user_router, prefix="/api/v1/users")

# Sobrescrever a dependência get_db com a versão assíncrona de teste
test_app.dependency_overrides[get_db] = override_get_db

client = TestClient(test_app)

version_prefix = "/api/v1/products"

# Função auxiliar para obter token de login (assíncrona)
async def login_token():
    # Obter o token para o usuário 'everlon'
    user_data = {"username": "everlon", "password": "secret"}
    # Removendo a criação do usuário daqui, pois deve ser feita no teste.
    # create_user_response = client.post("/api/v1/users/", json=user_data)
    # assert create_user_response.status_code == 201

    # Obter o token
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": user_data["username"],
            "password": user_data["password"],
        }
    )
    assert response.status_code == 200
    token_data = response.json()
    return {"Authorization": f"Bearer {token_data['access_token']}"}

async def test_create_product():
    # Limpa o DB e cria tabelas antes de cada teste que cria dados
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Criar o usuário de teste para autenticação
    user_data = {"username": "everlon", "password": "secret"}
    create_user_response = client.post("/api/v1/users/", json=user_data)
    assert create_user_response.status_code == 201

    product_data = {
        "name": "Produto de Teste",
        "description": "Descrição do Produto teste",
        "price": 99.99,
        "status": "em estoque",
        "stock_quantity": 10,
        "barcode": "1234567890124",
        "section": "Eletrônicos",
        "expiration_date": "2030-12-31T00:00:00",
        "images": ["http://example.com/img1.jpg", "http://example.com/img2.jpg"]
    }

    response = client.post(f"{version_prefix}/", json=product_data, headers=await login_token())
    assert response.status_code == 201
    created_product = response.json()
    assert created_product["name"] == product_data["name"]
    assert created_product["price"] == product_data["price"]
    # Outras asserções de criação podem ser adicionadas

async def test_list_products():
    # Limpa o DB e cria tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Criar o usuário de teste para autenticação
    user_data = {"username": "everlon", "password": "secret"}
    create_user_response = client.post("/api/v1/users/", json=user_data)
    assert create_user_response.status_code == 201

    # Criar um produto para garantir que a lista não esteja vazia
    client.post(f"{version_prefix}/", json={
        "name": "Produto Teste Listagem",
        "description": "Descrição do produto",
        "price": 99.99,
        "status": "em estoque",
        "stock_quantity": 20,
        "barcode": "1234567890130", # Barcode único
        "section": "Eletrônicos",
        "expiration_date": "2030-12-31T00:00:00",
        "images": []
    }, headers=await login_token())

    response = client.get(f"{version_prefix}/", headers=await login_token())
    assert response.status_code == 200
    data = response.json()
    # Asserções sobre a lista de produtos e paginação (adaptar conforme o schema de PaginatedProductResponse)
    assert isinstance(data["products"], list)
    assert data["total"] > 0 # Deve haver pelo menos o produto criado

async def test_get_product_by_id():
    # Limpa o DB e cria tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Criar o usuário de teste para autenticação
    user_data = {"username": "everlon", "password": "secret"}
    create_user_response = client.post("/api/v1/users/", json=user_data)
    assert create_user_response.status_code == 201

    # Criar um produto para buscar
    product_data = {
        "name": "Produto para Buscar",
        "description": "Descrição",
        "price": 10.0,
        "status": "em estoque",
        "stock_quantity": 10,
        "barcode": "1234567890131", # Barcode único
        "section": "Eletrônicos",
        "expiration_date": "2030-12-31T00:00:00",
        "images": []
    }
    create_response = client.post(f"{version_prefix}/", json=product_data, headers=await login_token())
    assert create_response.status_code == 201
    created_product_id = create_response.json()["id"]

    # Buscar o produto pelo ID
    response = client.get(f"{version_prefix}/{created_product_id}", headers=await login_token())
    assert response.status_code == 200
    product_info = response.json()["product"]
    assert product_info["id"] == created_product_id
    assert product_info["name"] == product_data["name"]
    # Verificar outros campos conforme necessário

async def test_create_product_barcode_unique():
    # Limpa o DB e cria tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Criar o usuário de teste para autenticação
    user_data = {"username": "everlon", "password": "secret"}
    create_user_response = client.post("/api/v1/users/", json=user_data)
    assert create_user_response.status_code == 201

    # Criar o primeiro produto
    product_data = {
        "name": "Produto 1",
        "description": "Primeiro produto",
        "price": 10.0,
        "status": "em estoque",
        "stock_quantity": 5,
        "barcode": "9999999999999",
        "section": "Eletrônicos",
        "expiration_date": "2030-12-31T00:00:00",
        "images": []
    }
    response1 = client.post(f"{version_prefix}/", json=product_data, headers=await login_token())
    assert response1.status_code == 201

    # Tentar criar outro produto com o mesmo código de barras
    product_data_duplicate_barcode = {
        "name": "Produto 2",
        "description": "Segundo produto com mesmo barcode",
        "price": 20.0,
        "status": "em falta",
        "stock_quantity": 2,
        "barcode": "9999999999999", # Mesmo barcode
        "section": "Livros",
        "expiration_date": "2025-12-31T00:00:00",
        "images": []
    }
    response2 = client.post(f"{version_prefix}/", json=product_data_duplicate_barcode, headers=await login_token())
    assert response2.status_code == 400
    assert response2.json() == {"detail": "Código de barras já cadastrado."}

async def test_update_product():
    # Limpa o DB e cria tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Criar o usuário de teste para autenticação
    user_data = {"username": "everlon", "password": "secret"}
    create_user_response = client.post("/api/v1/users/", json=user_data)
    assert create_user_response.status_code == 201

    # Criar um produto para atualizar
    product_data = {
        "name": "Produto Teste Atualização",
        "description": "Descrição do produto para atualização",
        "price": 49.99,
        "status": "em estoque",
        "stock_quantity": 50,
        "barcode": "1234567890126", # Barcode único
        "section": "Eletrônicos",
        "expiration_date": "2030-12-31T00:00:00",
        "images": []
    }
    create_response = client.post(f"{version_prefix}/", json=product_data, headers=await login_token())
    assert create_response.status_code == 201
    created_product_id = create_response.json()["id"]

    # Dados para atualização
    update_data = {
        "name": "Produto Atualizado",
        "price": 55.55,
        "status": "em reposição",
        "stock_quantity": 60
    }
    update_response = client.put(f"{version_prefix}/{created_product_id}", json=update_data, headers=await login_token())
    assert update_response.status_code == 200
    updated_product = update_response.json()

    assert updated_product["id"] == created_product_id
    assert updated_product["name"] == update_data["name"]
    assert updated_product["price"] == update_data["price"]
    assert updated_product["status"] == update_data["status"]
    assert updated_product["stock_quantity"] == update_data["stock_quantity"]
    # Verificar outros campos para garantir que os não atualizados permaneçam
    assert updated_product["barcode"] == product_data["barcode"]
    assert updated_product["section"] == product_data["section"]

async def test_delete_product():
    # Limpa o DB e cria tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Criar o usuário de teste para autenticação
    user_data = {"username": "everlon", "password": "secret"}
    create_user_response = client.post("/api/v1/users/", json=user_data)
    assert create_user_response.status_code == 201

    # Criar um produto para deletar
    product_data = {
        "name": "Produto Teste Deleção",
        "description": "Descrição do produto para deleção",
        "price": 29.99,
        "status": "em estoque",
        "stock_quantity": 10,
        "barcode": "1234567890127", # Barcode único
        "section": "Eletrônicos",
        "expiration_date": "2030-12-31T00:00:00",
        "images": []
    }
    create_response = client.post(f"{version_prefix}/", json=product_data, headers=await login_token())
    assert create_response.status_code == 201
    created_product_id = create_response.json()["id"]

    # Deletar o produto
    delete_response = client.delete(f"{version_prefix}/{created_product_id}", headers=await login_token())
    assert delete_response.status_code == 204

    # Tentar buscar o produto deletado (deve retornar 404)
    get_response = client.get(f"{version_prefix}/{created_product_id}", headers=await login_token())
    assert get_response.status_code == 404
