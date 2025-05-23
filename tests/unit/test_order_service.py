import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from http import HTTPStatus
from datetime import datetime

from src.services.order_service import (
    create_order,
    get_order_by_id,
    update_order,
    delete_order,
    get_orders
)
from src.models.order import Order, OrderItem
from src.models.product import Product
from src.models.client import Client
from src.models.user import User
from src.schemas.order import OrderCreate, OrderUpdate

@pytest.fixture
def mock_db():
    """Fixture que fornece uma sessão de banco de dados mockada."""
    db = AsyncMock(spec=AsyncSession)
    return db

@pytest.fixture
def mock_admin_user():
    """Fixture que fornece um usuário admin mockado."""
    return User(
        id=1,
        username="admin",
        email="admin@example.com",
        hashed_password="hashedpass",
        is_admin=True
    )

@pytest.fixture
def mock_client():
    """Fixture que fornece um cliente mockado."""
    return Client(
        id=1,
        name="Cliente Teste",
        email="cliente@teste.com",
        phone="11999998888",
        cpf="52998224725"
    )

@pytest.fixture
def mock_product():
    """Fixture que fornece um produto mockado."""
    return Product(
        id=1,
        name="Produto Teste",
        description="Descrição do produto teste",
        price=10.0,
        stock_quantity=100,
        barcode="123456789012",
        section="Teste",
        status="em estoque"
    )

@pytest.fixture
def mock_order(mock_client, mock_admin_user):
    """Fixture que fornece um pedido mockado."""
    return Order(
        id=1,
        client_id=mock_client.id,
        created_by_user_id=mock_admin_user.id,
        total=20.0,
        status="pendente",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        items=[
            OrderItem(
                id=1,
                product_id=1,
                quantity=2,
                price_at_time_of_purchase=10.0
            )
        ]
    )

@pytest.mark.asyncio
async def test_create_order_success(mock_db, mock_client, mock_product, mock_admin_user):
    """Testa a criação bem-sucedida de um pedido."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.side_effect = [mock_client, mock_product]
    mock_db.execute.return_value = mock_result
    
    order_data = OrderCreate(
        client_id=mock_client.id,
        items=[{"product_id": mock_product.id, "quantity": 2}]
    )
    
    # Configurar o mock do refresh para atualizar o pedido
    async def mock_refresh(order):
        order.id = 1
        order.total = 20.0
        order.status = "pendente"
        order.items = [
            OrderItem(
                id=1,
                product_id=mock_product.id,
                quantity=2,
                price_at_time_of_purchase=mock_product.price
            )
        ]
        return order
    
    mock_db.refresh.side_effect = mock_refresh
    
    result = await create_order(mock_db, order_data, mock_admin_user)
    
    assert result.client_id == mock_client.id
    assert result.created_by_user_id == mock_admin_user.id
    assert result.total == 20.0  # 2 * 10.0
    assert len(result.items) == 1
    assert result.items[0].quantity == 2
    assert result.items[0].price_at_time_of_purchase == 10.0
    
    # Verificar se o estoque foi atualizado
    assert mock_product.stock_quantity == 98  # 100 - 2
    mock_db.add.assert_called()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

@pytest.mark.asyncio
async def test_create_order_client_not_found(mock_db, mock_admin_user):
    """Testa a criação de pedido com cliente inexistente."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    order_data = OrderCreate(
        client_id=999,
        items=[{"product_id": 1, "quantity": 1}]
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_order(mock_db, order_data, mock_admin_user)
    
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
    assert "Cliente com ID 999 não encontrado" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_create_order_product_not_found(mock_db, mock_client, mock_admin_user):
    """Testa a criação de pedido com produto inexistente."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.side_effect = [mock_client, None]
    mock_db.execute.return_value = mock_result
    
    order_data = OrderCreate(
        client_id=mock_client.id,
        items=[{"product_id": 999, "quantity": 1}]
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_order(mock_db, order_data, mock_admin_user)
    
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
    assert "Produto com ID 999 não encontrado" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_create_order_insufficient_stock(mock_db, mock_client, mock_product, mock_admin_user):
    """Testa a criação de pedido com quantidade maior que o estoque disponível."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.side_effect = [mock_client, mock_product]
    mock_db.execute.return_value = mock_result
    
    order_data = OrderCreate(
        client_id=mock_client.id,
        items=[{"product_id": mock_product.id, "quantity": 101}]  # Mais que o estoque disponível
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_order(mock_db, order_data, mock_admin_user)
    
    assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
    assert "Estoque insuficiente" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_get_order_by_id_success(mock_db, mock_order, mock_admin_user):
    """Testa a busca bem-sucedida de pedido por ID."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_order
    mock_db.execute.return_value = mock_result
    
    result = await get_order_by_id(mock_db, mock_order.id, mock_admin_user)
    
    assert result == mock_order
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_order_by_id_not_found(mock_db, mock_admin_user):
    """Testa a busca de pedido por ID inexistente."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    result = await get_order_by_id(mock_db, 999, mock_admin_user)
    
    assert result is None

@pytest.mark.asyncio
async def test_update_order_success(mock_db, mock_order, mock_admin_user):
    """Testa a atualização bem-sucedida de um pedido."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_order
    mock_db.execute.return_value = mock_result
    
    update_data = OrderUpdate(status="processando")
    
    # Configurar o mock do refresh para atualizar o pedido
    async def mock_refresh(order):
        order.status = update_data.status
        return order
    
    mock_db.refresh.side_effect = mock_refresh
    
    result = await update_order(mock_db, mock_order.id, update_data, mock_admin_user)
    
    assert result.status == "processando"
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called()

@pytest.mark.asyncio
async def test_delete_order_success(mock_db, mock_order, mock_product, mock_admin_user):
    """Testa a exclusão bem-sucedida de um pedido."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.side_effect = [mock_order, mock_product]
    mock_db.execute.return_value = mock_result
    
    await delete_order(mock_db, mock_order.id, mock_admin_user)
    
    # Verificar se o pedido foi deletado
    mock_db.delete.assert_called_once_with(mock_order)
    
    # Verificar se o estoque foi restaurado
    assert mock_product.stock_quantity == 102  # 100 + 2 (quantidade do pedido)
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_get_orders_with_filters(mock_db, mock_order, mock_admin_user):
    """Testa a listagem de pedidos com filtros."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.unique.return_value.all.return_value = [mock_order]
    mock_result.scalar_one.return_value = 1  # Total count
    mock_db.execute.return_value = mock_result
    
    orders, total = await get_orders(
        mock_db,
        mock_admin_user,
        skip=0,
        limit=10,
        client_id=1,
        status="pendente",
        section="Teste",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31)
    )
    
    assert len(orders) == 1
    assert total == 1
    assert orders[0] == mock_order
    mock_db.execute.assert_called() 