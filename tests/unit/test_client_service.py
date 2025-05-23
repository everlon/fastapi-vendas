import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from http import HTTPStatus
from datetime import datetime

from src.services.client_service import (
    create_client,
    get_client_by_id,
    update_client,
    delete_client,
    list_clients
)
from src.models.client import Client
from src.schemas.client import ClientCreate, ClientUpdate, AddressSchema

@pytest.fixture
def mock_db():
    """Fixture que fornece uma sessão de banco de dados mockada."""
    db = AsyncMock(spec=AsyncSession)
    return db

@pytest.fixture
def sample_client_data():
    """Fixture que fornece dados de exemplo para criação de cliente."""
    return ClientCreate(
        name="Cliente Teste",
        email="cliente@teste.com",
        phone="11999998888",
        cpf="52998224725",
        address=AddressSchema(
            street="Rua Teste",
            number="123",
            complement="Apto 1",
            neighborhood="Centro",
            city="São Paulo",
            state="SP",
            zip_code="01234567"
        )
    )

@pytest.fixture
def mock_client():
    """Fixture que fornece um cliente mockado."""
    return Client(
        id=1,
        name="Cliente Teste",
        email="cliente@teste.com",
        phone="11999998888",
        cpf="52998224725",
        street="Rua Teste",
        number="123",
        complement="Apto 1",
        neighborhood="Centro",
        city="São Paulo",
        state="SP",
        zip_code="01234567",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@pytest.mark.asyncio
async def test_create_client_success(mock_db, sample_client_data):
    """Testa a criação bem-sucedida de um cliente."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.side_effect = [None, None]
    mock_db.execute.return_value = mock_result
    mock_client_obj = Client(
        id=1,
        name=sample_client_data.name,
        email=sample_client_data.email,
        phone=sample_client_data.phone,
        cpf=sample_client_data.cpf,
        street=sample_client_data.address.street,
        number=sample_client_data.address.number,
        complement=sample_client_data.address.complement,
        neighborhood=sample_client_data.address.neighborhood,
        city=sample_client_data.address.city,
        state=sample_client_data.address.state,
        zip_code=sample_client_data.address.zip_code
    )
    async def mock_refresh(client):
        client.id = mock_client_obj.id
        return client
    mock_db.refresh.side_effect = mock_refresh
    result = await create_client(sample_client_data, mock_db)
    assert result.name == sample_client_data.name
    assert result.email == sample_client_data.email
    assert result.cpf == sample_client_data.cpf
    assert result.street == sample_client_data.address.street
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

@pytest.mark.asyncio
async def test_create_client_duplicate_email(mock_db, sample_client_data):
    """Testa a criação de cliente com email duplicado."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = Client(
        id=2,
        email=sample_client_data.email
    )
    mock_db.execute.return_value = mock_result
    with pytest.raises(HTTPException) as exc_info:
        await create_client(sample_client_data, mock_db)
    assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
    assert "Email já cadastrado" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_create_client_duplicate_cpf(mock_db, sample_client_data):
    """Testa a criação de cliente com CPF duplicado."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.side_effect = [
        None,
        Client(id=2, cpf=sample_client_data.cpf)
    ]
    mock_db.execute.return_value = mock_result
    with pytest.raises(HTTPException) as exc_info:
        await create_client(sample_client_data, mock_db)
    assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
    assert "CPF já cadastrado" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_get_client_by_id_success(mock_db, mock_client):
    """Testa a busca bem-sucedida de cliente por ID."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_client
    mock_db.execute.return_value = mock_result
    result = await get_client_by_id(1, mock_db)
    assert result == mock_client
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_client_by_id_not_found(mock_db):
    """Testa a busca de cliente por ID inexistente."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    result = await get_client_by_id(999, mock_db)
    assert result is None

@pytest.mark.asyncio
async def test_update_client_success(mock_db, mock_client):
    """Testa a atualização bem-sucedida de um cliente."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.side_effect = [mock_client, None]
    mock_db.execute.return_value = mock_result
    update_data = ClientUpdate(
        name="Cliente Atualizado",
        email="novo@email.com"
    )
    async def mock_refresh(client):
        client.name = update_data.name
        client.email = update_data.email
        return client
    mock_db.refresh.side_effect = mock_refresh
    result = await update_client(1, update_data, mock_db)
    assert result.name == "Cliente Atualizado"
    assert result.email == "novo@email.com"
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

@pytest.mark.asyncio
async def test_update_client_not_found(mock_db):
    """Testa a atualização de cliente inexistente."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    update_data = ClientUpdate(name="Cliente Atualizado")
    with pytest.raises(HTTPException) as exc_info:
        await update_client(999, update_data, mock_db)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
    assert "Cliente não encontrado" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_update_client_duplicate_email(mock_db, mock_client):
    """Testa a atualização de cliente com email já existente."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.side_effect = [
        mock_client,
        Client(id=2, email="novo@email.com")
    ]
    mock_db.execute.return_value = mock_result
    update_data = ClientUpdate(email="novo@email.com")
    with pytest.raises(HTTPException) as exc_info:
        await update_client(1, update_data, mock_db)
    assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
    assert "Email já cadastrado" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_delete_client_success(mock_db, mock_client):
    """Testa a exclusão bem-sucedida de um cliente."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_client
    mock_db.execute.return_value = mock_result
    await delete_client(1, mock_db)
    mock_db.delete.assert_called_once_with(mock_client)
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_delete_client_not_found(mock_db):
    """Testa a exclusão de cliente inexistente."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    with pytest.raises(HTTPException) as exc_info:
        await delete_client(999, mock_db)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
    assert "Cliente não encontrado" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_list_clients_with_filters(mock_db, mock_client):
    """Testa a listagem de clientes com filtros."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_client]
    mock_result.scalar_one.return_value = 1
    mock_db.execute.return_value = mock_result
    clients, total = await list_clients(
        mock_db,
        page=1,
        page_size=10,
        search="Teste"
    )
    assert len(clients) == 1
    assert total == 1
    assert clients[0] == mock_client
    mock_db.execute.assert_called() 