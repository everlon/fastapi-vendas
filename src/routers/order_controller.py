from fastapi import APIRouter, Depends, HTTPException, Query
from http import HTTPStatus
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from database import get_db

from src.services.order_service import create_order, get_orders, get_order_by_id, update_order, delete_order
from src.schemas.order import OrderCreate, OrderResponse, OrderUpdate, PaginatedOrderResponse

from auth import User, get_current_active_user


router = APIRouter()


@router.post("/", status_code=HTTPStatus.CREATED, response_model=OrderResponse)
async def create_order_endpoint(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    **Criação de um novo Pedido**

    Este endpoint permite que um usuário autenticado crie um novo pedido associado a um cliente específico, com um ou mais itens de produtos.

    **Corpo da Requisição (`OrderCreate`):**
    - `client_id`: ID do cliente que está fazendo o pedido (integer, obrigatório).
    - `items`: Lista de `OrderItemSchema` (list of objects, obrigatório).
      - `product_id`: ID do produto (integer, obrigatório).
      - `quantity`: Quantidade do produto (integer, obrigatório, mínimo 1).

    **Regras de Negócio:**
    - É necessário que o usuário esteja autenticado para criar um pedido.
    - O `client_id` fornecido deve corresponder a um cliente existente.
    - Cada `product_id` nos itens deve corresponder a um produto existente e disponível em estoque.
    - A quantidade solicitada (`quantity`) não pode exceder a quantidade disponível em estoque do produto.
    - O preço de cada item no pedido é fixado com base no preço atual do produto no momento da criação do pedido.
    - O estoque dos produtos é decrementado ao criar o pedido.
    - O valor total do pedido é calculado com base nos itens e suas quantidades/preços.
    - O ID do usuário autenticado é registrado como o criador do pedido.

    **Casos de Uso:**
    - Um funcionário registra um pedido feito por um cliente.
    - Integração com um sistema externo que cria pedidos em nome de clientes.

    **Exemplo de Requisição:**
    ```json
    {
      "client_id": 456,
      "items": [
        {
          "product_id": 1,
          "quantity": 2
        },
        {
          "product_id": 3,
          "quantity": 1
        }
      ]
    }
    ```

    **Exemplo de Resposta (Pedido Criado):**
    ```json
    {
      "id": 101,
      "client_id": 456,
      "created_by_user_id": 1,
      "total": 4200.00, # Exemplo: 2*1500 (smartphone) + 1*1200 (outro produto)
      "status": "pending",
      "created_at": "2023-10-27T14:30:00.000Z",
      "updated_at": "2023-10-27T14:30:00.000Z",
      "items": [
        {
          "id": 201,
          "order_id": 101,
          "product_id": 1,
          "quantity": 2,
          "price_at_time_of_purchase": 1500.00
        },
        {
          "id": 202,
          "order_id": 101,
          "product_id": 3,
          "quantity": 1,
          "price_at_time_of_purchase": 1200.00
        }
      ]
    }
    ```
    """
    new_order = await create_order(db=db, order_data=order_data, created_by_user=current_user)

    return new_order


@router.get("/", response_model=PaginatedOrderResponse)
async def list_orders_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, gt=0, le=100),
    client_id: Optional[int] = Query(None, description="Filtrar pedidos por ID do cliente.", example=456),
    order_id: Optional[int] = Query(None, description="Filtrar por ID do pedido.", example=101),
    status: Optional[str] = Query(None, description="Filtrar por status do pedido.", example="pending"),
    section: Optional[str] = Query(None, description="Filtrar pedidos por seção de produtos.", example="Eletrônicos"),
    start_date: Optional[datetime] = Query(None, description="Filtrar pedidos a partir desta data (inclusive).", example="2023-10-01T00:00:00"),
    end_date: Optional[datetime] = Query(None, description="Filtrar pedidos até esta data (inclusive).", example="2023-10-31T23:59:59"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    **Listagem de Pedidos (Paginada)**

    Este endpoint permite listar pedidos com opções de paginação e filtragem por cliente.
    Por padrão, lista todos os pedidos que o usuário autenticado tem permissão para ver.

    **Parâmetros de Query:**
    - `skip`: Número de itens a serem pulados (offset) (padrão: 0, mínimo: 0).
    - `limit`: Número máximo de itens a serem retornados (limite) (padrão: 10, mínimo: 1, máximo: 100).
    - `client_id`: Opcional. Filtra os pedidos por um ID de cliente específico.
    - `order_id`: Opcional. Filtra por um ID de pedido específico.
    - `status`: Opcional. Filtra por status do pedido (ex: 'pending', 'processing', 'shipped', 'delivered', 'cancelled').
    - `section`: Opcional. Filtra pedidos que contenham pelo menos um produto de uma seção específica.
    - `start_date`: Opcional. Filtra pedidos criados a partir desta data e hora (inclusive).
    - `end_date`: Opcional. Filtra pedidos criados até esta data e hora (inclusive).

    **Regras de Negócio:**
    - É necessário que o usuário esteja autenticado para listar pedidos.
    - A lógica de permissão para visualizar pedidos de determinados clientes deve ser implementada no serviço ou em uma dependência separada.
    - A paginação é aplicada aos resultados.

    **Casos de Uso:**
    - Um funcionário lista todos os pedidos no sistema.
    - Um funcionário lista os pedidos de um cliente específico.
    - (Com lógica de permissão adequada) Um usuário/cliente logado lista apenas seus próprios pedidos (neste caso, o client_id seria determinado pelo usuário logado).

    **Exemplo de Resposta:**
    ```json
    {
      "orders": [
        {
          "id": 101,
          "client_id": 456,
          "created_by_user_id": 1,
          "total": 4200.00,
          "status": "pending",
          "created_at": "2023-10-27T14:30:00.000Z",
          "updated_at": "2023-10-27T14:30:00.000Z",
          "items": [
            {
              "id": 201,
              "order_id": 101,
              "product_id": 1,
              "quantity": 2,
              "price_at_time_of_purchase": 1500.00
            }
          ]
        }
        // ... outros pedidos ...
      ],
      "total": 5,
      "page": 1,
      "page_size": 10,
      "total_pages": 1
    }
    ```
    """
    orders, total_orders = await get_orders(
        db=db,
        created_by_user=current_user,
        skip=skip,
        limit=limit,
        client_id=client_id,
        order_id=order_id,
        status=status,
        section=section,
        start_date=start_date,
        end_date=end_date
    )
    return PaginatedOrderResponse(
        orders=orders,
        total=total_orders,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
        total_pages=(total_orders + limit - 1) // limit if limit > 0 else 0
    )

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_by_id_endpoint(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    **Obtenção de Pedido por ID**

    Este endpoint permite obter os detalhes de um pedido específico utilizando seu ID.
    Requer que o usuário esteja autenticado. A lógica de permissão para visualizar pedidos (baseada em client_id ou created_by_user_id) deve ser implementada.

    **Parâmetros de Path:**
    - `order_id`: O ID único do pedido a ser buscado (integer).

    **Regras de Negócio:**
    - É necessário que o usuário esteja autenticado.
    - O `order_id` fornecido deve corresponder a um pedido existente.
    - A lógica de permissão (quem pode ver qual pedido) deve ser aplicada (atualmente não implementada neste nível).
    - Retorna status 404 Not Found se o pedido não existir.

    **Casos de Uso:**
    - Visualizar os detalhes de um pedido específico.
    - Obter informações de um pedido para acompanhamento de status ou suporte.

    **Exemplo de Resposta:**
    ```json
    {
      "id": 101,
      "client_id": 456,
      "created_by_user_id": 1,
      "total": 4200.00,
      "status": "pending",
      "created_at": "2023-10-27T14:30:00.000Z",
      "updated_at": "2023-10-27T14:30:00.000Z",
      "items": [
        {
          "id": 201,
          "order_id": 101,
          "product_id": 1,
          "quantity": 2,
          "price_at_time_of_purchase": 1500.00
        },
        {
          "id": 202,
          "order_id": 101,
          "product_id": 3,
          "quantity": 1,
          "price_at_time_of_purchase": 1200.00
        }
      ]
    }
    ```
    """
    order = await get_order_by_id(db=db, order_id=order_id, created_by_user=current_user)

    if not order:
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
    **Atualização de Pedido por ID**

    Este endpoint permite atualizar um pedido existente utilizando seu ID.
    Requer que o usuário esteja autenticado. A lógica de permissão para atualizar pedidos deve ser implementada.

    **Parâmetros de Path:**
    - `order_id`: O ID único do pedido a ser atualizado (integer).

    **Corpo da Requisição (`OrderUpdate`):**
    Permite enviar apenas o campo `status` que deseja atualizar.
    - `status`: O novo status do pedido (string, opcional, ex: 'processing', 'shipped', 'delivered', 'cancelled').

    **Regras de Negócio:**
    - É necessário que o usuário esteja autenticado.
    - O `order_id` fornecido deve corresponder a um pedido existente.
    - A lógica de permissão para atualizar pedidos deve ser implementada (agora verificada no serviço).
    - Apenas o campo `status` é considerado para atualização por este endpoint (conforme OrderUpdate schema).
    - A lógica para transições de status e seus impactos (ex: reverter estoque ao cancelar) é tratada no serviço.
    - Retorna status 404 Not Found se o pedido não existir.

    **Casos de Uso:**
    - Permitir a atualização do status de um pedido.

    **Exemplo de Requisição:**
    ```json
    {
      "status": "cancelled"
    }
    ```

    **Exemplo de Resposta (Pedido Atualizado):**
    ```json
    {
      "id": 101,
      "client_id": 456,
      "created_by_user_id": 1,
      "total": 4200.00,
      "status": "cancelled",
      "created_at": "2023-10-27T14:30:00.000Z",
      "updated_at": "2023-10-27T14:45:00.000Z",
      "items": [
        {
          "id": 201,
          "order_id": 101,
          "product_id": 1,
          "quantity": 2,
          "price_at_time_of_purchase": 1500.00
        }
      ]
    }
    ```

    """
    updated_order = await update_order(db=db, order_id=order_id, order_update_data=order_update_data, created_by_user=current_user)
    return updated_order

@router.delete("/{order_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_order_endpoint(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    **Exclusão de Pedido por ID**

    Este endpoint permite deletar um pedido existente utilizando seu ID.
    Requer que o usuário esteja autenticado. A lógica de permissão para deletar pedidos deve ser implementada.

    **Parâmetros de Path:**
    - `order_id`: O ID único do pedido a ser deletado (integer).

    **Regras de Negócio:**
    - É necessário que o usuário esteja autenticado.
    - O `order_id` fornecido deve corresponder a um pedido existente.
    - A lógica de permissão para deletar pedidos deve ser implementada (agora verificada no serviço).
    - Ao deletar, o estoque dos produtos associados aos itens do pedido é revertido.
    - Retorna status 404 Not Found se o pedido não existir ou não pertencer ao usuário autenticado.
    - Retorna status 204 No Content em caso de sucesso.

    **Casos de Uso:**
    - Remover um pedido que foi criado por engano.
    - (Com lógica de permissão adequada) Permitir que um usuário/administrador cancele e remova um pedido.

    """
    await delete_order(db=db, order_id=order_id, created_by_user=current_user)
    return
