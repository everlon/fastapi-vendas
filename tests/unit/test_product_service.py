import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from http import HTTPStatus
from datetime import datetime

from src.services.product_service import (
    create_product,
    get_product_by_id,
    update_product,
    delete_product,
    list_products
)
from src.models.product import Product
from src.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductStatusEnum
)

@pytest.fixture
def mock_db():
    """Fixture que fornece uma sessão de banco de dados mockada."""
    db = AsyncMock(spec=AsyncSession)
    return db

@pytest.fixture
def sample_product_data():
    """Fixture que fornece dados de exemplo para criação de produto."""
    return ProductCreate(
        name="Produto Teste",
        description="Descrição do produto teste",
        price=10.0,
        stock_quantity=100,
        barcode="123456789012",
        section="Teste",
        expiration_date="2025-12-31",
        images=["http://example.com/img1.jpg"],
        status=ProductStatusEnum.in_stock
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
        expiration_date=datetime(2025, 12, 31),
        images=["http://example.com/img1.jpg"],
        status=ProductStatusEnum.in_stock,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@pytest.mark.asyncio
async def test_create_product_success(mock_db, sample_product_data):
    """Testa a criação bem-sucedida de um produto."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    mock_product_obj = Product(
        id=1,
        name=sample_product_data.name,
        description=sample_product_data.description,
        price=sample_product_data.price,
        stock_quantity=sample_product_data.stock_quantity,
        barcode=sample_product_data.barcode,
        section=sample_product_data.section,
        expiration_date=datetime(2025, 12, 31),
        images=sample_product_data.images,
        status=sample_product_data.status
    )
    async def mock_refresh(product):
        product.id = mock_product_obj.id
        return product
    mock_db.refresh.side_effect = mock_refresh
    result = await create_product(sample_product_data, mock_db)
    assert result.name == sample_product_data.name
    assert result.price == sample_product_data.price
    assert result.barcode == sample_product_data.barcode
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

@pytest.mark.asyncio
async def test_create_product_duplicate_barcode(mock_db, sample_product_data):
    """Testa a criação de produto com código de barras duplicado."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = Product(
        id=2,
        barcode=sample_product_data.barcode
    )
    mock_db.execute.return_value = mock_result
    with pytest.raises(HTTPException) as exc_info:
        await create_product(sample_product_data, mock_db)
    assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
    assert "Código de barras já cadastrado" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_get_product_by_id_success(mock_db, mock_product):
    """Testa a busca bem-sucedida de produto por ID."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    mock_db.execute.return_value = mock_result
    result = await get_product_by_id(1, mock_db)
    assert result == mock_product
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_product_by_id_not_found(mock_db):
    """Testa a busca de produto por ID inexistente."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    with pytest.raises(HTTPException) as exc_info:
        await get_product_by_id(999, mock_db)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
    assert "Produto não encontrado" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_update_product_success(mock_db, mock_product):
    """Testa a atualização bem-sucedida de um produto."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    mock_db.execute.return_value = mock_result
    update_data = ProductUpdate(
        name="Produto Atualizado",
        price=15.0
    )
    async def mock_refresh(product):
        product.name = update_data.name
        product.price = update_data.price
        return product
    mock_db.refresh.side_effect = mock_refresh
    result = await update_product(1, update_data, mock_db)
    assert result.name == "Produto Atualizado"
    assert result.price == 15.0
    assert result.barcode == mock_product.barcode
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

@pytest.mark.asyncio
async def test_update_product_not_found(mock_db):
    """Testa a atualização de produto inexistente."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    update_data = ProductUpdate(name="Produto Atualizado")
    with pytest.raises(HTTPException) as exc_info:
        await update_product(999, update_data, mock_db)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
    assert "Produto não encontrado" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_delete_product_success(mock_db, mock_product):
    """Testa a exclusão bem-sucedida de um produto."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    mock_db.execute.return_value = mock_result
    await delete_product(1, mock_db)
    mock_db.delete.assert_called_once_with(mock_product)
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_delete_product_not_found(mock_db):
    """Testa a exclusão de produto inexistente."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    with pytest.raises(HTTPException) as exc_info:
        await delete_product(999, mock_db)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
    assert "Produto não encontrado" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_list_products_with_filters(mock_db, mock_product):
    """Testa a listagem de produtos com filtros."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_product]
    mock_result.scalar_one.return_value = 1
    mock_db.execute.return_value = mock_result
    products, total = await list_products(
        mock_db,
        page=1,
        page_size=10,
        search="Teste",
        status="em estoque",
        section="Teste",
        min_price=5.0,
        max_price=20.0
    )
    assert len(products) == 1
    assert total == 1
    assert products[0] == mock_product
    mock_db.execute.assert_called() 