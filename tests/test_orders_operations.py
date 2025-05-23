import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import delete
from fastapi import FastAPI, Depends

from database import Base, get_db

from src.models.user import User # Precisamos do modelo de usuário para criar um usuário de teste
from src.models.product import Product # Precisamos do modelo de produto para criar produtos de teste
from src.models.order import Order, OrderItem # Importar modelos de Pedido
from src.models.client import Client # Importar modelo de Cliente

from src.schemas.user import UserCreate
from src.schemas.product import ProductCreate, ProductStatusEnum # Importar ProductStatusEnum
from src.schemas.order import OrderCreate, OrderItemSchema, OrderUpdate
from src.schemas.client import ClientCreate # Importar schema de Cliente

from src.services.user_service import create_user
from src.services.order_service import create_order
from src.services.client_service import create_client

# Importar roteadores
from src.routers.auth_controller import router as auth_router
from src.routers.user_controller import router as user_router
from src.routers.order_controller import router as order_router
from src.routers.product_controller import router as product_controller
from src.routers.client_controller import router as client_controller

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

testing_engine = None
TestingSessionLocal = None

@pytest.fixture(scope="session")
def anyio_backend():
    return 'asyncio'

@pytest.fixture(scope="session", autouse=True) # autouse=True para rodar automaticamente
async def setup_database():
    global testing_engine, TestingSessionLocal
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"

    testing_engine = create_async_engine(DATABASE_URL, echo=True)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=testing_engine, class_=AsyncSession)

    async with testing_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield 
    async with testing_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await testing_engine.dispose()

async def get_test_db():
    async with TestingSessionLocal() as db:
        yield db

