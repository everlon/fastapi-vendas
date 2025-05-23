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
    **Criação de um novo Produto**

    Este endpoint permite criar um novo produto na base de dados.
    É necessário que o usuário esteja autenticado para realizar esta operação.

    **Regras de Negócio:**
    - O campo `name` é obrigatório e deve ser único.
    - `description` é opcional.
    - `price` deve ser um valor positivo.
    - `status` deve ser um dos valores permitidos ('em estoque', 'em reposição', 'em falta').
    - `stock_quantity` deve ser um valor não negativo.
    - `barcode` é opcional, mas se informado deve ser único.
    - `section` é opcional.
    - `images` é opcional e deve ser uma lista de URLs (string).

    **Casos de Uso:**
    - Registrar um novo produto disponível para venda.
    - Incluir detalhes como preço, estoque, categoria e imagens.

    **Exemplo de Requisição:**
    ```json
    {
      "name": "Notebook Exemplo",
      "description": "Um notebook de alta performance.",
      "price": 3500.00,
      "status": "em estoque",
      "stock_quantity": 50,
      "barcode": "1234567890123",
      "section": "Eletrônicos",
      "images": ["http://example.com/img1.jpg", "http://example.com/img2.png"]
    }
    ```
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
    **Listagem e Busca de Produtos (Paginada)**

    Este endpoint permite listar produtos com opções de busca, filtragem e paginação.

    **Parâmetros de Query:**
    - `page`: Número da página (padrão: 1, mínimo: 1).
    - `page_size`: Número de itens por página (padrão: 10, mínimo: 1, máximo: 100).
    - `search`: Termo para buscar no nome ou descrição do produto (opcional).
    - `status`: Filtrar por status do produto ('em estoque', 'em reposição', 'em falta') (opcional).
    - `section`: Filtrar por seção/categoria do produto (opcional).
    - `min_price`: Filtrar por preço mínimo (opcional, mínimo: 0).
    - `max_price`: Filtrar por preço máximo (opcional, mínimo: 0).

    **Regras de Negócio:**
    - A paginação é obrigatória para evitar retornos excessivamente grandes.
    - Múltiplos filtros podem ser combinados (ex: buscar por nome *e* filtrar por status).
    - A busca por termo (`search`) é case-insensitive e procura tanto no nome quanto na descrição.

    **Casos de Uso:**
    - Exibir a lista de produtos na página inicial ou em uma categoria específica.
    - Permitir que usuários busquem produtos por nome ou descrição.
    - Filtrar produtos por status (disponível, em falta, etc.) ou por faixa de preço.
    - Implementar a navegação entre páginas de resultados.

    **Exemplo de Resposta:**
    ```json
    {
      "products": [
        {
          "id": 1,
          "name": "Smartphone X",
          "description": "Um smartphone de última geração.",
          "price": 1500.00,
          "status": "em estoque",
          "stock_quantity": 25,
          "barcode": "9876543210987",
          "section": "Eletrônicos",
          "images": ["http://example.com/phone.jpg"],
          "created_at": "2023-01-01T10:00:00.000Z",
          "updated_at": "2023-01-01T10:00:00.000Z"
        }
      ],
      "total": 100,
      "page": 1,
      "page_size": 10,
      "total_pages": 10
    }
    ```
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
    **Obtenção de Produto por ID**

    Este endpoint permite obter os detalhes completos de um produto específico utilizando seu ID.
    É necessário que o usuário esteja autenticado.

    **Parâmetros de Path:**
    - `id`: O ID único do produto a ser buscado (integer).

    **Regras de Negócio:**
    - O ID fornecido deve corresponder a um produto existente na base de dados.
    - Retorna status 404 se o produto não for encontrado.

    **Casos de Uso:**
    - Exibir a página de detalhes de um produto selecionado pelo usuário.
    - Obter informações completas de um produto para edição ou visualização.

    **Exemplo de Resposta:**
    ```json
    {
      "product": {
        "id": 1,
        "name": "Smartphone X",
        "description": "Um smartphone de última geração.",
        "price": 1500.00,
        "status": "em estoque",
        "stock_quantity": 25,
        "barcode": "9876543210987",
        "section": "Eletrônicos",
        "images": ["http://example.com/phone.jpg"],
        "created_at": "2023-01-01T10:00:00.000Z",
        "updated_at": "2023-01-01T10:00:00.000Z"
      },
      "views": []
    }
    ```
    """

    product = await get_product_by_id(id, db)

    if not product:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Produto não encontrado")

    response_data = { "product": product, "views": [] }

    return response_data


@router.put("/{id}", status_code=HTTPStatus.OK, response_model=ProductResponse)
async def update_product_endpoint(id: int, product_data: ProductUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    **Atualização de Produto por ID**

    Este endpoint permite atualizar parcialmente ou totalmente os dados de um produto existente utilizando seu ID.
    É necessário que o usuário esteja autenticado.

    **Parâmetros de Path:**
    - `id`: O ID único do produto a ser atualizado (integer).

    **Corpo da Requisição (`ProductUpdate`):**
    Permite enviar apenas os campos que deseja atualizar. Os campos opcionais incluem `name`, `description`, `price`, `status`, `stock_quantity`, `barcode`, `section`, e `images`.

    **Regras de Negócio:**
    - O ID fornecido deve corresponder a um produto existente na base de dados.
    - A validação dos dados (`name`, `price`, `status`, etc.) segue as mesmas regras do endpoint de criação, exceto que os campos são opcionais.
    - O campo `barcode`, se fornecido e diferente do atual, deve ser único na base de dados.
    - Retorna status 404 se o produto não for encontrado.

    **Casos de Uso:**
    - Corrigir informações de um produto existente.
    - Atualizar o preço ou quantidade em estoque de um produto.
    - Adicionar ou remover imagens do produto.

    **Exemplo de Requisição:**
    ```json
    {
      "price": 3600.00,
      "stock_quantity": 45
    }
    ```

    **Exemplo de Resposta (Produto Atualizado):**
    ```json
    {
      "id": 1,
      "name": "Notebook Exemplo",
      "description": "Um notebook de alta performance.",
      "price": 3600.00,
      "status": "em estoque",
      "stock_quantity": 45,
      "barcode": "1234567890123",
      "section": "Eletrônicos",
      "images": ["http://example.com/img1.jpg", "http://example.com/img2.png"],
      "created_at": "2023-01-01T10:00:00.000Z",
      "updated_at": "2023-01-01T10:15:00.000Z" # Data de atualização mudaria
    }
    ```
    """
    updated_product = await update_product(id, product_data, db)

    return updated_product


@router.delete("/{id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_product_endpoint(id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    **Exclusão de Produto por ID**

    Este endpoint permite excluir um produto existente utilizando seu ID.
    É necessário que o usuário esteja autenticado para realizar esta operação.

    **Parâmetros de Path:**
    - `id`: O ID único do produto a ser excluído (integer).

    **Regras de Negócio:**
    - O ID fornecido deve corresponder a um produto existente na base de dados.
    - Ao excluir um produto, o estoque que estava associado a ele nos itens de pedidos é revertido.
    - Retorna status 404 se o produto não for encontrado.

    **Casos de Uso:**
    - Remover um produto que não está mais disponível ou que foi cadastrado incorretamente.

    **Resposta de Sucesso:**
    - Retorna status 204 No Content se a exclusão for bem-sucedida.
    """
    await delete_product(id, db)

    return True
