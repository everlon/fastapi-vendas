from fastapi import HTTPException
from http import HTTPStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_
from sqlalchemy.orm import selectinload
from datetime import datetime # Importar datetime
from typing import List
from uuid import UUID

from src.models.order import Order, OrderItem, OrderStatusEnum
from src.models.product import Product
from src.models.user import User as UserModel
from src.models.client import Client as ClientModel

from src.schemas.order import OrderCreate, OrderItemSchema, OrderUpdate
from src.notifications.notification_service import NotificationService
from src.notifications.email_channel import EmailNotificationChannel

notification_service = NotificationService(channels=[EmailNotificationChannel()])

class OrderService:
    def __init__(
        self, 
        db_session, 
        notification_service: NotificationService
        ):
        self.db_session = db_session
        self.notification_service = NotificationService(channels=[
            EmailNotificationChannel(),
        ])

    async def create_order(
        self,
        order: OrderCreate,
        created_by_user: UserModel
        ) -> Order:
        # Criar a instância do pedido sem os itens inicialmente
        db_order = Order(
            client_id=order.client_id,
            created_by_user_id=created_by_user.id,
            status="pending", # Definir status inicial
            total=0 # O total será calculado abaixo
        )
        self.db_session.add(db_order)
        # Não comitar ainda, pois precisamos adicionar os itens e calcular o total

        total_amount = 0
        # Lista para guardar as instâncias de OrderItem
        db_order_items = []

        # Processar cada item do pedido
        for item_data in order.items:
            # Buscar o produto para verificar estoque e preço
            product_result = await self.db_session.execute(select(Product).where(Product.id == item_data.product_id))
            product = product_result.scalar_one_or_none()

            if not product:
                # Levantar exceção se o produto não for encontrado
                 raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Produto com ID {item_data.product_id} não encontrado.")

            # Verificar estoque
            if product.stock_quantity < item_data.quantity:
                 raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=f"Estoque insuficiente para o produto {product.name}. Disponível: {product.stock_quantity}")

            # Preço no momento da compra
            price_at_time = product.price
            item_total = price_at_time * item_data.quantity
            total_amount += item_total

            # Criar instância de OrderItem
            db_order_item = OrderItem(
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                price_at_time_of_purchase=price_at_time
            )
            # Adicionar o item à lista de itens do pedido principal (isso gerencia a relação)
            db_order_items.append(db_order_item)
            # db_order.items.append(db_order_item) # Alternativa: adicionar diretamente se db_order já está na sessão

            # Decrementar estoque
            product.stock_quantity -= item_data.quantity
            self.db_session.add(product) # Adicionar ou atualizar o produto na sessão

        # Adicionar a lista de itens processados ao pedido principal
        db_order.items = db_order_items
        # Atualizar o total do pedido
        db_order.total = total_amount

        # Agora podemos comitar
        await self.db_session.commit()
        # Atualizar a instância para carregar os relacionamentos (itens, cliente, criador)
        await self.db_session.refresh(db_order)

        # Após o commit, enviar a notificação (remover comentário se desejar)
        await self.notification_service.send_order_creation_notification(
            order=db_order,
            recipient_email="everlon@protonmail.com",
        )

        # Remover as linhas de debug
        # print(f"Debug: Tipo de db_order antes de retornar: {type(db_order)}")
        # print(f"Debug: db_order tem _sa_instance_state: {hasattr(db_order, '_sa_instance_state')}")

        return db_order

    async def get_orders(
        self,
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
         
        total_result = await self.db_session.execute(total_query)
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

        result = await self.db_session.execute(query)
        orders = result.scalars().unique().all() # Usar unique() para remover duplicatas no resultado final

        return orders, total_orders

    async def get_order_by_id(self, order_id: int, created_by_user: UserModel):
        """
        Obtém um pedido específico da base de dados pelo seu ID, verificando se ele foi criado pelo usuário autenticado.

        Carrega os itens do pedido, o cliente e o usuário criador juntamente com o pedido.

        Args:
            order_id: O ID do pedido a ser buscado.
            created_by_user: O objeto User do usuário que está solicitando o pedido.

        Returns:
            A instância do pedido correspondente ao ID, ou None se nenhum pedido for encontrado.

        Raises:
            HTTPException: Se o pedido com o ID fornecido não for encontrado (404) OU se o pedido não foi criado pelo usuário autenticado (404 - para evitar enumerar IDs).
        """
        result = await self.db_session.execute(select(Order).where(Order.id == order_id, Order.created_by_user_id == created_by_user.id).options(selectinload(Order.items), selectinload(Order.client), selectinload(Order.created_by_user)))
        order = result.scalar_one_or_none()
        # A verificação created_by_user.id == created_by_user.id já foi adicionada na cláusula where acima.
        # Se order for None, significa que o pedido não existe ou não foi criado por este usuário.
        return order

    async def update_order(self, order_id: int, order_update_data: OrderUpdate, created_by_user: UserModel):
        """
        Atualiza um pedido existente na base de dados pelo seu ID.
        A verificação de permissão (se o pedido pertence ao usuário) já foi feita no endpoint.

        Permite a atualização parcial dos campos do pedido com base nos dados fornecidos.
        Carrega os relacionamentos client e created_by_user após a atualização.

        Args:
            order_id: O ID do pedido a ser atualizado.
            order_update_data: Os dados de atualização do pedido.
            created_by_user: O objeto User do usuário que está solicitando a atualização.

        Returns:
            A instância do pedido atualizado com seus itens carregados.

        Raises:
            HTTPException: Se houver algum erro durante a atualização.
        """

        result = await self.db_session.execute(select(Order).where(Order.id == order_id).options(selectinload(Order.items), selectinload(Order.client), selectinload(Order.created_by_user)))
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Pedido não encontrado")

        update_data = order_update_data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(order, key, value)

        self.db_session.add(order)
        await self.db_session.commit()
        await self.db_session.refresh(order)

        order = await self.get_order_by_id(order_id, created_by_user)

        return order

    async def delete_order(self, order_id: int, created_by_user: UserModel):
        """
        Deleta um pedido existente na base de dados pelo seu ID, verificando se ele foi criado pelo usuário autenticado.

        Antes de deletar o pedido, reverte a quantidade em estoque dos produtos associados aos itens do pedido.

        Args:
            order_id: O ID do pedido a ser deletado.
            created_by_user: O objeto User do usuário que está solicitando a exclusão.

        Returns:
            O objeto do pedido que foi deletado (antes de ser removido do cache).

        Raises:
            HTTPException: Se o pedido com o ID fornecido não for encontrado (404) OU se o pedido não foi criado pelo usuário autenticado (404 - para evitar enumerar IDs).
        """
        order = await self.get_order_by_id(order_id, created_by_user)
        if not order:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Pedido não encontrado")

        order_items_copy = list(order.items)

        await self.db_session.delete(order)

        for item in order_items_copy:
            product_result = await self.db_session.execute(select(Product).where(Product.id == item.product_id))
            product = product_result.scalar_one_or_none()
            if product:
                product.stock_quantity += item.quantity
                self.db_session.add(product)

        await self.db_session.commit()
        return order

    async def list_orders(
        self,
        page: int = 1,
        page_size: int = 10,
        client_id: int = None,
        status: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        created_by_user: UserModel = None
    ) -> dict:
        """
        Lista pedidos com paginação e filtros.
        """
        query = select(Order)
        if created_by_user:
             query = query.where(Order.created_by_user_id == created_by_user.id)

        if client_id:
            query = query.where(Order.client_id == client_id)

        if status:
            query = query.where(Order.status == status)

        if start_date:
            query = query.where(Order.created_at >= start_date)

        if end_date:
            query = query.where(Order.created_at <= end_date)

        total_query = select(func.count()).select_from(query.subquery())
        total = await self.db_session.execute(total_query) # Usar self.db_session
        total = total.scalar()

        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db_session.execute(query) # Usar self.db_session
        orders = result.scalars().all()

        orders_with_items = []
        for order in orders:
            items_query = select(OrderItem).where(OrderItem.order_id == order.id)
            items_result = await self.db_session.execute(items_query) # Usar self.db_session
            items = items_result.scalars().all()

            product_ids = [item.product_id for item in items]
            products_query = select(Product).where(Product.id.in_(product_ids))
            products_result = await self.db_session.execute(products_query) # Usar self.db_session
            products = {p.id: p for p in products_result.scalars().all()}

            order_items = []
            for item in items:
                product = products.get(item.product_id)
                if product:
                    order_items.append({
                        "id": item.id,
                        "product": product,
                        "quantity": item.quantity,
                        "price_at_time_of_purchase": item.price_at_time_of_purchase
                    })

            orders_with_items.append({
                **order.__dict__,
                "items": order_items
            })

        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1

        return {
            "orders": orders_with_items,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        } 