from fastapi.testclient import TestClient
# from sqlalchemy import create_engine # Remover importação síncrona
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession # Importar async
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI

from database import Base, get_db # Importar Base do seu models ou database
from src.models.order import Order, OrderItem # Importar modelos de Pedido
from src.models.product import Product # Precisamos do modelo de produto para criar produtos de teste
from src.models.user import User # Precisamos do modelo de usuário para criar um usuário de teste
from src.schemas.user import UserCreate
from src.services.user_service import get_password_hash

# Importar roteadores diretamente
from src.routers.auth_controller import router as auth_router
from src.routers.user_controller import router as user_router

# Configuração do banco de dados de teste (SQLite em memória - ASSÍNCRONO)
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine( # Usar create_async_engine
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker( # Usar sessionmaker assíncrono
    engine,
    class_=AsyncSession, # Usar AsyncSession
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sobrescrever get_db para os testes assíncronos
async def override_get_db(): # Tornar a dependência assíncrona
    async with TestingSessionLocal() as db:
        yield db

# Remover a criação síncrona das tabelas no setup do teste
# Base.metadata.create_all(bind=engine)


app = FastAPI()
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(user_router, prefix="/api/v1/users")

# Sobrescrever a dependência get_db com a versão assíncrona de teste
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# Função auxiliar para obter token de login (assíncrona)
async def login_token(username, password): # Tornar a função assíncrona
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": username,
            "password": password,
        }
    )
    assert response.status_code == 200
    token_data = response.json()
    return token_data["access_token"]

# --- Testes de Usuário ---

async def test_create_user():
    # Limpa o DB antes de cada teste de criação
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    user_data = {
        "username": "testuser",
        "password": "testpassword",
        "email": "test@example.com",
        "full_name": "Test User"
    }
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 201
    created_user = response.json()
    assert created_user["username"] == user_data["username"]
    assert created_user["email"] == user_data["email"]
    assert created_user["full_name"] == user_data["full_name"]
    assert "id" in created_user
    assert "hashed_password" not in created_user # A senha hashed não deve retornar na resposta

async def test_create_user_duplicate_username():
    # Limpa o DB e cria tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Cria um usuário inicial usando o endpoint assíncrono
    test_user_data = {"username": "duplicate", "password": "password"}
    client.post("/api/v1/users/", json=test_user_data)

    # Tenta criar outro com o mesmo username
    duplicate_user_data = {"username": "duplicate", "password": "anotherpassword"}
    response = client.post("/api/v1/users/", json=duplicate_user_data)
    assert response.status_code == 400
    assert response.json() == {"detail": "Username already registered"}

async def test_create_user_duplicate_email():
    # Limpa o DB e cria tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Cria um usuário inicial com email usando o endpoint assíncrono
    test_user_data = {"username": "user_with_email", "password": "password", "email": "duplicate@example.com"}
    client.post("/api/v1/users/", json=test_user_data)

    # Tenta criar outro com o mesmo email
    duplicate_email_data = {"username": "another_user", "password": "password", "email": "duplicate@example.com"}
    response = client.post("/api/v1/users/", json=duplicate_email_data)
    assert response.status_code == 400
    assert response.json() == {"detail": "Email already registered"}

async def test_read_users_me():
    # Limpa o DB e cria tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Cria um usuário para login usando o endpoint assíncrono
    user_data = {"username": "loginuser", "password": "loginpassword"}
    client.post("/api/v1/users/", json=user_data)

    # Obtém o token de login (função auxiliar agora assíncrona)
    token = await login_token(user_data["username"], user_data["password"])

    # Acessa o endpoint /me com o token
    response = client.get(
        "/api/v1/users/me/",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )
    assert response.status_code == 200
    user_info = response.json()
    assert user_info["username"] == user_data["username"]
    assert "id" in user_info

async def test_read_users_me_unauthenticated():
    # Limpa o DB antes de cada teste
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Tenta acessar /me sem token
    response = client.get("/api/v1/users/me/")
    assert response.status_code == 401
    # Corrigir a asserção para a mensagem de erro real (já feita)
    assert response.json() == {"detail": "Not authenticated"} 