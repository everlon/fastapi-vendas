import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import delete
from fastapi import FastAPI, Depends # Importar Depends

from database import Base, get_db # Importar Base do seu models ou database

from src.models.user import User # Precisamos do modelo de usuário para criar um usuário de teste
from src.models.product import Product # Precisamos do modelo de produto para criar produtos de teste
from src.models.order import Order, OrderItem # Importar modelos de Pedido

from src.schemas.user import UserCreate
from src.schemas.product import ProductCreate, ProductStatusEnum # Importar ProductStatusEnum
from src.schemas.order import OrderCreate, OrderItemSchema, OrderUpdate

from src.services.user_service import create_user
from src.services.order_service import create_order
# from auth import authenticate_user, create_access_token # Removido, não usado diretamente nas fixtures/testes agora

# Importar roteadores
from src.routers.auth_controller import router as auth_router
from src.routers.user_controller import router as user_router
from src.routers.order_controller import router as order_router
from src.routers.product_controller import router as product_controller

# Configuração do banco de dados de teste em memória (SQLite)
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Variáveis para armazenar a engine e sessionmaker do banco de dados de teste
testing_engine = None
TestingSessionLocal = None

@pytest.fixture(scope="session")
def anyio_backend():
    return 'asyncio'

# Fixture para configurar o banco de dados e criar tabelas (escopo de sessão)
@pytest.fixture(scope="session", autouse=True) # autouse=True para rodar automaticamente
async def setup_database():
    global testing_engine, TestingSessionLocal
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"

    testing_engine = create_async_engine(DATABASE_URL, echo=True)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=testing_engine, class_=AsyncSession)

    async with testing_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield # Rodar testes
    # Limpeza após todos os testes da sessão
    async with testing_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await testing_engine.dispose()

# Função geradora assíncrona para sobrescrever a dependência do banco de dados (NÃO é uma fixture)
async def get_test_db():
    async with TestingSessionLocal() as db:
        yield db

# Criar uma nova instância do FastAPI para os testes
app = FastAPI()

