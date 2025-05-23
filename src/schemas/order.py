from pydantic import BaseModel, Field, validator, field_validator
from typing import List, Optional
from datetime import datetime
from enum import Enum
from src.validators import validate_date_range

# Importar schema de produto se OrderItem precisar referenciar Product details
# from .product import ProductResponse # Depende de como queremos exibir o produto no item do pedido

# Importar schemas necessários (Client, User se forem incluídos na resposta)
# from .client import ClientResponse
# from .user import User

class OrderStatusEnum(str, Enum):
    pending = "pendente"
    processing = "processando"
    shipped = "enviado"
    delivered = "entregue"
    cancelled = "cancelado"

class OrderItemSchema(BaseModel):
    product_id: int = Field(..., description="ID do produto.", example=123)
    quantity: int = Field(..., gt=0, description="Quantidade do produto.", example=2)
    # price_at_time_of_purchase: float = Field(..., gt=0, description="Preço do produto no momento da compra") # Este campo será populado no backend

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError("A quantidade deve ser maior que zero")
        if v > 1000:  # Limite razoável para quantidade
            raise ValueError("A quantidade não pode ser maior que 1000")
        return v

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    client_id: int = Field(..., description="ID do cliente que está fazendo o pedido.", example=456)
    items: List[OrderItemSchema] = Field(..., min_items=1, description="Lista de itens do pedido.")

    @field_validator('items')
    @classmethod
    def validate_unique_products(cls, v):
        product_ids = [item.product_id for item in v]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Não é permitido repetir o mesmo produto no pedido")
        return v

class OrderItemDetailSchema(BaseModel):
    id: int = Field(..., description="ID do item do pedido.")
    order_id: int = Field(..., description="ID do pedido.")
    product_id: int = Field(..., description="ID do produto.")
    quantity: int = Field(..., description="Quantidade do produto.")
    price_at_time_of_purchase: float = Field(..., description="Preço do produto no momento da compra.", example=19.99)

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int = Field(..., description="ID do pedido.", example=1)
    client_id: int = Field(..., description="ID do cliente que fez o pedido.", example=456)
    created_by_user_id: Optional[int] = Field(None, description="ID do usuário que criou o pedido no sistema.", example=789)
    total: float = Field(..., description="Valor total do pedido.", example=39.98)
    status: str = Field(..., description="Status atual do pedido.", example="pendente")
    created_at: datetime = Field(..., description="Data e hora de criação do pedido.")
    updated_at: Optional[datetime] = Field(None, description="Data e hora da última atualização do pedido.")
    items: List[OrderItemDetailSchema] = Field(..., description="Detalhes dos itens incluídos no pedido.")

    # Se necessário, podemos adicionar detalhes completos do cliente e do usuário criador
    # client: ClientResponse
    # created_by_user: User # Necessita importar User schema

    class Config:
        from_attributes = True

# Schema para listagem paginada
class PaginatedOrderResponse(BaseModel):
    orders: List[OrderResponse] = Field(..., description="Lista de pedidos na página atual.")
    total: int = Field(..., description="Número total de pedidos.", example=10)
    page: int = Field(..., description="Número da página atual.", example=1)
    page_size: int = Field(..., description="Número de pedidos por página.", example=10)
    total_pages: int = Field(..., description="Número total de páginas disponíveis.", example=1)

    @field_validator('orders')
    @classmethod
    def validate_orders(cls, v):
        # Aqui poderíamos adicionar validações específicas para a lista de pedidos
        # Por exemplo, verificar se há pedidos duplicados
        return v

# Schema para atualização de pedido (ex: status)
class OrderUpdate(BaseModel):
    status: Optional[OrderStatusEnum] = Field(None, description="Novo status do pedido.", example=OrderStatusEnum.processing)

    @field_validator('status')
    @classmethod
    def validate_status_transition(cls, v):
        if v == OrderStatusEnum.cancelled:
            # Aqui poderíamos adicionar regras específicas para cancelamento
            # Por exemplo, verificar se o pedido já foi entregue
            pass
        return v 