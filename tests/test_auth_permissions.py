import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import delete
from fastapi import FastAPI
from unittest.mock import MagicMock, AsyncMock

from database import Base, get_db
from src.models.user import User
from src.models.product import Product
from src.models.order import Order, OrderItem
from src.models.client import Client

from src.schemas.user import UserCreate
from src.schemas.product import ProductCreate, ProductStatusEnum
from src.schemas.order import OrderCreate
from src.schemas.client import ClientCreate

from src.services.user_service import create_user
from src.services.product_service import create_product
from src.services.order_service import create_order
from src.services.client_service import create_client

# Importar roteadores
from src.routers.auth_controller import router as auth_router
from src.routers.user_controller import router as user_router
from src.routers.order_controller import router as order_router
from src.routers.product_controller import router as product_controller
from src.routers.client_controller import router as client_controller

# Importar NotificationService e EmailNotificationChannel
from src.notifications.notification_service import NotificationService
from src.notifications.email_channel import EmailNotificationChannel

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

testing_engine = None
TestingSessionLocal = None

@pytest.fixture(scope="session")
def anyio_backend():
    return 'asyncio'

@pytest.fixture(scope="session", autouse=True)
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

# Nova fixture para mockar o NotificationService
@pytest.fixture
def mock_notification_service():
    # Cria um MagicMock para o NotificationService
    mock_service = MagicMock(spec=NotificationService)
    # Mocka o método send_order_creation_notification para ser um AsyncMock
    mock_service.send_order_creation_notification = AsyncMock()
    return mock_service

# Sobrescrever a dependência do NotificationService na aplicação de teste
# Isso garante que o mock seja usado quando o controller precisar do serviço
def override_get_notification_service():
    # Retorna o mock do serviço de notificação
    # NOTA: Esta dependência será injetada nos endpoints, mas não nas chamadas diretas como na fixture test_order.
    # Portanto, ainda precisamos passar o mock explicitamente na fixture test_order.
    return mock_notification_service()

# app.dependency_overrides[get_notification_service] = override_get_notification_service # Comentado pois a fixture test_order chama o service direto

@pytest.fixture(scope="session")
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def test_users():
    async with TestingSessionLocal() as db:
        # Limpar dados existentes
        await db.execute(delete(OrderItem))
        await db.execute(delete(Order))
        await db.execute(delete(Product))
        await db.execute(delete(Client))
        await db.execute(delete(User))
        await db.commit()

        # Criar usuário admin
        admin_data = UserCreate(
            username="admin",
            email="admin@example.com",
            password="admin123",
            is_admin=True
        )
        admin = await create_user(db=db, user=admin_data)
        await db.commit()
        await db.refresh(admin)
        admin_id = admin.id

        # Criar usuário normal
        user_data = UserCreate(
            username="user",
            email="user@example.com",
            password="user123",
            is_admin=False
        )
        user = await create_user(db=db, user=user_data)
        await db.commit()
        await db.refresh(user)
        user_id = user.id

        return {"admin_id": admin_id, "user_id": user_id}

@pytest.fixture
async def admin_token(client: AsyncClient, test_users):
    test_users_dict = await test_users if callable(test_users) else test_users
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture
async def user_token(client: AsyncClient, test_users):
    test_users_dict = await test_users if callable(test_users) else test_users
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "user", "password": "user123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture
async def test_product(admin_token: str):
    async with TestingSessionLocal() as db:
        product_data = ProductCreate(
            name="Produto Teste",
            description="Descrição Teste",
            price=10.0,
            stock_quantity=100,
            barcode="123456789012",
            section="Teste",
            expiration_date="2025-12-31",
            images=[],
            status=ProductStatusEnum.in_stock
        )
        product = await create_product(db=db, product_data=product_data)
        await db.commit()
        await db.refresh(product)
        return product

@pytest.fixture
async def test_client(admin_token: str):
    async with TestingSessionLocal() as db:
        client_data = ClientCreate(
            name="Cliente Teste",
            email="cliente@teste.com",
            phone="11999998888",
            address={
                "street": "Rua Teste",
                "number": "123",
                "complement": "Apto 1",
                "neighborhood": "Centro",
                "city": "São Paulo",
                "state": "SP",
                "zip_code": "01234567"
            },
            cpf="52998224725"
        )
        client = await create_client(db=db, client_data=client_data)
        await db.commit()
        await db.refresh(client)
        return client