# Incluir roteadores na instância de teste com prefixos
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(user_router, prefix="/api/v1/users", tags=["users"])
app.include_router(order_router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(product_controller, prefix="/api/v1/products", tags=["products"])

# Sobrescrever a dependência get_db com a versão de teste assíncrona
app.dependency_overrides[get_db] = get_test_db

# Fixture para o cliente de teste AsyncClient (escopo de sessão)
@pytest.fixture(scope="session")
async def client():
    # Usar a instância 'app' local para o cliente de teste
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# Fixture para criar um usuário de teste e obter token de autenticação
@pytest.fixture
async def authenticated_user_token(client: AsyncClient): # Remover dependência de db
    # Obter sessão diretamente da TestingSessionLocal
    async with TestingSessionLocal() as db:
        # Limpar usuários, produtos, pedidos e itens de pedido existentes antes de criar novo usuário/produtos para este teste/fixture
        await db.execute(delete(OrderItem))
        await db.execute(delete(Order))
        await db.execute(delete(Product))
        await db.execute(delete(User))
        await db.commit()

        user_data = UserCreate(username="testuser", email="test@example.com", password="testpassword")
        user = await create_user(db=db, user=user_data)
        await db.commit()
        await db.refresh(user)

        # Autenticar e obter token
        # Usar o cliente para chamar o endpoint de autenticação
        token_response = await client.post("/api/v1/auth/token", data={"username": user_data.username, "password": user_data.password})
        assert token_response.status_code == 200
        token_data = token_response.json()
        return token_data["access_token"]

# Fixture para criar produtos de teste
@pytest.fixture
async def test_products(): # Remover dependência de db
    # Obter sessão diretamente da TestingSessionLocal
    async with TestingSessionLocal() as db:
        # Certificar que não há produtos duplicados de execuções anteriores
        # A limpeza é feita em authenticated_user_token, mas garantimos aqui também se necessário
        await db.execute(delete(Product))
        await db.commit()

        product1_data = ProductCreate(name="Produto Teste 1", description="Descrição 1", price=10.0, stock_quantity=100, barcode="123456789012", section="Eletrônicos", expiration_date="2025-12-31", images=["http://example.com/img1.jpg"], status=ProductStatusEnum.in_stock)
        product2_data = ProductCreate(name="Produto Teste 2", description="Descrição 2", price=20.0, stock_quantity=50, barcode="123456789013", section="Livros", expiration_date="2026-01-15", images=["http://example.com/img2.jpg"], status=ProductStatusEnum.in_stock)

        # Importar create_product do serviço de produto
        from src.services.product_service import create_product

        product1 = await create_product(db=db, product_data=product1_data)
        product2 = await create_product(db=db, product_data=product2_data)
        await db.commit()
        await db.refresh(product1)
        await db.refresh(product2)

        # Precisamos retornar objetos que podem ser usados pelos testes, que não dependam da sessão fechada
        # Uma maneira é retornar dicionários ou schemas Pydantic, ou IDs e buscar no teste
        # Vamos retornar dicionários por enquanto para simplificar
        return [
            product1_data.model_dump(by_alias=True) | {"id": product1.id, "stock_quantity": product1.stock_quantity, "status": str(product1.status), "active": product1.active, "created_at": product1.created_at.isoformat(), "updated_at": (product1.updated_at.isoformat() if product1.updated_at else None), "views":[] },
            product2_data.model_dump(by_alias=True) | {"id": product2.id, "stock_quantity": product2.stock_quantity, "status": str(product2.status), "active": product2.active, "created_at": product2.created_at.isoformat(), "updated_at": (product2.updated_at.isoformat() if product2.updated_at else None), "views":[] }
            ]

# Teste para criar um pedido
@pytest.mark.asyncio
async def test_create_order(client: AsyncClient, authenticated_user_token: str, test_products: list[dict]): # test_products agora retorna dicts
    product1_data = test_products[0]
    product2_data = test_products[1]
    order_data = {
        "items": [
            {"product_id": product1_data["id"], "quantity": 2},
            {"product_id": product2_data["id"], "quantity": 1}
        ]
    }
    response = await client.post(
        "/api/v1/orders/",
        json=order_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token}"
        }
    )
    assert response.status_code == 201
    order = response.json()
    assert order["user_id"] is not None # Verificar se o user_id foi associado
    assert len(order["items"]) == 2
    # Ajustar cálculo do total para usar dados do produto da fixture
    assert order["total"] == (product1_data["price"] * 2) + (product2_data["price"] * 1) # Verificar cálculo do total

    # Verificar se o estoque foi atualizado
    # A chamada HTTP para o endpoint de produto já fará isso, vamos usar o cliente
    updated_product1_res = await client.get(
        f"/api/v1/products/{product1_data['id']}",
        headers={
            "Authorization": f"Bearer {authenticated_user_token}"
        }
    )
    updated_product2_res = await client.get(
        f"/api/v1/products/{product2_data['id']}",
        headers={
            "Authorization": f"Bearer {authenticated_user_token}"
        }
    )
    assert updated_product1_res.status_code == 200
    assert updated_product2_res.status_code == 200
    updated_product1 = updated_product1_res.json()
    updated_product2 = updated_product2_res.json()
    # Ajustar asserção de estoque para usar dados do produto da fixture
    assert updated_product1["product"]["stock_quantity"] == product1_data["stock_quantity"] - 2
    assert updated_product2["product"]["stock_quantity"] == product2_data["stock_quantity"] - 1

# Teste para criar pedido com estoque insuficiente
@pytest.mark.asyncio
async def test_create_order_insufficient_stock(client: AsyncClient, authenticated_user_token: str, test_products: list[dict]): # test_products agora retorna dicts
    product_data = test_products[0] # Usar o primeiro produto
    order_data = {
        "items": [
            {"product_id": product_data["id"], "quantity": product_data["stock_quantity"] + 1} # Tentar pedir mais do que tem em estoque
        ]
    }
    response = await client.post(
        "/api/v1/orders/",
        json=order_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token}"
        }
    )
    assert response.status_code == 400
    assert "Estoque insuficiente" in response.json()["detail"]

