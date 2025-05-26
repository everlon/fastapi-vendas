from pydantic import BaseModel, Field, validator, field_validator
from typing import Optional, List
from datetime import datetime
from src.validators import validate_cpf, validate_email, validate_phone

# Schema para endereço do cliente
class AddressSchema(BaseModel):
    street: str = Field(..., description="Rua do cliente.", max_length=100, example="Rua Exemplo")
    number: str = Field(..., description="Número do endereço.", max_length=10, example="123")
    complement: Optional[str] = Field(None, description="Complemento do endereço.", max_length=50, example="Apto 45")
    neighborhood: str = Field(..., description="Bairro do cliente.", max_length=100, example="Centro")
    city: str = Field(..., description="Cidade do cliente.", max_length=100, example="São Paulo")
    state: str = Field(..., description="Estado do cliente.", max_length=2, example="SP")
    zip_code: str = Field(..., description="CEP do cliente.", max_length=8, example="01234567")

# Schemas para Cliente

class ClientCreate(BaseModel):
    name: str = Field(..., description="Nome do cliente.", max_length=100, example="João Silva")
    email: str = Field(..., description="Email do cliente.", max_length=100, example="joao.silva@example.com")
    phone: Optional[str] = Field(None, description="Telefone do cliente.", max_length=20, example="(11) 98765-4321")
    address: AddressSchema = Field(..., description="Endereço do cliente.")
    cpf: Optional[str] = Field(None, description="CPF do cliente (apenas números).", max_length=11, example="12345678900")

    _validate_email = field_validator('email')(validate_email)
    _validate_phone = field_validator('phone')(validate_phone)
    _validate_cpf = field_validator('cpf')(validate_cpf)

class ClientResponse(BaseModel):
    id: int = Field(..., description="ID do cliente.", example=1)
    name: str = Field(..., description="Nome do cliente.", max_length=100, example="João Silva")
    email: str = Field(..., description="Email do cliente.", max_length=100, example="joao.silva@example.com")
    phone: Optional[str] = Field(None, description="Telefone do cliente.", max_length=20, example="(11) 98765-4321")
    address: AddressSchema = Field(..., description="Endereço do cliente.")
    cpf: Optional[str] = Field(None, description="CPF do cliente (apenas números).", max_length=11, example="12345678900")
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
    address: Optional[AddressSchema] = Field(None, description="Endereço do cliente.")
    active: Optional[bool] = Field(None, description="Status de atividade do cliente.", example=False)
    cpf: Optional[str] = Field(None, description="CPF do cliente (apenas números).", max_length=11, example="12345678900")

    _validate_email = field_validator('email')(validate_email)
    _validate_phone = field_validator('phone')(validate_phone)
    _validate_cpf = field_validator('cpf')(validate_cpf)

class PaginatedClientResponse(BaseModel):
    clients: List[ClientResponse] = Field(..., description="Lista de clientes na página atual.")
    total: int = Field(..., description="Número total de clientes.", example=100)
    page: int = Field(..., description="Número da página atual.", example=1)
    page_size: int = Field(..., description="Número de clientes por página.", example=10)
    total_pages: int = Field(..., description="Número total de páginas disponíveis.", example=10)
 