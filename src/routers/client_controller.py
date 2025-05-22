from http import HTTPStatus
from typing_extensions import List
from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy.orm import Session
from database import get_db

from src.services.client_service import (
    create_client,
    list_clients,
    get_client_by_id,
    update_client,
    delete_client)

from src.schemas.client import (
    ClientCreate,
    ClientResponse,
    ClientUpdate,
    PaginatedClientResponse
)

from typing import Annotated
from auth import User, get_current_active_user


router = APIRouter(prefix="/api/v1/clients", tags=["clients"])


@router.post("/", status_code=HTTPStatus.CREATED, response_model=ClientResponse)
async def create_client_endpoint(client: ClientCreate, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    Endpoint para criar um novo Cliente.
    """
    return await create_client(client, db)


@router.get("/", status_code=HTTPStatus.OK, response_model=PaginatedClientResponse)
async def list_clients_endpoint(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(10, ge=1, le=100, description="Número de itens por página"),
    search: str = Query(None, description="Filtrar por busca em nome ou email do cliente")
    , user: User = Depends(get_current_active_user)):
    """
    Endpoint para listar Clientes com paginação e busca.
    """
    clients, total = await list_clients(
        db,
        page=page,
        page_size=page_size,
        search=search)

    response_data = {
        "clients": clients,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

    return response_data


@router.get("/{id}", status_code=HTTPStatus.OK, response_model=ClientResponse)
async def get_client_by_id_endpoint(id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    Endpoint para obter detalhes de um Cliente por ID.
    """
    client = await get_client_by_id(id, db)

    if not client:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cliente não encontrado")

    return client


@router.put("/{id}", status_code=HTTPStatus.OK, response_model=ClientResponse)
async def update_client_endpoint(id: int, client_data: ClientUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    Endpoint para atualizar um Cliente existente.
    """
    updated_client = await update_client(id, client_data, db)

    return updated_client


@router.delete("/{id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_client_endpoint(id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    Endpoint para excluir um Cliente.
    """
    await delete_client(id, db)

    return True
