from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Schemas para Cliente

class ClientCreate(BaseModel):
    name: str = Field(..., description="Nome do cliente", max_length=100)
    email: str = Field(..., description="Email do cliente", max_length=100)
    phone: Optional[str] = Field(None, description="Telefone do cliente", max_length=20)
    address: Optional[str] = Field(None, description="Endereço do cliente", max_length=200)

class ClientResponse(BaseModel):
    id: int = Field(..., description="ID do cliente")
    name: str = Field(..., description="Nome do cliente", max_length=100)
    email: str = Field(..., description="Email do cliente", max_length=100)
    phone: Optional[str] = Field(None, description="Telefone do cliente", max_length=20)
    address: Optional[str] = Field(None, description="Endereço do cliente", max_length=200)
    active: bool = Field(..., description="Status de atividade do cliente")
    created_at: datetime = Field(..., description="Data de criação do cliente")
    updated_at: Optional[datetime] = Field(None, description="Data de última atualização do cliente")

    class Config:
        orm_mode = True

class ClientUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Nome do cliente", max_length=100)
    email: Optional[str] = Field(None, description="Email do cliente", max_length=100)
    phone: Optional[str] = Field(None, description="Telefone do cliente", max_length=20)
    address: Optional[str] = Field(None, description="Endereço do cliente", max_length=200)
    active: Optional[bool] = Field(None, description="Status de atividade do cliente")

class PaginatedClientResponse(BaseModel):
    clients: List[ClientResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