# Teste para criar pedido com produto não encontrado
@pytest.mark.asyncio
async def test_create_order_product_not_found(client: AsyncClient, authenticated_user_token: str):
    order_data = {
        "items": [
            {"product_id": 99999, "quantity": 1} # ID de produto que não existe
        ]
    }
    response = await client.post(
        "/api/v1/orders/",
        json=order_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token}"
        }
    )
    assert response.status_code == 404
    assert "não encontrado" in response.json()["detail"]

# Teste para listar pedidos
@pytest.mark.asyncio
async def test_list_orders(client: AsyncClient, authenticated_user_token: str, test_products: list[dict]): # test_products agora retorna dicts
    product1_data = test_products[0]
    order_data1 = {"items": [{"product_id": product1_data["id"], "quantity": 1}]}
    
    # Usar o cliente HTTP para criar os pedidos de teste
    create_response1 = await client.post(
        "/api/v1/orders/",
        json=order_data1,
        headers={
            "Authorization": f"Bearer {authenticated_user_token}"
        }
    )
    assert create_response1.status_code == 201

    order_data2 = {"items": [{"product_id": product1_data["id"], "quantity": 2}]}
    create_response2 = await client.post(
        "/api/v1/orders/",
        json=order_data2,
        headers={
            "Authorization": f"Bearer {authenticated_user_token}"
        }
    )
    assert create_response2.status_code == 201

    # Listar pedidos usando o cliente HTTP
    response = await client.get(
        "/api/v1/orders/",
        headers={
            "Authorization": f"Bearer {authenticated_user_token}"
        }
    )
    assert response.status_code == 200
    data = response.json()
    # Ajuste na asserção: verificar o número exato de pedidos criados neste teste para o usuário logado
    # Como limpamos o DB por teste/fixture, só devem existir os pedidos criados acima para o testuser
    assert data["total"] == 2
    assert len(data["orders"]) == 2

# Teste para obter um pedido por ID
@pytest.mark.asyncio
async def test_get_order_by_id(client: AsyncClient, authenticated_user_token: str, test_products: list[dict]): # test_products agora retorna dicts
    product_data = test_products[0]
    order_data = {"items": [{"product_id": product_data["id"], "quantity": 1}]}

    # Criar o pedido usando a sessão direta para facilitar a obtenção do ID
    async with TestingSessionLocal() as db:
        from src.services.order_service import create_order as create_order_service
        from sqlalchemy import select
        user = (await db.execute(select(User).filter(User.username == "testuser"))).scalar_one_or_none()
        assert user is not None

        order = await create_order_service(db=db, order_data=OrderCreate(**order_data), user_id=user.id)
        await db.commit()
        await db.refresh(order)
        order_id = order.id

    # Obter o pedido pelo ID usando o cliente HTTP
    get_response = await client.get(
        f"/api/v1/orders/{order_id}",
        headers={
            "Authorization": f"Bearer {authenticated_user_token}"
        }
    )
    assert get_response.status_code == 200
    order_response = get_response.json()
    assert order_response["id"] == order_id
    assert len(order_response["items"]) == 1
    assert order_response["items"][0]["product_id"] == product_data["id"]
    assert order_response["items"][0]["quantity"] == 1

# Teste para obter pedido não encontrado
@pytest.mark.asyncio
async def test_get_order_by_id_not_found(client: AsyncClient, authenticated_user_token: str):
    response = await client.get(
        "/api/v1/orders/99999", # ID que não existe
        headers={
            "Authorization": f"Bearer {authenticated_user_token}"
        }
    )
    assert response.status_code == 404
    assert "Pedido não encontrado" in response.json()["detail"]

