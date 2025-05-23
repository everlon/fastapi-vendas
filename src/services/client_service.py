from fastapi import HTTPException
from http import HTTPStatus
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_
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
    existing_client_by_email = None
    existing_client_by_cpf = None

    if client_data.email:
        result_email = await db.execute(select(Client).where(Client.email == client_data.email))
        existing_client_by_email = result_email.scalar_one_or_none()

    if client_data.cpf:
        result_cpf = await db.execute(select(Client).where(Client.cpf == client_data.cpf))
        existing_client_by_cpf = result_cpf.scalar_one_or_none()

    if existing_client_by_email:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Email já cadastrado.")
    if existing_client_by_cpf:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="CPF já cadastrado.")

    new_client = Client(
        name=client_data.name,
        email=client_data.email,
        phone=client_data.phone,
        cpf=client_data.cpf,
        # Campos de endereço
        street=client_data.address.street,
        number=client_data.address.number,
        complement=client_data.address.complement,
        neighborhood=client_data.address.neighborhood,
        city=client_data.address.city,
        state=client_data.address.state,
        zip_code=client_data.address.zip_code
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

    if client_data.email is not None and client_data.email != db_client.email:
        result_unique_email = await db.execute(select(Client).where(Client.email == client_data.email, Client.id != id))
        existing_client_unique_email = result_unique_email.scalar_one_or_none()
        if existing_client_unique_email:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Email já cadastrado.")
        db_client.email = client_data.email
        
    if client_data.cpf is not None and client_data.cpf != db_client.cpf:
        result_unique_cpf = await db.execute(select(Client).where(Client.cpf == client_data.cpf, Client.id != id))
        existing_client_unique_cpf = result_unique_cpf.scalar_one_or_none()
        if client_data.cpf is not None and existing_client_unique_cpf:
             raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="CPF já cadastrado.")
        db_client.cpf = client_data.cpf

    if client_data.name is not None:
        db_client.name = client_data.name
    if client_data.phone is not None:
        db_client.phone = client_data.phone
    if client_data.address is not None:
        db_client.street = client_data.address.street
        db_client.number = client_data.address.number
        db_client.complement = client_data.address.complement
        db_client.neighborhood = client_data.address.neighborhood
        db_client.city = client_data.address.city
        db_client.state = client_data.address.state
        db_client.zip_code = client_data.address.zip_code
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