app = FastAPI()

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(user_router, prefix="/api/v1/users", tags=["users"])
app.include_router(order_router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(product_controller, prefix="/api/v1/products", tags=["products"])
app.include_router(client_controller, prefix="/api/v1/clients", tags=["clients"])

app.dependency_overrides[get_db] = get_test_db

@pytest.fixture(scope="session")
async def client():
    # Usar a instância 'app' local para o cliente de teste
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# Fixture para criar um usuário de teste e obter token de autenticação
@pytest.fixture
async def authenticated_user(client: AsyncClient): # Renomeada e modificada para retornar o objeto User
    # Obter sessão diretamente da TestingSessionLocal
    async with TestingSessionLocal() as db:
        # Limpar usuários, produtos, pedidos, itens de pedido e clientes existentes antes de criar novo usuário/produtos para este teste/fixture
        await db.execute(delete(OrderItem))
        await db.execute(delete(Order))
        await db.execute(delete(Product))
        await db.execute(delete(Client))
        await db.execute(delete(User))
        await db.commit()

        user_data = UserCreate(username="testuser", email="test@example.com", password="testpassword")
        user = await create_user(db=db, user=user_data)
        await db.commit()
        await db.refresh(user)

        token_response = await client.post("/api/v1/auth/token", data={"username": user_data.username, "password": user_data.password})
        assert token_response.status_code == 200
        
        return user # Retornar o objeto User

@pytest.fixture
async def authenticated_user_token_str(client: AsyncClient, authenticated_user: User): # Depende de authenticated_user
    token_response = await client.post("/api/v1/auth/token", data={"username": authenticated_user.username, "password": "testpassword"})
    assert token_response.status_code == 200
    token_data = token_response.json()
    return token_data["access_token"]

@pytest.fixture
async def test_client(authenticated_user: User): 
    async with TestingSessionLocal() as db:
        client_data = ClientCreate(name="Cliente Teste", email="cliente@example.com", phone="11999998888", address="Rua Teste, 123")
        from src.services.client_service import create_client
        client = await create_client(db=db, client_data=client_data)
        await db.commit()
        await db.refresh(client)
        return client 

@pytest.fixture
async def test_products():
    async with TestingSessionLocal() as db:
        product1_data = ProductCreate(name="Produto Teste 1", description="Descrição 1", price=10.0, stock_quantity=100, barcode="123456789012", section="Eletrônicos", expiration_date="2025-12-31", images=["http://example.com/img1.jpg"], status=ProductStatusEnum.in_stock)
        product2_data = ProductCreate(name="Produto Teste 2", description="Descrição 2", price=20.0, stock_quantity=50, barcode="123456789013", section="Livros", expiration_date="2026-01-15", images=["http://example.com/img2.jpg"], status=ProductStatusEnum.in_stock)

        from src.services.product_service import create_product

        product1 = await create_product(db=db, product_data=product1_data)
        product2 = await create_product(db=db, product_data=product2_data)
        await db.commit()
        await db.refresh(product1)
        await db.refresh(product2)

        return [product1, product2]

@pytest.mark.asyncio
async def test_create_order(client: AsyncClient, authenticated_user: User, authenticated_user_token_str: str, test_products: list[Product], test_client: Client): # Atualizadas dependências e tipos
    product1_data = test_products[0]
    product2_data = test_products[1]
    order_data = {
        "client_id": test_client.id, # Incluir client_id
        "items": [
            {"product_id": product1_data.id, "quantity": 2},
            {"product_id": product2_data.id, "quantity": 1}
        ]
    }
    response = await client.post(
        "/api/v1/orders/",
        json=order_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert response.status_code == 201
    order = response.json()
    
    assert order["client_id"] == test_client.id
    assert order["created_by_user_id"] == authenticated_user.id

    assert len(order["items"]) == 2
    assert order["total"] == (product1_data.price * 2) + (product2_data.price * 1) # Verificar cálculo do total (usando .price agora)

    updated_product1_res = await client.get(
        f"/api/v1/products/{product1_data.id}",
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    updated_product2_res = await client.get(
        f"/api/v1/products/{product2_data.id}",
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert updated_product1_res.status_code == 200
    assert updated_product2_res.status_code == 200
    updated_product1 = updated_product1_res.json()
    updated_product2 = updated_product2_res.json()
    
    assert updated_product1["product"]["stock_quantity"] == product1_data.stock_quantity - 2
    assert updated_product2["product"]["stock_quantity"] == product2_data.stock_quantity - 1

@pytest.mark.asyncio
async def test_create_order_insufficient_stock(client: AsyncClient, authenticated_user: User, authenticated_user_token_str: str, test_products: list[Product], test_client: Client): # Atualizadas dependências e tipos
    product_data = test_products[0] # Usar o primeiro produto
    order_data = {
        "client_id": test_client.id, # Incluir client_id
        "items": [
            {"product_id": product_data.id, "quantity": product_data.stock_quantity + 1} # Tentar pedir mais do que tem em estoque
        ]
    }
    response = await client.post(
        "/api/v1/orders/",
        json=order_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert response.status_code == 400
    assert "Estoque insuficiente" in response.json()["detail"]

# Teste para criar pedido com produto não encontrado
@pytest.mark.asyncio
async def test_create_order_product_not_found(client: AsyncClient, authenticated_user_token_str: str, test_client: Client): # Atualizadas dependências
    order_data = {
        "client_id": test_client.id, # Incluir client_id
        "items": [
            {"product_id": 99999, "quantity": 1} # ID de produto que não existe
        ]
    }
    response = await client.post(
        "/api/v1/orders/",
        json=order_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert response.status_code == 404
    assert "não encontrado" in response.json()["detail"]

# Novo teste para criar pedido com cliente não encontrado
@pytest.mark.asyncio
async def test_create_order_client_not_found(client: AsyncClient, authenticated_user_token_str: str, test_products: list[Product]): # Atualizadas dependências
     product1_data = test_products[0]
     order_data = {
        "client_id": 99999, # ID de cliente que não existe
        "items": [
            {"product_id": product1_data.id, "quantity": 1}
        ]
    }
     response = await client.post(
        "/api/v1/orders/",
        json=order_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
     assert response.status_code == 404
     assert "Cliente com ID 99999 não encontrado." in response.json()["detail"]

@pytest.mark.asyncio
async def test_list_orders(client: AsyncClient, authenticated_user_token_str: str, test_products: list[Product], test_client: Client, authenticated_user: User): # Atualizadas dependências e tipos
    product1_data = test_products[0]
    
    order_data1 = {"client_id": test_client.id, "items": [{"product_id": product1_data.id, "quantity": 1}]}
    create_response1 = await client.post(
        "/api/v1/orders/",
        json=order_data1,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert create_response1.status_code == 201

    order_data2 = {"client_id": test_client.id, "items": [{"product_id": product1_data.id, "quantity": 2}]}
    create_response2 = await client.post(
        "/api/v1/orders/",
        json=order_data2,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert create_response2.status_code == 201

    response_all = await client.get(
        "/api/v1/orders/",
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert response_all.status_code == 200
    data_all = response_all.json()
    assert data_all["total"] >= 2 
    
    response_filtered = await client.get(
        f"/api/v1/orders/?client_id={test_client.id}", 
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert response_filtered.status_code == 200
    data_filtered = response_filtered.json()
    assert data_filtered["total"] == 2 
    assert len(data_filtered["orders"]) == 2

    for order in data_filtered["orders"]:
        assert order["client_id"] == test_client.id
        assert order["created_by_user_id"] == authenticated_user.id

@pytest.mark.asyncio
async def test_get_order_by_id(client: AsyncClient, authenticated_user_token_str: str, test_products: list[Product], test_client: Client): # test_products agora retorna dicts
    product_data = test_products[0]
    order_data = {"client_id": test_client.id, "items": [{"product_id": product_data.id, "quantity": 1}]}

    create_response = await client.post(
        "/api/v1/orders/",
        json=order_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert create_response.status_code == 201
    created_order = create_response.json()
    order_id = created_order["id"]

    get_response = await client.get(
        f"/api/v1/orders/{order_id}",
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert get_response.status_code == 200
    order_response = get_response.json()
    assert order_response["id"] == order_id
    assert len(order_response["items"]) == 1
    assert order_response["items"][0]["product_id"] == product_data.id
    assert order_response["items"][0]["quantity"] == 1

@pytest.mark.asyncio
async def test_get_order_by_id_not_found(client: AsyncClient, authenticated_user_token_str: str):
    response = await client.get(
        "/api/v1/orders/99999",
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert response.status_code == 404
    assert "Pedido não encontrado" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_order_by_id_other_user(client: AsyncClient, test_client: Client): # Remover dependência de db
    async with TestingSessionLocal() as db:

        user1_data = UserCreate(username="testuser1", email="test1@example.com", password="testpassword1")
        user1 = await create_user(db=db, user=user1_data)
        await db.commit()
        await db.refresh(user1)
        token_response1 = await client.post("/api/v1/auth/token", data={"username": "testuser1", "password": "testpassword1"})
        assert token_response1.status_code == 200
        token_data1 = token_response1.json()
        token1 = token_data1["access_token"]

        user2_data = UserCreate(username="testuser2", email="test2@example.com", password="testpassword2")
        user2 = await create_user(db=db, user=user2_data)
        await db.commit()
        await db.refresh(user2)

        token_response2 = await client.post("/api/v1/auth/token", data={"username": "testuser2", "password": "testpassword2"})
        assert token_response2.status_code == 200
        token_data2 = token_response2.json()
        token2 = token_data2["access_token"]

        from src.services.product_service import create_product as create_product_service
        product_data = ProductCreate(name="Produto Pedido", description="Desc", price=15.0, stock_quantity=10, barcode="orderprod1", section="Geral", expiration_date="2025-12-31", images=[], status=ProductStatusEnum.in_stock)
        product = await create_product_service(db=db, product_data=product_data)
        await db.commit()
        await db.refresh(product)

        order_data = {"client_id": test_client.id, "items": [{"product_id": product.id, "quantity": 1}]}
        create_response2 = await client.post(
            "/api/v1/orders/",
            json=order_data,
            headers={
                "Authorization": f"Bearer {token2}"
            }
        )
        assert create_response2.status_code == 201
        order_id_user2 = create_response2.json()["id"]

        get_response = await client.get(
            f"/api/v1/orders/{order_id_user2}",
            headers={
                "Authorization": f"Bearer {token1}"
            }
        )
        assert get_response.status_code == 404 # Deve retornar 404 porque o pedido não pertence a este usuário
        assert "Pedido não encontrado" in get_response.json()["detail"]

@pytest.mark.asyncio
async def test_update_order(client: AsyncClient, authenticated_user_token_str: str, test_products: list[Product], test_client: Client): # test_products agora retorna dicts
    product_data = test_products[0]
    order_data = {"client_id": test_client.id, "items": [{"product_id": product_data.id, "quantity": 1}]}

    create_response = await client.post(
        "/api/v1/orders/",
        json=order_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert create_response.status_code == 201
    created_order = create_response.json()
    order_id = created_order["id"]

    update_data = {"status": "completed"}
    update_response = await client.put(
        f"/api/v1/orders/{order_id}",
        json=update_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert update_response.status_code == 200
    updated_order = update_response.json()
    assert updated_order["id"] == order_id
    assert updated_order["status"] == "completed"

@pytest.mark.asyncio
async def test_update_order_not_found(client: AsyncClient, authenticated_user_token_str: str):
    update_data = {"status": "completed"}
    response = await client.put(
        "/api/v1/orders/99999",
        json=update_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert response.status_code == 404
    assert "Pedido não encontrado" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_order_other_user(client: AsyncClient, test_client: Client): 
    async with TestingSessionLocal() as db:
        user1_data = UserCreate(username="testuser1", email="test1@example.com", password="testpassword1")
        user1 = await create_user(db=db, user=user1_data)
        await db.commit()
        await db.refresh(user1)
        token_response1 = await client.post("/api/v1/auth/token", data={"username": "testuser1", "password": "testpassword1"})
        assert token_response1.status_code == 200
        token_data1 = token_response1.json()
        token1 = token_data1["access_token"]

        user2_data = UserCreate(username="testuser2", email="test2@example.com", password="testpassword2")
        user2 = await create_user(db=db, user=user2_data)
        await db.commit()
        await db.refresh(user2)

        token_response2 = await client.post("/api/v1/auth/token", data={"username": "testuser2", "password": "testpassword2"})
        assert token_response2.status_code == 200
        token_data2 = token_response2.json()
        token2 = token_data2["access_token"]

        from src.services.product_service import create_product as create_product_service
        product_data = ProductCreate(name="Produto Pedido Update", description="Desc Update", price=25.0, stock_quantity=20, barcode="orderprodupdate", section="Geral", expiration_date="2025-12-31", images=[], status=ProductStatusEnum.in_stock)
        product = await create_product_service(db=db, product_data=product_data)
        await db.commit()
        await db.refresh(product)

        from src.services.order_service import create_order as create_order_service
        order_data = {"client_id": test_client.id, "items": [{"product_id": product.id, "quantity": 1}]}
        create_response2 = await client.post(
            "/api/v1/orders/",
            json=order_data,
            headers={
                "Authorization": f"Bearer {token2}"
            }
        )
        assert create_response2.status_code == 201
        order_id_user2 = create_response2.json()["id"]

        update_data = {"status": "cancelled"}
        update_response = await client.put(
            f"/api/v1/orders/{order_id_user2}",
            json=update_data,
            headers={
                "Authorization": f"Bearer {token1}"
            }
        )
        assert update_response.status_code == 404 
        assert "Pedido não encontrado" in update_response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_order(client: AsyncClient, authenticated_user_token_str: str, test_products: list[Product], test_client: Client): # test_products agora retorna dicts
    product_data = test_products[0]
    initial_stock = product_data.stock_quantity # Obter estoque inicial
    order_data = {"client_id": test_client.id, "items": [{"product_id": product_data.id, "quantity": 1}]}

    create_response = await client.post(
        "/api/v1/orders/",
        json=order_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert create_response.status_code == 201
    created_order = create_response.json()
    order_id = created_order["id"]

    delete_response = await client.delete(
        f"/api/v1/orders/{order_id}",
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert delete_response.status_code == 204 # No Content

    get_response = await client.get(
        f"/api/v1/orders/{order_id}",
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert get_response.status_code == 404

    async with TestingSessionLocal() as db:
        from sqlalchemy import select
        updated_product = (await db.execute(select(Product).filter(Product.id == product_data.id))).scalar_one_or_none()
        assert updated_product is not None
        assert updated_product.stock_quantity == initial_stock # Estoque deve voltar ao valor inicial

@pytest.mark.asyncio
async def test_delete_order_other_user(client: AsyncClient, test_client: Client): # Remover dependência de db
    async with TestingSessionLocal() as db:

        user1_data = UserCreate(username="testuser1", email="test1@example.com", password="testpassword1")
        user1 = await create_user(db=db, user=user1_data)
        await db.commit()
        await db.refresh(user1)
        token_response1 = await client.post("/api/v1/auth/token", data={"username": "testuser1", "password": "testpassword1"})
        assert token_response1.status_code == 200
        token_data1 = token_response1.json()
        token1 = token_data1["access_token"]

        user2_data = UserCreate(username="testuser2", email="test2@example.com", password="testpassword2")
        user2 = await create_user(db=db, user=user2_data)
        await db.commit()
        await db.refresh(user2)

        token_response2 = await client.post("/api/v1/auth/token", data={"username": "testuser2", "password": "testpassword2"})
        assert token_response2.status_code == 200
        token_data2 = token_response2.json()
        token2 = token_data2["access_token"]

        from src.services.product_service import create_product as create_product_service
        product_data = ProductCreate(name="Produto Pedido Delete", description="Desc Delete", price=35.0, stock_quantity=30, barcode="orderproddelete", section="Geral", expiration_date="2025-12-31", images=[], status=ProductStatusEnum.in_stock)
        product = await create_product_service(db=db, product_data=product_data)
        await db.commit()
        await db.refresh(product)

        from src.services.order_service import create_order as create_order_service
        order_data = {"client_id": test_client.id, "items": [{"product_id": product.id, "quantity": 1}]}
        create_response2 = await client.post(
            "/api/v1/orders/",
            json=order_data,
            headers={
                "Authorization": f"Bearer {token2}"
            }
        )
        assert create_response2.status_code == 201
        order_id_user2 = create_response2.json()["id"]

        delete_response = await client.delete(
            f"/api/v1/orders/{order_id_user2}",
            headers={
                "Authorization": f"Bearer {token1}"
            }
        )
        assert delete_response.status_code == 404 # Deve retornar 404 porque o pedido não pertence a este usuário
        assert "Pedido não encontrado" in delete_response.json()["detail"]
