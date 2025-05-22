from fastapi import HTTPException
from http import HTTPStatus
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

from src.models.client import Client
from src.schemas.client import (
    ClientCreate,
    ClientResponse,
    ClientUpdate
)


async def create_client(client_data: ClientCreate, db: Session) -> Client:
    # Verifica unicidade do email
    if db.query(Client).filter(Client.email == client_data.email).first():
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Email já cadastrado.")

    new_client = Client(
        name = client_data.name,
        email = client_data.email,
        phone = client_data.phone,
        address = client_data.address
    )

    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    return new_client


async def list_clients(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    search: str = None
):
    query = db.query(Client)

    if search:
        query = query.filter(or_(
            Client.name.ilike(f"%{search}%"),
            Client.email.ilike(f"%{search}%")
        ))

    total = query.count()
    clients = query.offset((page - 1) * page_size).limit(page_size).all()

    return clients, total


async def get_client_by_id(id: int, db: Session) -> Client:
    return db.query(Client).filter(Client.id == id).first()


async def update_client(id: int, client_data: ClientUpdate, db: Session) -> Client:
    db_client = db.query(Client).filter(Client.id == id).first()

    if not db_client:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Cliente não encontrado")

    if client_data.name is not None:
        db_client.name = client_data.name
    if client_data.email is not None and client_data.email != db_client.email:
         # Verifica unicidade do email
        if db.query(Client).filter(Client.email == client_data.email, Client.id != id).first():
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Email já cadastrado.")
        db_client.email = client_data.email
    if client_data.phone is not None:
        db_client.phone = client_data.phone
    if client_data.address is not None:
        db_client.address = client_data.address
    if client_data.active is not None:
        db_client.active = client_data.active

    db_client.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(db_client)

    return db_client


async def delete_client(id: int, db: Session) -> None:
    db_client = db.query(Client).filter(Client.id == id).first()

    if not db_client:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Cliente não encontrado")

    db.delete(db_client)
    db.commit()
