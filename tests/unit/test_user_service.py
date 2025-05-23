import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from http import HTTPStatus

from src.services.user_service import (
    get_password_hash,
    verify_password,
    get_user_by_username,
    get_user_by_email,
    create_user
)
from src.models.user import User
from src.schemas.user import UserCreate

@pytest.fixture
def mock_db():
    """Fixture que fornece uma sessão de banco de dados mockada."""
    db = AsyncMock(spec=AsyncSession)
    return db

@pytest.fixture
def sample_user_data():
    """Fixture que fornece dados de exemplo para criação de usuário."""
    return UserCreate(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        full_name="Test User",
        is_admin=False
    )

def test_get_password_hash():
    """Testa se a função de hash de senha gera um hash diferente da senha original."""
    password = "testpass123"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert isinstance(hashed, str)
    assert len(hashed) > len(password)

def test_verify_password():
    """Testa se a verificação de senha funciona corretamente."""
    password = "testpass123"
    hashed = get_password_hash(password)
    
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpass", hashed) is False

@pytest.mark.asyncio
async def test_get_user_by_username_existing(mock_db):
    """Testa a busca de usuário por username quando o usuário existe."""
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashedpass",
        is_admin=False
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_result
    
    result = await get_user_by_username(mock_db, "testuser")
    
    assert result == mock_user
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_by_username_not_found(mock_db):
    """Testa a busca de usuário por username quando o usuário não existe."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    result = await get_user_by_username(mock_db, "nonexistent")
    
    assert result is None
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_by_email_existing(mock_db):
    """Testa a busca de usuário por email quando o usuário existe."""
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashedpass",
        is_admin=False
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_result
    
    result = await get_user_by_email(mock_db, "test@example.com")
    
    assert result == mock_user
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_by_email_none(mock_db):
    """Testa a busca de usuário por email quando o email é None."""
    result = await get_user_by_email(mock_db, None)
    assert result is None
    mock_db.execute.assert_not_called()

@pytest.mark.asyncio
async def test_create_user_success(mock_db, sample_user_data):
    """Testa a criação bem-sucedida de um usuário."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    mock_user = User(
        id=1,
        username=sample_user_data.username,
        email=sample_user_data.email,
        hashed_password="hashedpass",
        is_admin=sample_user_data.is_admin
    )
    
    async def mock_refresh(user):
        user.id = mock_user.id
        user.hashed_password = mock_user.hashed_password
        return user
    
    mock_db.refresh.side_effect = mock_refresh
    
    result = await create_user(mock_db, sample_user_data)
    
    assert result.username == sample_user_data.username
    assert result.email == sample_user_data.email
    assert result.is_admin == sample_user_data.is_admin
    assert result.hashed_password != sample_user_data.password  # Senha deve estar hasheada
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

@pytest.mark.asyncio
async def test_create_user_duplicate(mock_db, sample_user_data):
    """Testa a criação de usuário com dados duplicados."""
    mock_db.commit.side_effect = IntegrityError(None, None, None)
    
    with pytest.raises(HTTPException) as exc_info:
        await create_user(mock_db, sample_user_data)
    
    assert exc_info.value.status_code == HTTPStatus.CONFLICT
    assert "Nome de usuário ou email já cadastrado" in str(exc_info.value.detail)
    mock_db.rollback.assert_called_once() 