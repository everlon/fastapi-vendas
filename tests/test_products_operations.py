from http import HTTPStatus
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from typing import Generator
from httpx import AsyncClient
from datetime import datetime, timedelta
from sqlalchemy import delete

from database import Base, get_db

from app.main import app

# Importar roteadores diretamente (se necessário para o ambiente de teste local)
from src.routers.auth_controller import router as auth_router
from src.routers.product_controller import router as product_router
from src.routers.user_controller import router as user_router

from src.models.product import Product
from src.schemas.product import ProductStatusEnum
from src.routers import product_controller, auth_controller, user_controller
from src.schemas.user import UserCreate
from src.services.user_service import create_user
from src.models.user import User
from src.models.order import Order, OrderItem
from src.models.client import Client

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

# Criar as tabelas no banco de testes antes de rodar os testes
@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

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

@pytest.fixture(scope="session")
async def client():
    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def authenticated_user_token_str(client: AsyncClient):
    # Criar usuário de teste
    async with TestingSessionLocal() as db:
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="testpassword",
            is_admin=True  # Definir como admin
        )
        user = await create_user(db=db, user=user_data)
        await db.commit()
        await db.refresh(user)

    # Obter token
    token_response = await client.post("/api/v1/auth/token", data={"username": "testuser", "password": "testpassword"})
    assert token_response.status_code == 200
    token_data = token_response.json()
    return token_data["access_token"]

@pytest.fixture(autouse=True)
async def cleanup_database():
    # Limpar o banco de dados antes de cada teste
    async with TestingSessionLocal() as db:
        await db.execute(delete(OrderItem))
        await db.execute(delete(Order))
        await db.execute(delete(Product))
        await db.execute(delete(Client))
        await db.execute(delete(User))
        await db.commit()
    yield

