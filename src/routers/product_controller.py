from http import HTTPStatus
from typing_extensions import List
from fastapi import APIRouter, Depends, HTTPException, Query
# from fastapi.encoders import jsonable_encoder

from sqlalchemy.orm import Session
from database import get_db

from src.services.product_service import (
    create_product,
    list_products,
    get_product_by_id,
    update_product,
    delete_product)

from src.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductByIdResponse,
    PaginatedProductResponse,
    ProductUpdate
)

from typing import Annotated
from auth import User, get_current_active_user


router = APIRouter()


@router.post("/", status_code=HTTPStatus.CREATED, response_model=ProductResponse)
async def create_product_endpoint(product: ProductCreate, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    Neste endpoint será para criar o Produto. Será passado pelo "body" os campos em JSON:
        _"name": str, "description": str, "price": float, "status": 'em estoque', 'em reposição' ou 'em falta', "stock_quantity": int_
    """

    return await create_product(product, db)


@router.get("/", status_code=HTTPStatus.OK, response_model=PaginatedProductResponse)
async def list_products_endpoint(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(10, ge=1, le=100, description="Número de itens por página"),
    search: str = Query(None, description="Filtrar por busca em título ou descrição do produto"),
    status: str = Query(None, description="Filtrar por status do produto: 'em estoque', 'em reposição' e 'em falta'"),
    section: str = Query(None, description="Filtrar por seção/categoria do produto"),
    min_price: float = Query(None, ge=0, description="Filtrar por preço mínimo"),
    max_price: float = Query(None, ge=0, description="Filtrar por preço máximo")
):
    """
    Neste endpoint será paginado e será possível colocar PAGE para o número da página, PAGE_SIZE para limitar o tamanho da lista. \n
    Em SEARCH você poderá procurar termos para ser buscado no Nome do Produto e na Descrição. \n
    Já em STATUS pode se filtrar como: 'em estoque', 'em reposição' e 'em falta'.
    """
    products, total = await list_products(
        db,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        section=section,
        min_price=min_price,
        max_price=max_price)

    response_data = {
        "products": products,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

    return response_data


@router.get("/{id}", status_code=HTTPStatus.OK, response_model=ProductByIdResponse)
async def get_product_by_id_endpoint(id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    Neste endpoint será exibido TODAS as informações do Produto indicado pelo ID.
    Assim como as informações de LOG de quando este produto foi exibido na listagem de busca.
    """

    product = await get_product_by_id(id, db)

    if not product:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Produto não encontrado")

    response_data = { "product": product, "views": [] }

    return response_data


@router.put("/{id}", status_code=HTTPStatus.OK, response_model=ProductResponse)
async def update_product_endpoint(id: int, product_data: ProductUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    Neste endpoint será para atualizar os dados do Produto, não precisando informar todos os campos mas
    somente aqueles que queira atualizar.
    """
    updated_product = await update_product(id, product_data, db)

    return updated_product


@router.delete("/{id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_product_endpoint(id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    Neste endpoint será para excluir o produto desejado, informando o ID.
    """
    await delete_product(id, db)

    return True
