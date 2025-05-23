from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Schemas para Cliente

class ClientCreate(BaseModel):
    name: str = Field(..., description="Nome do cliente.", max_length=100, example="João Silva")
    email: str = Field(..., description="Email do cliente.", max_length=100, example="joao.silva@example.com")
    phone: Optional[str] = Field(None, description="Telefone do cliente.", max_length=20, example="(11) 98765-4321")
    address: Optional[str] = Field(None, description="Endereço do cliente.", max_length=200, example="Rua Exemplo, 123, Centro - São Paulo")

class ClientResponse(BaseModel):
    id: int = Field(..., description="ID do cliente.", example=1)
    name: str = Field(..., description="Nome do cliente.", max_length=100, example="João Silva")
    email: str = Field(..., description="Email do cliente.", max_length=100, example="joao.silva@example.com")
    phone: Optional[str] = Field(None, description="Telefone do cliente.", max_length=20, example="(11) 98765-4321")
    address: Optional[str] = Field(None, description="Endereço do cliente.", max_length=200, example="Rua Exemplo, 123, Centro - São Paulo")
    active: bool = Field(..., description="Status de atividade do cliente.", example=True)
    created_at: datetime = Field(..., description="Data de criação do cliente.")
    updated_at: Optional[datetime] = Field(None, description="Data de última atualização do cliente.")

    class Config:
        # orm_mode = True
        from_attributes = True

class ClientUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Nome do cliente.", max_length=100, example="João Silva Atualizado")
    email: Optional[str] = Field(None, description="Email do cliente.", max_length=100, example="joao.silva.novo@example.com")
    phone: Optional[str] = Field(None, description="Telefone do cliente.", max_length=20, example="(11) 91234-5678")
    address: Optional[str] = Field(None, description="Endereço do cliente.", max_length=200, example="Avenida Nova, 456, Bairro - São Paulo")
    active: Optional[bool] = Field(None, description="Status de atividade do cliente.", example=False)

class PaginatedClientResponse(BaseModel):
    clients: List[ClientResponse] = Field(..., description="Lista de clientes na página atual.")
    total: int = Field(..., description="Número total de clientes.", example=100)
    page: int = Field(..., description="Número da página atual.", example=1)
    page_size: int = Field(..., description="Número de clientes por página.", example=10)
    total_pages: int = Field(..., description="Número total de páginas disponíveis.", example=10)
