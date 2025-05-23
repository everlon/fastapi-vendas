from operator import or_
from fastapi import HTTPException
from http import HTTPStatus
from datetime import datetime

from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from src.models.product import Product
from src.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductStatusEnum,
    ProductResponse,
    ProductUpdate)


status_map = {
    "em estoque": ProductStatusEnum.in_stock,
    "em reposição": ProductStatusEnum.restocking,
    "em falta": ProductStatusEnum.out_of_stock,
}


async def map_status(status_str: str) -> ProductStatusEnum:
    status = status_map.get(status_str)

    if not status:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Status inválido.")

    return status


async def create_product(product_data: ProductCreate, db: AsyncSession) -> Product:
    status = await map_status(product_data.status.value)

    # Verifica unicidade do código de barras
    result = await db.execute(select(Product).where(Product.barcode == product_data.barcode))
    existing_product = result.scalar_one_or_none()
    if existing_product:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Código de barras já cadastrado.")

    new_product = Product(
        name = product_data.name,
        description = product_data.description,
        price = product_data.price,
        status = status,
        stock_quantity = product_data.stock_quantity,
        barcode = product_data.barcode,
        section = product_data.section,
        expiration_date = product_data.expiration_date,
        images = product_data.images
    )

    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)

    return new_product


async def list_products(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    search: str = None,
    status: str = None,
    section: str = None,
    min_price: float = None,
    max_price: float = None
):
    query = select(Product)

    if search:
        query = query.where(or_(
            Product.name.ilike(f"%{search}%"),
            Product.description.ilike(f"%{search}%")
        ))

    if status:
        status_enum = await map_status(status)
        query = query.where(Product.status == status_enum)

    if section:
        query = query.where(Product.section.ilike(f"%{section}%"))

    if min_price is not None:
        query = query.where(Product.price >= min_price)

    if max_price is not None:
        query = query.where(Product.price <= max_price)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    products_result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    products = products_result.scalars().all()

    return products, total


async def get_product_by_id(id: int, db: AsyncSession) -> Product:
    """
    Obtém um produto pelo seu ID.
    """
    result = await db.execute(select(Product).where(Product.id == id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Produto não encontrado")
    return product


async def update_product(id: int, product_data: ProductUpdate, db: AsyncSession) -> Product:
    result = await db.execute(select(Product).where(Product.id == id))
    db_product = result.scalar_one_or_none()

    if not db_product:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Produto não encontrado")

    if product_data.name is not None:
        db_product.name = product_data.name
    if product_data.description is not None:
        db_product.description = product_data.description
    if product_data.price is not None:
        db_product.price = product_data.price
    if product_data.status is not None:
        db_product.status = product_data.status
    if product_data.stock_quantity is not None:
        db_product.stock_quantity = product_data.stock_quantity
    if product_data.barcode is not None and product_data.barcode != db_product.barcode:
        # Verifica unicidade do código de barras (agora assíncrono)
        result_unique = await db.execute(select(Product).where(Product.barcode == product_data.barcode, Product.id != id))
        existing_product_unique = result_unique.scalar_one_or_none()
        if existing_product_unique:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Código de barras já cadastrado.")
        db_product.barcode = product_data.barcode
    if product_data.section is not None:
        db_product.section = product_data.section
    if product_data.expiration_date is not None:
        db_product.expiration_date = product_data.expiration_date
    if product_data.images is not None:
        db_product.images = product_data.images

    db_product.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(db_product)

    return db_product

async def delete_product(id: int, db: AsyncSession) -> None:
    result = await db.execute(select(Product).where(Product.id == id))
    db_product = result.scalar_one_or_none()

    if not db_product:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Produto não encontrado")

    await db.delete(db_product)
    await db.commit()