# Teste para obter pedido de outro usuário
@pytest.mark.asyncio
async def test_get_order_by_id_other_user(client: AsyncClient): # Remover dependência de db
     # Obter sessão diretamente da TestingSessionLocal
    async with TestingSessionLocal() as db:
        # Criar o primeiro usuário e obter token (manualmente nesta função de teste)
        user1_data = UserCreate(username="testuser1", email="test1@example.com", password="testpassword1")
        user1 = await create_user(db=db, user=user1_data)
        await db.commit()
        await db.refresh(user1)
        token_response1 = await client.post("/api/v1/auth/token", data={"username": "testuser1", "password": "testpassword1"})
        assert token_response1.status_code == 200
        token_data1 = token_response1.json()
        token1 = token_data1["access_token"]

        # Criar um segundo usuário
        user2_data = UserCreate(username="testuser2", email="test2@example.com", password="testpassword2")
        user2 = await create_user(db=db, user=user2_data)
        await db.commit()
        await db.refresh(user2)

        # Autenticar o segundo usuário para criar um pedido para ele
        token_response2 = await client.post("/api/v1/auth/token", data={"username": "testuser2", "password": "testpassword2"})
        assert token_response2.status_code == 200
        token_data2 = token_response2.json()
        token2 = token_data2["access_token"]

        # Criar um produto de teste (precisa estar no DB)
        from src.services.product_service import create_product as create_product_service
        product_data = ProductCreate(name="Produto Pedido", description="Desc", price=15.0, stock_quantity=10, barcode="orderprod1", section="Geral", expiration_date="2025-12-31", images=[], status=ProductStatusEnum.in_stock)
        product = await create_product_service(db=db, product_data=product_data)
        await db.commit()
        await db.refresh(product)

        # Criar um pedido com o segundo usuário
        from src.services.order_service import create_order as create_order_service
        order_data = {"items": [{"product_id": product.id, "quantity": 1}]}
        create_response2 = await client.post(
            "/api/v1/orders/",
            json=order_data,
            headers={
                "Authorization": f"Bearer {token2}"
            }
        )
        assert create_response2.status_code == 201
        order_id_user2 = create_response2.json()["id"]

        # Tentar obter o pedido do segundo usuário com o token do primeiro usuário
        get_response = await client.get(
            f"/api/v1/orders/{order_id_user2}",
            headers={
                "Authorization": f"Bearer {token1}"
            }
        )
        assert get_response.status_code == 404 # Deve retornar 404 porque o pedido não pertence a este usuário
        assert "Pedido não encontrado" in get_response.json()["detail"]

# Teste para atualizar um pedido (apenas status permitido por enquanto)
@pytest.mark.asyncio
async def test_update_order(client: AsyncClient, authenticated_user_token: str, test_products: list[dict]): # test_products agora retorna dicts
    product_data = test_products[0]
    order_data = {"items": [{"product_id": product_data["id"], "quantity": 1}]}

    # Criar o pedido usando a sessão direta para facilitar a obtenção do ID
    async with TestingSessionLocal() as db:
        from src.services.order_service import create_order as create_order_service
        from sqlalchemy import select
        user = (await db.execute(select(User).filter(User.username == "testuser"))).scalar_one_or_none()
        assert user is not None

        order = await create_order_service(db=db, order_data=OrderCreate(**order_data), user_id=user.id)
        await db.commit()
        await db.refresh(order)
        order_id = order.id

    # Atualizar o status do pedido usando o cliente HTTP
    update_data = {"status": "completed"}
    update_response = await client.put(
        f"/api/v1/orders/{order_id}",
        json=update_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token}"
        }
    )
    assert update_response.status_code == 200
    updated_order = update_response.json()
    assert updated_order["id"] == order_id
    assert updated_order["status"] == "completed"

