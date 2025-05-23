from fastapi import HTTPException
from http import HTTPStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_
from sqlalchemy.orm import selectinload
from datetime import datetime # Importar datetime

from src.models.order import Order, OrderItem
from src.models.product import Product # Precisamos do modelo de produto para verificar estoque e preço
from src.models.user import User as UserModel # Importar modelo de usuário para o tipo criado_por
from src.models.client import Client as ClientModel # Importar modelo de cliente para verificar se o cliente existe

from src.schemas.order import OrderCreate, OrderItemSchema, OrderUpdate # Importar schemas de entrada
# Podemos precisar importar schemas de saída se o serviço retornar o schema formatado
# from src.schemas.order import OrderResponse, OrderItemDetailSchema


async def create_order(db: AsyncSession, order_data: OrderCreate, created_by_user: UserModel) -> Order:
    """
    Cria um novo pedido no banco de dados com os itens fornecidos, associando-o a um cliente e ao usuário criador.

    Verifica a disponibilidade de estoque para cada produto no pedido, calcula o valor total,
    decrementa a quantidade em estoque dos produtos, associa o pedido ao cliente especificado
    e registra o usuário do sistema que executou a criação.

    Args:
        db: A sessão assíncrona do banco de dados.
        order_data: Os dados para a criação do pedido, incluindo o client_id e a lista de itens.
        created_by_user: O objeto User do usuário que está criando o pedido no sistema.

    Returns:
        A instância do pedido recém-criado com seus itens carregados.

    Raises:
        HTTPException: Se um produto nos itens do pedido não for encontrado (404), se a quantidade solicitada for maior que a disponível em estoque (400),
                       ou se o cliente especificado não for encontrado (404).
    """
    # Verificar se o cliente existe
    client_result = await db.execute(select(ClientModel).where(ClientModel.id == order_data.client_id))
    client = client_result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Cliente com ID {order_data.client_id} não encontrado.")

    total_amount = 0
    order_items = []

    for item_data in order_data.items:
        product_result = await db.execute(select(Product).where(Product.id == item_data.product_id))
        product = product_result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Produto com ID {item_data.product_id} não encontrado.")

        if product.stock_quantity < item_data.quantity:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=f"Estoque insuficiente para o produto {product.name}. Disponível: {product.stock_quantity}")

        price_at_time = product.price
        item_total = price_at_time * item_data.quantity
        total_amount += item_total

        order_item = OrderItem(
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            price_at_time_of_purchase=price_at_time
        )
        order_items.append(order_item)

        product.stock_quantity -= item_data.quantity
        db.add(product)

    new_order = Order(
        client_id=order_data.client_id, # Usar client_id do payload
        created_by_user_id=created_by_user.id, # Usar o ID do usuário autenticado
        total=total_amount,
        status="pending",
        items=order_items
    )

    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)

    return new_order

async def get_orders(
    db: AsyncSession,
    created_by_user: UserModel,
    skip: int = 0,
    limit: int = 10,
    client_id: int | None = None,
    order_id: int | None = None, # Novo parâmetro de filtro
    status: str | None = None,   # Novo parâmetro de filtro
    section: str | None = None, # Novo parâmetro de filtro
    start_date: datetime | None = None, # Novo parâmetro de filtro
    end_date: datetime | None = None # Novo parâmetro de filtro
):
    """
    Lista todos os pedidos da base de dados criados pelo usuário autenticado, com opções de filtragem por cliente, período, seção, ID do pedido e status, além de paginação.

    Args:
        db: A sessão assíncrona do banco de dados.
        created_by_user: O objeto User do usuário que está solicitando a listagem.
        skip: O número de registros a serem ignorados (offset) para paginação.
        limit: O número máximo de registros a serem retornados (limite) para paginação.
        client_id: O ID do cliente pelo qual filtrar os pedidos (opcional).
        order_id: O ID do pedido para filtrar (opcional).
        status: O status do pedido para filtrar (opcional).
        section: A seção dos produtos para filtrar (opcional).
        start_date: A data de início para filtrar por período (opcional).
        end_date: A data de fim para filtrar por período (opcional).

    Returns:
        Uma tupla contendo a lista de pedidos encontrados e o número total de pedidos que correspondem aos critérios.
    """
    # A base da query é sempre filtrar pelos pedidos criados pelo usuário autenticado
    query = select(Order).where(Order.created_by_user_id == created_by_user.id)

    # Adicionar filtros dinamicamente se forem fornecidos
    filters = []
    if client_id is not None:
        filters.append(Order.client_id == client_id)
    if order_id is not None:
        filters.append(Order.id == order_id)
    if status is not None:
        filters.append(Order.status == status)
    if start_date is not None:
        filters.append(Order.created_at >= start_date)
    if end_date is not None:
        filters.append(Order.created_at <= end_date)
    
    # Para o filtro de seção, precisamos juntar com OrderItem e Product
    if section is not None:
        query = query.join(OrderItem).join(Product) # Fazer os joins
        filters.append(Product.section == section)

    # Aplicar todos os filtros combinados com AND
    if filters:
        query = query.where(and_(*filters))

    # Contagem total para paginação
    # NOTA: Se houver joins na query, o func.count() pode precisar de ajuste para contar pedidos únicos.
    # Para uma contagem correta após joins, podemos contar o ID do pedido.
    if section is not None: # Se houve join com OrderItem/Product
        total_query = select(func.count(Order.id)).select_from(query.alias())
    else:
         total_query = select(func.count()).select_from(query.alias())
         
    total_result = await db.execute(total_query)
    total_orders = total_result.scalar_one()

    # Carregar relacionamentos para a resposta
    # Manter os relacionamentos existentes e adicionar OrderItem/Product se o filtro de seção foi usado
    options = [selectinload(Order.client), selectinload(Order.created_by_user)]
    # Se o filtro de seção foi usado, o join já foi feito na query principal,
    # então o selectinload de items já carregará os produtos associados.
    # Se o filtro de seção NÃO foi usado, carregamos os itens aqui.
    # No entanto, para simplificar e garantir que os itens sempre venham com os pedidos,
    # podemos sempre carregar os itens e, se o filtro de seção foi usado, o join já otimizou isso.
    options.append(selectinload(Order.items).selectinload(OrderItem.product)) # Carregar itens e produtos associados

    query = query.options(*options).offset(skip).limit(limit).distinct()
    # Usar distinct() para garantir que a contagem e os resultados da query principal
    # estejam corretos caso o filtro de seção (com join) introduza duplicatas de pedidos.

    result = await db.execute(query)
    orders = result.scalars().unique().all() # Usar unique() para remover duplicatas no resultado final

    return orders, total_orders

