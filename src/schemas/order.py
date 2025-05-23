from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Importar schema de produto se OrderItem precisar referenciar Product details
# from .product import ProductResponse # Depende de como queremos exibir o produto no item do pedido

class OrderItemSchema(BaseModel):
    product_id: int = Field(..., description="ID do produto")
    quantity: int = Field(..., gt=0, description="Quantidade do produto")
    # price_at_time_of_purchase: float = Field(..., gt=0, description="Preço do produto no momento da compra") # Este campo será populado no backend

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    items: List[OrderItemSchema] = Field(..., min_items=1, description="Lista de itens do pedido")
    # Não precisamos de campos como total, status, user_id aqui, pois serão definidos no backend

class OrderResponse(BaseModel):
    id: int
    user_id: int # Ou Client ID, dependendo do design
    total: float
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    items: List[OrderItemSchema] # Podemos precisar de um schema de OrderItem mais detalhado aqui

    class Config:
        from_attributes = True

# Vamos reavaliar o OrderItemSchema para incluir o preço de compra e talvez detalhes do produto
class OrderItemDetailSchema(BaseModel):
    product_id: int
    quantity: int
    price_at_time_of_purchase: float
    # Podemos adicionar um campo para os detalhes do produto, se necessário
    # product: ProductResponse # Necessita importar ProductResponse e ajustar a relação

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    user_id: int
    total: float
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    items: List[OrderItemDetailSchema]

    class Config:
        from_attributes = True

# Schema para listagem paginada
class PaginatedOrderResponse(BaseModel):
    orders: List[OrderResponse] # Podemos querer um schema OrderListResponse mais leve aqui
    total: int
    page: int
    page_size: int
    total_pages: int

# Schema para atualização de pedido (ex: status)
class OrderUpdate(BaseModel):
    status: Optional[str] = None
    # Adicionar outros campos permitidos para atualização, se necessário (ex: List[OrderItemSchema] para atualizar itens?) 