# Teste para atualizar pedido não encontrado
@pytest.mark.asyncio
async def test_update_order_not_found(client: AsyncClient, authenticated_user_token: str):
    update_data = {"status": "completed"}
    response = await client.put(
        "/api/v1/orders/99999", # ID que não existe
        json=update_data,
        headers={
            "Authorization": f"Bearer {authenticated_user_token}"
        }
    )
    assert response.status_code == 404
    assert "Pedido não encontrado" in response.json()["detail"]

# Teste para atualizar pedido de outro usuário
@pytest.mark.asyncio
async def test_update_order_other_user(client: AsyncClient): # Remover dependência de db
     # Obter sessão diretamente da TestingSessionLocal
    async with TestingSessionLocal() as db:
         # Criar o primeiro usuário e obter token (manualmente nesta função de teste)
        user1_data = UserCreate(username="testuser1", email="test1@example.com", password="testpassword1")
        user1 = await create_user(db=db, user=user1_data)
        await db.commit()
        await db.refresh(user1)
        token_response1 = await client.post("/api/v1/auth/token", data={"username": "testuser1", "password": "testpassword1"})
        assert token_response1.status_code == 200
        token_data1 = token_response1.json()
        token1 = token_data1["access_token"]

        # Criar um segundo usuário
        user2_data = UserCreate(username="testuser2", email="test2@example.com", password="testpassword2")
        user2 = await create_user(db=db, user=user2_data)
        await db.commit()
        await db.refresh(user2)

        # Autenticar o segundo usuário para criar um pedido para ele
        token_response2 = await client.post("/api/v1/auth/token", data={"username": "testuser2", "password": "testpassword2"})
        assert token_response2.status_code == 200
        token_data2 = token_response2.json()
        token2 = token_data2["access_token"]

        # Criar um produto de teste (precisa estar no DB)
        from src.services.product_service import create_product as create_product_service
        product_data = ProductCreate(name="Produto Pedido Update", description="Desc Update", price=25.0, stock_quantity=20, barcode="orderprodupdate", section="Geral", expiration_date="2025-12-31", images=[], status=ProductStatusEnum.in_stock)
        product = await create_product_service(db=db, product_data=product_data)
        await db.commit()
        await db.refresh(product)

        # Criar um pedido com o segundo usuário
        from src.services.order_service import create_order as create_order_service
        order_data = {"items": [{"product_id": product.id, "quantity": 1}]}
        create_response2 = await client.post(
            "/api/v1/orders/",
            json=order_data,
            headers={
                "Authorization": f"Bearer {token2}"
            }
        )
        assert create_response2.status_code == 201
        order_id_user2 = create_response2.json()["id"]

        # Tentar atualizar o pedido do segundo usuário com o token do primeiro usuário
        update_data = {"status": "cancelled"}
        update_response = await client.put(
            f"/api/v1/orders/{order_id_user2}",
            json=update_data,
            headers={
                "Authorization": f"Bearer {token1}"
            }
        )
        assert update_response.status_code == 404 # Deve retornar 404 porque o pedido não pertence a este usuário
        assert "Pedido não encontrado" in update_response.json()["detail"]

# Teste para deletar um pedido
@pytest.mark.asyncio
async def test_delete_order(client: AsyncClient, authenticated_user_token: str, test_products: list[dict]): # test_products agora retorna dicts
    product_data = test_products[0]
    initial_stock = product_data["stock_quantity"] # Obter estoque inicial
    order_data = {"items": [{"product_id": product_data["id"], "quantity": 1}]}

    # Criar o pedido usando a sessão direta para facilitar a obtenção do ID
    async with TestingSessionLocal() as db:
        from src.services.order_service import create_order as create_order_service
        from sqlalchemy import select
        user = (await db.execute(select(User).filter(User.username == "testuser"))).scalar_one_or_none()
        assert user is not None

        order = await create_order_service(db=db, order_data=OrderCreate(**order_data), user_id=user.id)
        await db.commit()
        await db.refresh(order)
        order_id = order.id

    # Deletar o pedido usando o cliente HTTP
    delete_response = await client.delete(
        f"/api/v1/orders/{order_id}",
        headers={
            "Authorization": f"Bearer {authenticated_user_token}"
        }
    )
    assert delete_response.status_code == 204 # No Content

    # Verificar se o pedido foi realmente deletado usando o cliente HTTP
    get_response = await client.get(
        f"/api/v1/orders/{order_id}",
        headers={
            "Authorization": f"Bearer {authenticated_user_token}"
        }
    )
    assert get_response.status_code == 404

    # Verificar se o estoque foi revertido (precisa ler o produto do DB)
    async with TestingSessionLocal() as db:
        from sqlalchemy import select
        updated_product = (await db.execute(select(Product).filter(Product.id == product_data["id"]))).scalar_one_or_none()
        assert updated_product is not None
        assert updated_product.stock_quantity == initial_stock # Estoque deve voltar ao valor inicial