@pytest.mark.asyncio
async def test_create_product(client: AsyncClient, authenticated_user_token_str: str):
    product_data = {
        "name": "Produto Teste",
        "description": "Descrição do produto teste",
        "price": 100.0,
        "status": ProductStatusEnum.in_stock,
        "stock_quantity": 50,
        "barcode": "1234567890123",
        "section": "Eletrônicos",
        "expiration_date": (datetime.now() + timedelta(days=365)).isoformat(),
        "images": ["https://example.com/img1.jpg"]
    }

    response = await client.post(
        f"{version_prefix}/",
        json=product_data,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.CREATED
    created_product = response.json()
    
    assert created_product["name"] == product_data["name"]
    assert created_product["description"] == product_data["description"]
    assert created_product["price"] == product_data["price"]
    assert created_product["status"] == ProductStatusEnum.in_stock
    assert created_product["stock_quantity"] == product_data["stock_quantity"]
    assert created_product["barcode"] == product_data["barcode"]
    assert created_product["section"] == product_data["section"]
    assert created_product["images"] == product_data["images"]

@pytest.mark.asyncio
async def test_create_product_duplicate_barcode(client: AsyncClient, authenticated_user_token_str: str):
    # Criar primeiro produto
    product_data1 = {
        "name": "Produto 1",
        "description": "Descrição 1",
        "price": 100.0,
        "status": ProductStatusEnum.in_stock,
        "stock_quantity": 50,
        "barcode": "1234567890124",
        "section": "Eletrônicos",
        "expiration_date": (datetime.now() + timedelta(days=365)).isoformat(),
        "images": []
    }

    response1 = await client.post(
        f"{version_prefix}/",
        json=product_data1,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response1.status_code == HTTPStatus.CREATED

    # Tentar criar segundo produto com mesmo barcode
    product_data2 = {
        "name": "Produto 2",
        "description": "Descrição 2",
        "price": 200.0,
        "status": ProductStatusEnum.in_stock,
        "stock_quantity": 30,
        "barcode": "1234567890124",  # Mesmo barcode
        "section": "Eletrônicos",
        "expiration_date": (datetime.now() + timedelta(days=365)).isoformat(),
        "images": []
    }

    response2 = await client.post(
        f"{version_prefix}/",
        json=product_data2,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response2.status_code == HTTPStatus.BAD_REQUEST
    assert "Código de barras já cadastrado" in response2.json()["detail"]

@pytest.mark.asyncio
async def test_list_products(client: AsyncClient, authenticated_user_token_str: str):
    # Criar alguns produtos para testar a listagem
    products_data = [
        {
            "name": "Produto A",
            "description": "Descrição A",
            "price": 100.0,
            "status": ProductStatusEnum.in_stock,
            "stock_quantity": 50,
            "barcode": "1234567890125",
            "section": "Eletrônicos",
            "expiration_date": (datetime.now() + timedelta(days=365)).isoformat(),
            "images": []
        },
        {
            "name": "Produto B",
            "description": "Descrição B",
            "price": 200.0,
            "status": ProductStatusEnum.restocking,
            "stock_quantity": 0,
            "barcode": "1234567890126",
            "section": "Informática",
            "expiration_date": (datetime.now() + timedelta(days=365)).isoformat(),
            "images": []
        }
    ]

    for product_data in products_data:
        response = await client.post(
            f"{version_prefix}/",
            json=product_data,
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
    assert "products" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert len(data["products"]) >= 2

    # Testar filtro por status
    response = await client.get(
        f"{version_prefix}/?status={ProductStatusEnum.in_stock}",
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert all(p["status"] == ProductStatusEnum.in_stock for p in data["products"])

    # Testar filtro por seção
    response = await client.get(
        f"{version_prefix}/",
        params={"section": "Eletrônicos"},
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    print("Query (ou cláusula where) gerada (filtro por seção):", response.url.query)
    print('SECTIONS RETORNADAS:', [p["section"] for p in data["products"]])
    assert all(p["section"] == "Eletrônicos" for p in data["products"])

    # Testar filtro por preço
    response = await client.get(
        f"{version_prefix}/?min_price=150.0&max_price=250.0",
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert all(150.0 <= p["price"] <= 250.0 for p in data["products"])

@pytest.mark.asyncio
async def test_get_product_by_id(client: AsyncClient, authenticated_user_token_str: str):
    # Criar um produto para buscar
    product_data = {
        "name": "Produto para Buscar",
        "description": "Descrição do produto",
        "price": 150.0,
        "status": ProductStatusEnum.in_stock,
        "stock_quantity": 25,
        "barcode": "1234567890127",
        "section": "Eletrônicos",
        "expiration_date": (datetime.now() + timedelta(days=365)).isoformat(),
        "images": ["https://example.com/img1.jpg"]
    }

    create_response = await client.post(
        f"{version_prefix}/",
        json=product_data,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert create_response.status_code == HTTPStatus.CREATED
    created_product = create_response.json()
    product_id = created_product["id"]

    # Buscar o produto
    response = await client.get(
        f"{version_prefix}/{product_id}",
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "product" in data
    product = data["product"]
    
    assert product["id"] == product_id
    assert product["name"] == product_data["name"]
    assert product["description"] == product_data["description"]
    assert product["price"] == product_data["price"]
    assert product["status"] == ProductStatusEnum.in_stock
    assert product["stock_quantity"] == product_data["stock_quantity"]
    assert product["barcode"] == product_data["barcode"]
    assert product["section"] == product_data["section"]
    assert product["images"] == product_data["images"]

@pytest.mark.asyncio
async def test_get_product_not_found(client: AsyncClient, authenticated_user_token_str: str):
    response = await client.get(
        f"{version_prefix}/99999",
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "Produto não encontrado" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_product(client: AsyncClient, authenticated_user_token_str: str):
    # Criar um produto para atualizar
    product_data = {
        "name": "Produto para Atualizar",
        "description": "Descrição original",
        "price": 100.0,
        "status": ProductStatusEnum.in_stock,
        "stock_quantity": 50,
        "barcode": "1234567890128",
        "section": "Eletrônicos",
        "expiration_date": (datetime.now() + timedelta(days=365)).isoformat(),
        "images": []
    }

    create_response = await client.post(
        f"{version_prefix}/",
        json=product_data,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert create_response.status_code == HTTPStatus.CREATED
    created_product = create_response.json()
    product_id = created_product["id"]

    # Atualizar o produto
    update_data = {
        "name": "Produto Atualizado",
        "description": "Nova descrição",
        "price": 150.0,
        "status": ProductStatusEnum.restocking,
        "stock_quantity": 25,
        "section": "Informática",
        "images": ["https://example.com/new_img.jpg"]
    }

    response = await client.put(
        f"{version_prefix}/{product_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.OK
    updated_product = response.json()

    assert updated_product["id"] == product_id
    assert updated_product["name"] == update_data["name"]
    assert updated_product["description"] == update_data["description"]
    assert updated_product["price"] == update_data["price"]
    assert updated_product["status"] == ProductStatusEnum.restocking
    assert updated_product["stock_quantity"] == update_data["stock_quantity"]
    assert updated_product["section"] == update_data["section"]
    assert updated_product["images"] == update_data["images"]
    assert updated_product["barcode"] == product_data["barcode"]  # Não deve ter mudado

@pytest.mark.asyncio
async def test_update_product_not_found(client: AsyncClient, authenticated_user_token_str: str):
    update_data = {
        "name": "Produto Atualizado",
        "price": 150.0
    }

    response = await client.put(
        f"{version_prefix}/99999",
        json=update_data,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "Produto não encontrado" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_product(client: AsyncClient, authenticated_user_token_str: str):
    # Criar um produto para deletar
    product_data = {
        "name": "Produto para Deletar",
        "description": "Descrição do produto",
        "price": 100.0,
        "status": ProductStatusEnum.in_stock,
        "stock_quantity": 50,
        "barcode": "1234567890129",
        "section": "Eletrônicos",
        "expiration_date": (datetime.now() + timedelta(days=365)).isoformat(),
        "images": []
    }

    create_response = await client.post(
        f"{version_prefix}/",
        json=product_data,
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert create_response.status_code == HTTPStatus.CREATED
    created_product = create_response.json()
    product_id = created_product["id"]

    # Deletar o produto
    response = await client.delete(
        f"{version_prefix}/{product_id}",
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.NO_CONTENT

    # Verificar se o produto foi realmente deletado
    get_response = await client.get(
        f"{version_prefix}/{product_id}",
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert get_response.status_code == HTTPStatus.NOT_FOUND

@pytest.mark.asyncio
async def test_delete_product_not_found(client: AsyncClient, authenticated_user_token_str: str):
    response = await client.delete(
        f"{version_prefix}/99999",
        headers={"Authorization": f"Bearer {authenticated_user_token_str}"}
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "Produto não encontrado" in response.json()["detail"]
