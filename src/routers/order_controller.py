from fastapi import APIRouter, Depends, HTTPException, Query
from http import HTTPStatus
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db

from src.services.order_service import create_order, get_orders, get_order_by_id, update_order, delete_order # Importar funções de serviço
from src.schemas.order import OrderCreate, OrderResponse, OrderUpdate, PaginatedOrderResponse # Importar schemas

from auth import User, get_current_active_user # Para autenticação


router = APIRouter()


@router.post("/", status_code=HTTPStatus.CREATED, response_model=OrderResponse)
async def create_order_endpoint(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cria um novo pedido para o usuário autenticado.
    """
    # Chamar a função de serviço para criar o pedido
    new_order = await create_order(db=db, order_data=order_data, user_id=current_user.id)

    return new_order

# Endpoints para listar, obter, atualizar e deletar pedidos

@router.get("/", response_model=PaginatedOrderResponse)
async def list_orders_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, gt=0, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lista todos os pedidos do usuário autenticado com paginação.
    """
    orders, total_orders = await get_orders(db=db, skip=skip, limit=limit, user_id=current_user.id)
    return PaginatedOrderResponse(
        orders=orders,
        total=total_orders,
        page=skip // limit + 1 if limit > 0 else 1, # Calcular página atual
        page_size=limit,
        total_pages=(total_orders + limit - 1) // limit if limit > 0 else 0 # Calcular total de páginas
    )

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_by_id_endpoint(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtém um pedido específico pelo seu ID para o usuário autenticado.
    """
    order = await get_order_by_id(db=db, order_id=order_id)
    # Verificar se o pedido existe e se pertence ao usuário autenticado
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Pedido não encontrado")
    return order

@router.put("/{order_id}", response_model=OrderResponse)
async def update_order_endpoint(
    order_id: int,
    order_update_data: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Atualiza um pedido existente pelo seu ID para o usuário autenticado.
    Permite atualizar o status do pedido.
    """
    order = await get_order_by_id(db=db, order_id=order_id)
    # Verificar se o pedido existe e se pertence ao usuário autenticado
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Pedido não encontrado")

    # Chamar a função de serviço para atualizar o pedido
    updated_order = await update_order(db=db, order_id=order_id, order_update_data=order_update_data)
    # O serviço já valida se o pedido foi encontrado, mas verificamos novamente por segurança e para type hinting
    if not updated_order:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Pedido não encontrado durante a atualização") # Não deve acontecer se a verificação inicial passar

    return updated_order

@router.delete("/{order_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_order_endpoint(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Deleta um pedido existente pelo seu ID para o usuário autenticado.
    """
    order = await get_order_by_id(db=db, order_id=order_id)
    # Verificar se o pedido existe e se pertence ao usuário autenticado
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Pedido não encontrado")

    # Chamar a função de serviço para deletar o pedido
    await delete_order(db=db, order_id=order_id)
    # A função de serviço não precisa retornar o objeto deletado para este endpoint com status_code=NO_CONTENT

    return # Retornar None ou {} para 204 No Content 