@pytest.fixture
async def test_order(admin_token: str, test_product: Product, test_client: Client, test_users: dict, mock_notification_service: MagicMock):
    async with TestingSessionLocal() as db:
        order_data = OrderCreate(
            client_id=test_client.id,
            items=[{"product_id": test_product.id, "quantity": 1}]
        )
        from src.models.user import User as UserModel
        from sqlalchemy.future import select
        admin = (await db.execute(select(UserModel).where(UserModel.id == test_users["admin_id"]))).scalar_one()
        order = await create_order(db=db, order_data=order_data, created_by_user=admin, notification_service=mock_notification_service)
        await db.commit()
        await db.refresh(order)
        return order

# Testes de permissão para produtos
@pytest.mark.asyncio
async def test_create_product_permissions(client: AsyncClient, admin_token: str, user_token: str):
    # Teste com usuário normal (deve falhar)
    product_data = {
        "name": "Produto Não Autorizado",
        "description": "Descrição",
        "price": 10.0,
        "stock_quantity": 100,
        "barcode": "123456789013",
        "section": "Teste",
        "expiration_date": "2025-12-31T00:00:00",
        "images": ["http://example.com/img1.jpg"],
        "status": "em estoque"
    }
    
    response = await client.post(
        "/api/v1/products/",
        json=product_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403
    assert "Não autorizado" in response.json()["detail"]

    # Teste com admin (deve passar)
    response = await client.post(
        "/api/v1/products/",
        json=product_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_update_product_permissions(client: AsyncClient, admin_token: str, user_token: str, test_product: Product):
    update_data = {"name": "Produto Atualizado"}
    
    # Teste com usuário normal (deve falhar)
    response = await client.put(
        f"/api/v1/products/{test_product.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403
    assert "Não autorizado" in response.json()["detail"]

    # Teste com admin (deve passar)
    response = await client.put(
        f"/api/v1/products/{test_product.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_delete_product_permissions(client: AsyncClient, admin_token: str, user_token: str, test_product: Product):
    # Teste com usuário normal (deve falhar)
    response = await client.delete(
        f"/api/v1/products/{test_product.id}",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403
    assert "Não autorizado" in response.json()["detail"]

    # Teste com admin (deve passar)
    response = await client.delete(
        f"/api/v1/products/{test_product.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204

# Testes de permissão para pedidos
@pytest.mark.asyncio
async def test_order_access_permissions(client: AsyncClient, admin_token: str, user_token: str, test_order: Order):
    # Teste de acesso a pedido de outro usuário (deve falhar com 404)
    response = await client.get(
        f"/api/v1/orders/{test_order.id}",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 404
    assert "Pedido não encontrado" in response.json()["detail"]

    # Teste de acesso com admin (deve passar)
    response = await client.get(
        f"/api/v1/orders/{test_order.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_order_update_permissions(client: AsyncClient, admin_token: str, user_token: str, test_order: Order):
    update_data = {"status": "processando"}
    
    # Teste de atualização por outro usuário (deve falhar com 404)
    response = await client.put(
        f"/api/v1/orders/{test_order.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 404
    assert "Pedido não encontrado" in response.json()["detail"]

    # Teste de atualização pelo admin (deve passar)
    response = await client.put(
        f"/api/v1/orders/{test_order.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_order_delete_permissions(client: AsyncClient, admin_token: str, user_token: str, test_order: Order):
    # Teste de exclusão por outro usuário (deve falhar com 404)
    response = await client.delete(
        f"/api/v1/orders/{test_order.id}",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 404
    assert "Pedido não encontrado" in response.json()["detail"]

    # Teste de exclusão pelo admin (deve passar)
    response = await client.delete(
        f"/api/v1/orders/{test_order.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204

# Testes de permissão para clientes
@pytest.mark.asyncio
async def test_client_access_permissions(client: AsyncClient, admin_token: str, user_token: str, test_client: Client):
    # Teste de acesso a cliente (deve passar para ambos)
    response = await client.get(
        f"/api/v1/clients/{test_client.id}",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 200

    response = await client.get(
        f"/api/v1/clients/{test_client.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_client_update_permissions(client: AsyncClient, admin_token: str, user_token: str, test_client: Client):
    update_data = {"name": "Cliente Atualizado"}
    
    # Teste de atualização por usuário normal (deve falhar)
    response = await client.put(
        f"/api/v1/clients/{test_client.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403
    assert "Não autorizado" in response.json()["detail"]

    # Teste de atualização pelo admin (deve passar)
    response = await client.put(
        f"/api/v1/clients/{test_client.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_client_delete_permissions(client: AsyncClient, admin_token: str, user_token: str, test_client: Client):
    # Teste de exclusão por usuário normal (deve falhar)
    response = await client.delete(
        f"/api/v1/clients/{test_client.id}",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403
    assert "Não autorizado" in response.json()["detail"]

    # Teste de exclusão pelo admin (deve passar)
    response = await client.delete(
        f"/api/v1/clients/{test_client.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204 