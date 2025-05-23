from fastapi import HTTPException
from http import HTTPStatus
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from src.models.client import Client
from src.schemas.client import (
    ClientCreate,
    ClientResponse,
    ClientUpdate
)


async def create_client(client_data: ClientCreate, db: AsyncSession) -> Client:
    result = await db.execute(select(Client).where(Client.email == client_data.email))
    existing_client = result.scalar_one_or_none()
    if existing_client:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Email já cadastrado.")

    new_client = Client(
        name = client_data.name,
        email = client_data.email,
        phone = client_data.phone,
        address = client_data.address
    )

    db.add(new_client)
    await db.commit()
    await db.refresh(new_client)

    return new_client


async def list_clients(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    search: str = None
):
    query = select(Client)

    if search:
        query = query.where(or_(
            Client.name.ilike(f"%{search}%"),
            Client.email.ilike(f"%{search}%")
        ))

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    clients_result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    clients = clients_result.scalars().all()

    return clients, total


async def get_client_by_id(id: int, db: AsyncSession) -> Client:
    result = await db.execute(select(Client).where(Client.id == id))
    return result.scalar_one_or_none()


async def update_client(id: int, client_data: ClientUpdate, db: AsyncSession) -> Client:
    result = await db.execute(select(Client).where(Client.id == id))
    db_client = result.scalar_one_or_none()

    if not db_client:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cliente não encontrado")

    if client_data.name is not None:
        db_client.name = client_data.name
    if client_data.email is not None and client_data.email != db_client.email:
        result_unique = await db.execute(select(Client).where(Client.email == client_data.email, Client.id != id))
        existing_client_unique = result_unique.scalar_one_or_none()
        if existing_client_unique:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Email já cadastrado.")
        db_client.email = client_data.email
    if client_data.phone is not None:
        db_client.phone = client_data.phone
    if client_data.address is not None:
        db_client.address = client_data.address
    if client_data.active is not None:
        db_client.active = client_data.active

    db_client.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(db_client)

    return db_client


async def delete_client(id: int, db: AsyncSession) -> None:
    result = await db.execute(select(Client).where(Client.id == id))
    db_client = result.scalar_one_or_none()

    if not db_client:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cliente não encontrado")

    await db.delete(db_client)
    await db.commit()