async def get_order_by_id(db: AsyncSession, order_id: int, created_by_user: UserModel):
    """
    Obtém um pedido específico da base de dados pelo seu ID, verificando se ele foi criado pelo usuário autenticado.

    Carrega os itens do pedido, o cliente e o usuário criador juntamente com o pedido.

    Args:
        db: A sessão assíncrona do banco de dados.
        order_id: O ID do pedido a ser buscado.
        created_by_user: O objeto User do usuário que está solicitando o pedido.

    Returns:
        A instância do pedido correspondente ao ID, ou None se nenhum pedido for encontrado.

    Raises:
        HTTPException: Se o pedido com o ID fornecido não for encontrado (404) OU se o pedido não foi criado pelo usuário autenticado (404 - para evitar enumerar IDs).
    """
    result = await db.execute(select(Order).where(Order.id == order_id, Order.created_by_user_id == created_by_user.id).options(selectinload(Order.items), selectinload(Order.client), selectinload(Order.created_by_user)))
    order = result.scalar_one_or_none()
    # A verificação created_by_user.id == created_by_user.id já foi adicionada na cláusula where acima.
    # Se order for None, significa que o pedido não existe ou não foi criado por este usuário.
    return order

async def update_order(db: AsyncSession, order_id: int, order_update_data: OrderUpdate, created_by_user: UserModel):
    """
    Atualiza um pedido existente na base de dados pelo seu ID.
    A verificação de permissão (se o pedido pertence ao usuário) já foi feita no endpoint.

    Permite a atualização parcial dos campos do pedido com base nos dados fornecidos.
    Carrega os relacionamentos client e created_by_user após a atualização.

    Args:
        db: A sessão assíncrona do banco de dados.
        order_id: O ID do pedido a ser atualizado.
        order_update_data: Os dados de atualização do pedido.
        created_by_user: O objeto User do usuário que está solicitando a atualização.

    Returns:
        A instância do pedido atualizado com seus itens carregados.

    Raises:
        HTTPException: Se houver algum erro durante a atualização.
    """
    # Buscar o pedido diretamente, já que a verificação de permissão foi feita no endpoint
    result = await db.execute(select(Order).where(Order.id == order_id).options(selectinload(Order.items), selectinload(Order.client), selectinload(Order.created_by_user)))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Pedido não encontrado")

    # Aplicar as atualizações
    update_data = order_update_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(order, key, value)

    db.add(order)
    await db.commit()
    await db.refresh(order)

    # Carregar relacionamentos após o refresh
    order = await get_order_by_id(db, order_id, created_by_user)

    return order

async def delete_order(db: AsyncSession, order_id: int, created_by_user: UserModel):
    """
    Deleta um pedido existente na base de dados pelo seu ID, verificando se ele foi criado pelo usuário autenticado.

    Antes de deletar o pedido, reverte a quantidade em estoque dos produtos associados aos itens do pedido.

    Args:
        db: A sessão assíncrona do banco de dados.
        order_id: O ID do pedido a ser deletado.
        created_by_user: O objeto User do usuário que está solicitando a exclusão.

    Returns:
        O objeto do pedido que foi deletado (antes de ser removido do cache).

    Raises:
        HTTPException: Se o pedido com o ID fornecido não for encontrado (404) OU se o pedido não foi criado pelo usuário autenticado (404 - para evitar enumerar IDs).
    """
    # Reutiliza get_order_by_id para buscar o pedido e já aplicar a verificação de created_by_user
    order = await get_order_by_id(db, order_id, created_by_user)
    if not order:
         # get_order_by_id já retorna None se não encontrar ou não pertencer ao usuário
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Pedido não encontrado")

    # Copiar itens antes de deletar o pedido, pois o cascade delete pode remover os itens primeiro
    order_items_copy = list(order.items)

    await db.delete(order)

    for item in order_items_copy:
        product_result = await db.execute(select(Product).where(Product.id == item.product_id))
        product = product_result.scalar_one_or_none()
        if product:
            product.stock_quantity += item.quantity
            db.add(product)

    await db.commit()
    # O objeto order não deve ser mais acessado após o commit da exclusão
    return order # Retornando o objeto antes do commit final para fins de teste/verificação, se necessário. Em produção, pode retornar uma confirmação. 