# Teste para deletar pedido não encontrado
@pytest.mark.asyncio
async def test_delete_order_not_found(client: AsyncClient, authenticated_user_token: str):
    response = await client.delete(
        "/api/v1/orders/99999", # ID que não existe
        headers={
            "Authorization": f"Bearer {authenticated_user_token}"
        }
    )
    assert response.status_code == 404
    assert "Pedido não encontrado" in response.json()["detail"]

# Teste para deletar pedido de outro usuário
@pytest.mark.asyncio
async def test_delete_order_other_user(client: AsyncClient): # Remover dependência de db
    # Obter sessão diretamente da TestingSessionLocal
    async with TestingSessionLocal() as db:
        # Criar o primeiro usuário e obter token (manualmente nesta função de teste)
        user1_data = UserCreate(username="testuser1", email="test1@example.com", password="testpassword1")
        user1 = await create_user(db=db, user=user1_data)
        await db.commit()
        await db.refresh(user1)
        token_response1 = await client.post("/api/v1/auth/token", data={"username": "testuser1", "password": "testpassword1"})
        assert token_response1.status_code == 200
        token_data1 = token_response1.json()
        token1 = token_data1["access_token"]

        # Criar um segundo usuário
        user2_data = UserCreate(username="testuser2", email="test2@example.com", password="testpassword2")
        user2 = await create_user(db=db, user=user2_data)
        await db.commit()
        await db.refresh(user2)

        # Autenticar o segundo usuário para criar um pedido para ele
        token_response2 = await client.post("/api/v1/auth/token", data={"username": "testuser2", "password": "testpassword2"})
        assert token_response2.status_code == 200
        token_data2 = token_response2.json()
        token2 = token_data2["access_token"]

        # Criar um produto de teste (precisa estar no DB)
        from src.services.product_service import create_product as create_product_service
        product_data = ProductCreate(name="Produto Pedido Delete", description="Desc Delete", price=35.0, stock_quantity=30, barcode="orderproddelete", section="Geral", expiration_date="2025-12-31", images=[], status=ProductStatusEnum.in_stock)
        product = await create_product_service(db=db, product_data=product_data)
        await db.commit()
        await db.refresh(product)

        # Criar um pedido com o segundo usuário
        from src.services.order_service import create_order as create_order_service
        order_data = {"items": [{"product_id": product.id, "quantity": 1}]}
        create_response2 = await client.post(
            "/api/v1/orders/",
            json=order_data,
            headers={
                "Authorization": f"Bearer {token2}"
            }
        )
        assert create_response2.status_code == 201
        order_id_user2 = create_response2.json()["id"]

        # Tentar deletar o pedido do segundo usuário com o token do primeiro usuário
        delete_response = await client.delete(
            f"/api/v1/orders/{order_id_user2}",
            headers={
                "Authorization": f"Bearer {token1}"
            }
        )
        assert delete_response.status_code == 404 # Deve retornar 404 porque o pedido não pertence a este usuário
        assert "Pedido não encontrado" in delete_response.json()["detail"] 