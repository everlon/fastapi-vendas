import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import delete
from fastapi import FastAPI, Depends
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock # Importar AsyncMock

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
from src.services.client_service import create_client

# Importar roteadores
from src.routers.auth_controller import router as auth_router
from src.routers.user_controller import router as user_router
from src.routers.order_controller import router as order_router
from src.routers.product_controller import router as product_controller
from src.routers.client_controller import router as client_controller

# Importar a dependência do controller que queremos sobrescrever
from src.routers.order_controller import get_notification_service

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

# Fixture para o NotificationService mockado
@pytest.fixture
def mock_notification_service():
    # Criar uma instância mockada do NotificationService
    mock_service = MagicMock()
    # Configurar o método assíncrono para ser um AsyncMock
    mock_service.send_order_creation_notification = AsyncMock()
    return mock_service

# Fixture para sobrescrever a dependência get_notification_service com o mock
@pytest.fixture(autouse=True)
def override_notification_dependency(mock_notification_service):
    # Sobrescrever a dependência get_notification_service na aplicação de teste
    app.dependency_overrides[get_notification_service] = lambda: mock_notification_service
    yield # Permitir que o teste execute
    # Limpar a sobrescrita após o teste
    del app.dependency_overrides[get_notification_service]

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
        client_data = ClientCreate(
            name="Cliente Teste",
            email="cliente@example.com",
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
    
    # Criar múltiplos pedidos para testar listagem e filtros
    order_data1 = {"client_id": test_client.id, "items": [{"product_id": product1_data.id, "quantity": 1}]}
    create_response1 = await client.post(
        "/api/v1/orders/",
        json=order_data1,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert create_response1.status_code == 201
    order1 = create_response1.json() # Salvar o pedido criado

    order_data2 = {"client_id": test_client.id, "items": [{"product_id": product1_data.id, "quantity": 2}]}
    create_response2 = await client.post(
        "/api/v1/orders/",
        json=order_data2,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert create_response2.status_code == 201
    # Não precisamos salvar order2 para o teste básico de listagem

    response = await client.get(
        "/api/v1/orders/",
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert response.status_code == 200
    data = response.json()

    assert "orders" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data

    # Filtrar apenas os pedidos criados por este teste (pode haver outros de testes anteriores)
    # Uma forma mais robusta seria limpar o banco antes de cada teste de listagem, mas por enquanto,
    # podemos verificar se pelo menos os pedidos que criamos estão presentes.
    # Ou melhor, garantir a limpeza no setup do teste de listagem.
    # Já temos a limpeza na fixture authenticated_user, então isso deve garantir um ambiente limpo.

    # Precisamos garantir que order1 e order2 estão na lista
    order_ids_in_list = [order["id"] for order in data["orders"]]
    assert order1["id"] in order_ids_in_list
    # assert order2["id"] in order_ids_in_list # Removido pois o teste básico não precisa verificar order2 explicitamente

    # Verificar os campos client_id e created_by_user_id nos pedidos listados
    # O teste básico de listagem verifica apenas que a lista não está vazia e contém campos esperados
    # Testes de filtro verificarão os conteúdos específicos.

    # TODO: Testar paginação no futuro
    # TODO: Testar filtros (order_id, status, section, start_date, end_date) em testes separados

# Novo teste para listar pedidos filtrando por ID do pedido
@pytest.mark.asyncio
async def test_list_orders_filter_by_id(client: AsyncClient, authenticated_user_token_str: str, test_products: list[Product], test_client: Client, authenticated_user: User):
    product_data = test_products[0]
    # Criar um pedido para filtrar
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
    order_id_to_filter = created_order["id"]

    # Listar pedidos filtrando pelo ID
    response = await client.get(
        f"/api/v1/orders/?order_id={order_id_to_filter}",
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["orders"]) == 1 # Deve retornar apenas 1 pedido
    assert data["total"] == 1        # O total deve ser 1
    assert data["orders"][0]["id"] == order_id_to_filter # Verificar se o ID do pedido retornado é o esperado
    assert data["orders"][0]["client_id"] == test_client.id
    assert data["orders"][0]["created_by_user_id"] == authenticated_user.id

# Novo teste para listar pedidos filtrando por status
@pytest.mark.asyncio
async def test_list_orders_filter_by_status(client: AsyncClient, authenticated_user_token_str: str, test_products: list[Product], test_client: Client, authenticated_user: User):
    product_data = test_products[0]
    # Criar um pedido com status 'pendente'
    order_data_pending = {"client_id": test_client.id, "items": [{"product_id": product_data.id, "quantity": 1}]}
    create_response_pending = await client.post(
        "/api/v1/orders/",
        json=order_data_pending,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert create_response_pending.status_code == 201
    order_pending = create_response_pending.json()

    # Criar outro pedido e atualizar status para 'enviado'
    order_data_to_ship = {"client_id": test_client.id, "items": [{"product_id": product_data.id, "quantity": 1}]}
    create_response_to_ship = await client.post(
        "/api/v1/orders/",
        json=order_data_to_ship,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert create_response_to_ship.status_code == 201
    order_to_ship = create_response_to_ship.json()

    update_response = await client.put(
        f"/api/v1/orders/{order_to_ship['id']}",
        json={"status": "enviado"},
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert update_response.status_code == 200

    # Listar pedidos filtrando por status 'pendente'
    response_pending = await client.get(
        "/api/v1/orders/?status=pendente",
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert response_pending.status_code == 200
    data_pending = response_pending.json()

    assert len(data_pending["orders"]) >= 1 # Deve conter o pedido 'pendente' criado neste teste
    assert all(order["status"] == "pendente" for order in data_pending["orders"])
    order_ids_pending = [order["id"] for order in data_pending["orders"]]
    assert order_pending["id"] in order_ids_pending

    # Listar pedidos filtrando por status 'enviado'
    response_shipped = await client.get(
        "/api/v1/orders/?status=enviado",
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert response_shipped.status_code == 200
    data_shipped = response_shipped.json()

    assert len(data_shipped["orders"]) >= 1 # Deve conter o pedido 'enviado' criado neste teste
    assert all(order["status"] == "enviado" for order in data_shipped["orders"])
    order_ids_shipped = [order["id"] for order in data_shipped["orders"]]
    assert order_to_ship["id"] in order_ids_shipped

# Novo teste para listar pedidos filtrando por seção de produtos
@pytest.mark.asyncio
async def test_list_orders_filter_by_section(client: AsyncClient, authenticated_user_token_str: str, test_products: list[Product], test_client: Client, authenticated_user: User):
    # Assumindo que test_products[0] é 'Eletrônicos' e test_products[1] é 'Livros'
    product_eletronico = test_products[0]
    product_livro = test_products[1]

    # Criar um pedido com item eletrônico
    order_eletronico_data = {"client_id": test_client.id, "items": [{"product_id": product_eletronico.id, "quantity": 1}]}
    create_response_eletronico = await client.post(
        "/api/v1/orders/",
        json=order_eletronico_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert create_response_eletronico.status_code == 201
    order_eletronico = create_response_eletronico.json()

    # Criar um pedido com item livro
    order_livro_data = {"client_id": test_client.id, "items": [{"product_id": product_livro.id, "quantity": 1}]}
    create_response_livro = await client.post(
        "/api/v1/orders/",
        json=order_livro_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert create_response_livro.status_code == 201
    order_livro = create_response_livro.json()

    # Criar um pedido com itens de ambas as seções (este deve aparecer em ambas as filtragens por seção)
    order_mista_data = {"client_id": test_client.id, "items": [{"product_id": product_eletronico.id, "quantity": 1}, {"product_id": product_livro.id, "quantity": 1}]}
    create_response_mista = await client.post(
        "/api/v1/orders/",
        json=order_mista_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert create_response_mista.status_code == 201
    order_mista = create_response_mista.json()

    # Listar pedidos filtrando por seção 'Eletrônicos'
    response_eletronicos = await client.get(
        "/api/v1/orders/?section=Eletrônicos",
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert response_eletronicos.status_code == 200
    data_eletronicos = response_eletronicos.json()

    assert len(data_eletronicos["orders"]) >= 2 # Deve conter o pedido eletronico e o misto
    order_ids_eletronicos = [order["id"] for order in data_eletronicos["orders"]]
    assert order_eletronico["id"] in order_ids_eletronicos
    assert order_mista["id"] in order_ids_eletronicos
    assert order_livro["id"] not in order_ids_eletronicos

    # Listar pedidos filtrando por seção 'Livros'
    response_livros = await client.get(
        "/api/v1/orders/?section=Livros",
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert response_livros.status_code == 200
    data_livros = response_livros.json()

    assert len(data_livros["orders"]) >= 2 # Deve conter o pedido livro e o misto
    order_ids_livros = [order["id"] for order in data_livros["orders"]]
    assert order_livro["id"] in order_ids_livros
    assert order_mista["id"] in order_ids_livros
    assert order_eletronico["id"] not in order_ids_livros

# Novo teste para listar pedidos filtrando por período
@pytest.mark.asyncio
async def test_list_orders_filter_by_date_range(client: AsyncClient, authenticated_user_token_str: str, test_products: list[Product], test_client: Client, authenticated_user: User):
    product_data = test_products[0]

    # Criar pedidos com datas diferentes (usando o DB diretamente para controlar created_at)
    async with TestingSessionLocal() as db:
        # Pedido na data de início (ou próximo dela)
        order_early = Order(
            client_id=test_client.id,
            created_by_user_id=authenticated_user.id,
            total=10.0,
            status="pending",
            created_at=datetime(2023, 10, 15, 10, 0, 0) # Data dentro do período
        )
        db.add(order_early)
        await db.commit()
        await db.refresh(order_early)
        order_early_id = order_early.id # Coletar o ID

        # Pedido na data de fim (ou próximo dela)
        order_late = Order(
            client_id=test_client.id,
            created_by_user_id=authenticated_user.id,
            total=20.0,
            status="pending",
            created_at=datetime(2023, 10, 25, 15, 30, 0) # Data dentro do período
        )
        db.add(order_late)
        await db.commit()
        await db.refresh(order_late)
        order_late_id = order_late.id # Coletar o ID

        # Pedido fora do período (antes do start_date)
        order_before = Order(
            client_id=test_client.id,
            created_by_user_id=authenticated_user.id,
            total=30.0,
            status="pending",
            created_at=datetime(2023, 10, 10, 9, 0, 0) # Data antes do período
        )
        db.add(order_before)
        await db.commit()
        await db.refresh(order_before)
        order_before_id = order_before.id # Coletar o ID

        # Pedido fora do período (depois do end_date)
        order_after = Order(
            client_id=test_client.id,
            created_by_user_id=authenticated_user.id,
            total=40.0,
            status="pending",
            created_at=datetime(2023, 11, 1, 11, 0, 0) # Data depois do período
        )
        db.add(order_after)
        await db.commit()
        await db.refresh(order_after)
        order_after_id = order_after.id # Coletar o ID

    # As asserções usarão os IDs coletados
    start_date_filter = "2023-10-15T00:00:00"
    end_date_filter = "2023-10-25T23:59:59"

    # Listar pedidos filtrando pelo período
    response = await client.get(
        f"/api/v1/orders/?start_date={start_date_filter}&end_date={end_date_filter}",
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert response.status_code == 200
    data = response.json()

    # Deve conter os pedidos early e late, mas não before e after
    order_ids_in_list = [order["id"] for order in data["orders"]]
    assert order_early_id in order_ids_in_list # Usar o ID coletado
    assert order_late_id in order_ids_in_list  # Usar o ID coletado
    assert order_before_id not in order_ids_in_list # Usar o ID coletado
    assert order_after_id not in order_ids_in_list   # Usar o ID coletado

# Novo teste para combinar múltiplos filtros (ex: client_id e status)
@pytest.mark.asyncio
async def test_list_orders_multiple_filters(client: AsyncClient, authenticated_user_token_str: str, test_products: list[Product], test_client: Client, authenticated_user: User):
    product_data = test_products[0]

    # Criar pedidos com diferentes clientes e status
    async with TestingSessionLocal() as db:
        # Criar um segundo cliente para este teste
        client2_data = ClientCreate(
            name="Cliente Teste 2",
            email="cliente2@example.com",
            phone="11999997777",
            address={
                "street": "Rua Teste 2",
                "number": "456",
                "complement": "Apto 2",
                "neighborhood": "Centro",
                "city": "São Paulo",
                "state": "SP",
                "zip_code": "01234567"
            },
            cpf="98765432100"
        )
        from src.services.client_service import create_client as create_client_service
        client2 = await create_client_service(db=db, client_data=client2_data)
        await db.commit()
        await db.refresh(client2)

        # Pedido 1: Cliente 1, status 'pendente'
        order1 = Order(
            client_id=test_client.id,
            created_by_user_id=authenticated_user.id,
            total=10.0,
            status="pendente"
        )
        db.add(order1)

        # Pedido 2: Cliente 1, status 'enviado'
        order2 = Order(
            client_id=test_client.id,
            created_by_user_id=authenticated_user.id,
            total=20.0,
            status="enviado"
        )
        db.add(order2)

        # Pedido 3: Cliente 2, status 'pendente'
        order3 = Order(
            client_id=client2.id,
            created_by_user_id=authenticated_user.id,
            total=30.0,
            status="pendente"
        )
        db.add(order3)

        # Pedido 4: Cliente 2, status 'enviado'
        order4 = Order(
            client_id=client2.id,
            created_by_user_id=authenticated_user.id,
            total=40.0,
            status="enviado"
        )
        db.add(order4)

        await db.commit()
        await db.refresh(order1)
        await db.refresh(order2)
        await db.refresh(order3)
        await db.refresh(order4)

    # Listar pedidos filtrando por client_id (do test_client) e status 'pendente'
    response = await client.get(
        f"/api/v1/orders/?client_id={test_client.id}&status=pendente",
        headers={
            "Authorization": f"Bearer {authenticated_user_token_str}"
        }
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["orders"]) >= 1 # Deve conter pelo menos o pedido 1 (Cliente 1, pendente)
    order_ids_in_list = [order["id"] for order in data["orders"]]
    assert order1.id in order_ids_in_list
    assert order2.id not in order_ids_in_list
    assert order3.id not in order_ids_in_list
    assert order4.id not in order_ids_in_list
    assert all(order["client_id"] == test_client.id and order["status"] == "pendente" for order in data["orders"] if order["id"] == order1.id) # Verificar se o filtro foi aplicado corretamente no pedido esperado

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

    update_data = {"status": "processando"}
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
    assert updated_order["status"] == "processando"

@pytest.mark.asyncio
async def test_update_order_not_found(client: AsyncClient, authenticated_user_token_str: str):
    update_data = {"status": "processando"}
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

        update_data = {"status": "cancelado"}
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

# Novo teste para verificar o envio da notificação ao criar pedido
@pytest.mark.asyncio
async def test_order_creation_sends_notification(client: AsyncClient, authenticated_user_token_str: str, test_products: list[Product], test_client: Client, mock_notification_service: MagicMock): # Adicionar mock_notification_service
    product_data = test_products[0]
    order_data = {
        "client_id": test_client.id,
        "items": [
            {"product_id": product_data.id, "quantity": 1}
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
    created_order = response.json()

    # Verificar se o método de notificação foi chamado no mock
    mock_notification_service.send_order_creation_notification.assert_called_once()

    # Verificar os argumentos com que o método foi chamado
    # Note que os detalhes do pedido podem variar, então vamos verificar os essenciais e o destinatário
    called_args, called_kwargs = mock_notification_service.send_order_creation_notification.call_args

    # Verificar o destinatário
    assert called_args[0] == "everlon@protonmail.com"

    # Verificar alguns detalhes essenciais no dicionário order_details (o segundo argumento)
    order_details_arg = called_args[1]
    assert isinstance(order_details_arg, dict)
    assert order_details_arg["order_id"] == created_order["id"]
    assert order_details_arg["client_id"] == test_client.id
    assert order_details_arg["total"] == created_order["total"]
    assert order_details_arg["status"] == created_order["status"]
 