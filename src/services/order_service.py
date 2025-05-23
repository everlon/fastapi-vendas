from fastapi import HTTPException
from http import HTTPStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from src.models.order import Order, OrderItem
from src.models.product import Product # Precisamos do modelo de produto para verificar estoque e preço
from src.schemas.order import OrderCreate, OrderItemSchema, OrderUpdate # Importar schemas de entrada
# Podemos precisar importar schemas de saída se o serviço retornar o schema formatado
# from src.schemas.order import OrderResponse, OrderItemDetailSchema


async def create_order(db: AsyncSession, order_data: OrderCreate, user_id: int) -> Order:
    """
    Cria um novo pedido no banco de dados.
    Verifica a disponibilidade do produto e calcula o total do pedido.
    """
    total_amount = 0
    order_items = []

    # Percorrer os itens do pedido de entrada
    for item_data in order_data.items:
        # Buscar o produto no DB para verificar existência, preço e estoque
        product_result = await db.execute(select(Product).where(Product.id == item_data.product_id))
        product = product_result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Produto com ID {item_data.product_id} não encontrado.")

        if product.stock_quantity < item_data.quantity:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=f"Estoque insuficiente para o produto {product.name}. Disponível: {product.stock_quantity}")

        # Calcular o preço do item no momento da compra e adicionar ao total
        price_at_time = product.price # Usar o preço atual do produto
        item_total = price_at_time * item_data.quantity
        total_amount += item_total

        # Criar a instância de OrderItem
        order_item = OrderItem(
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            price_at_time_of_purchase=price_at_time
        )
        order_items.append(order_item)

        # Atualizar a quantidade em estoque do produto (subtrair a quantidade comprada)
        product.stock_quantity -= item_data.quantity
        db.add(product) # Adicionar a alteração ao db

    # Criar a instância de Order
    new_order = Order(
        user_id=user_id,
        total=total_amount,
        status="pending", # Status inicial
        items=order_items
    )

    # Adicionar o novo pedido e seus itens à sessão e commitar
    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)

    return new_order

async def get_orders(db: AsyncSession, skip: int = 0, limit: int = 10, user_id: int | None = None):
    """
    Lista todos os pedidos, opcionalmente filtrando por usuário, com paginação.
    """
    query = select(Order)
    if user_id is not None:
        query = query.where(Order.user_id == user_id)

    # Contar o total de pedidos para paginação
    total_query = select(func.count()).select_from(query.alias())
    total_result = await db.execute(total_query)
    total_orders = total_result.scalar_one()

    # Aplicar paginação
    query = query.offset(skip).limit(limit).options(selectinload(Order.items))

    result = await db.execute(query)
    orders = result.scalars().all()

    return orders, total_orders

async def get_order_by_id(db: AsyncSession, order_id: int):
    """
    Obtém um pedido pelo seu ID.
    """
    result = await db.execute(select(Order).where(Order.id == order_id).options(selectinload(Order.items)))
    order = result.scalar_one_or_none()
    return order

async def update_order(db: AsyncSession, order_id: int, order_update_data: OrderUpdate):
    """
    Atualiza um pedido existente pelo seu ID.
    """
    order = await get_order_by_id(db, order_id)
    if not order:
        return None

    update_data = order_update_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(order, key, value)

    db.add(order)
    await db.commit()
    await db.refresh(order)

    return order

async def delete_order(db: AsyncSession, order_id: int):
    """
    Deleta um pedido existente pelo seu ID.
    """
    order = await get_order_by_id(db, order_id)
    if not order:
        return None

    # Reverter estoque dos produtos ao deletar o pedido
    for item in order.items:
        product_result = await db.execute(select(Product).where(Product.id == item.product_id))
        product = product_result.scalar_one_or_none()
        if product:
            product.stock_quantity += item.quantity
            db.add(product) # Adicionar a alteração do produto à sessão

    await db.delete(order)
    await db.commit()
    # Não precisa de refresh após deletar
    return order # Retornar o objeto deletado ou simplesmente True/False 