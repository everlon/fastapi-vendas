from pydantic import BaseModel, Field, validator, field_validator
from enum import Enum
from typing import List, Optional
from datetime import datetime
from src.validators import validate_barcode, validate_future_date


class ProductStatusEnum(str, Enum):
    in_stock = "em estoque"
    restocking = "em reposição"
    out_of_stock = "em falta"


class ProductCreate(BaseModel):
    name: str = Field(..., description="Nome do produto.", max_length=100, example="Laptop")
    description: Optional[str] = Field(None, description="Descrição do produto.", max_length=500, example="Um laptop poderoso com processador i7.")
    price: float = Field(..., gt=0, description="Preço do produto.", example=1200.50)
    status: ProductStatusEnum = Field(..., description="Status do produto.", example=ProductStatusEnum.in_stock)
    stock_quantity: int = Field(..., ge=0, description="Quantidade em estoque do produto.", example=10)
    barcode: str = Field(..., description="Código de barras do produto.", max_length=100, example="1234567890123")
    section: Optional[str] = Field(None, description="Seção/Categoria do produto.", max_length=100, example="Eletrônicos")
    expiration_date: Optional[datetime] = Field(None, description="Data de validade do produto.", example="2024-12-31T23:59:59")
    images: Optional[List[str]] = Field(None, description="Lista de URLs das imagens do produto.", example=["http://example.com/img1.jpg", "http://example.com/img2.jpg"])

    _validate_barcode = field_validator('barcode')(validate_barcode)
    _validate_expiration_date = field_validator('expiration_date')(validate_future_date)

    @field_validator('images')
    @classmethod
    def validate_image_urls(cls, v):
        if v is None:
            return v
        for url in v:
            if not url.startswith(('http://', 'https://')):
                raise ValueError("URLs de imagens devem começar com http:// ou https://")
        return v

    class Config:
        # orm_mode = True
        from_attributes = True


class ProductResponse(ProductCreate):
    id: int = Field(..., description="ID do produto.", example=1)
    active: bool = Field(..., description="Indica se o produto está ativo.", example=True)
    created_at: datetime = Field(..., description="Data e hora de criação do produto.")
    updated_at: Optional[datetime] = Field(None, description="Data e hora da última alteração do produto.")


class ProductByIdResponse(BaseModel):
    product: ProductResponse = Field(..., description="Detalhes do produto.")
    views: list = Field(..., description="Lista de visualizações associadas ao produto.")


class ProductListResponse(BaseModel):
    id: int = Field(..., description="ID do produto.", example=1)
    name: str = Field(..., description="Nome do produto.", max_length=100, example="Laptop")
    description: Optional[str] = Field(None, description="Descrição do produto.", max_length=500, example="Um laptop poderoso.")
    price: float = Field(..., gt=0, description="Preço do produto.", example=1200.50)
    barcode: str = Field(..., description="Código de barras do produto.", max_length=100, example="1234567890123")
    section: Optional[str] = Field(None, description="Seção/Categoria do produto.", max_length=100, example="Eletrônicos")
    expiration_date: Optional[datetime] = Field(None, description="Data de validade do produto.", example="2024-12-31T23:59:59")
    images: Optional[List[str]] = Field(None, description="Lista de URLs das imagens do produto.", example=["http://example.com/img1_list.jpg"])
    status: ProductStatusEnum = Field(..., description="Status do produto.", example=ProductStatusEnum.in_stock)
    stock_quantity: int = Field(..., ge=0, description="Quantidade em estoque do produto.", example=10)

    _validate_barcode = field_validator('barcode')(validate_barcode)
    _validate_expiration_date = field_validator('expiration_date')(validate_future_date)


class PaginatedProductResponse(BaseModel):
    products: List[ProductListResponse] = Field(..., description="Lista de produtos na página atual.")
    total: int = Field(..., description="Número total de produtos.", example=50)
    page: int = Field(..., description="Número da página atual.", example=1)
    page_size: int = Field(..., description="Número de produtos por página.", example=10)
    total_pages: int = Field(..., description="Número total de páginas disponíveis.", example=5)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Nome do produto.", max_length=100, example="Laptop Pro")
    description: Optional[str] = Field(None, description="Descrição do produto.", max_length=500, example="Versão aprimorada.")
    price: Optional[float] = Field(None, gt=0, description="Preço do produto.", example=1300.00)
    status: Optional[ProductStatusEnum] = Field(None, description="Status do produto.", example=ProductStatusEnum.restocking)
    stock_quantity: Optional[int] = Field(None, ge=0, description="Quantidade em estoque do produto.", example=5)
    barcode: Optional[str] = Field(None, description="Código de barras do produto.", max_length=100, example="9876543210987")
    section: Optional[str] = Field(None, description="Seção/Categoria do produto.", max_length=100, example="Informática")
    expiration_date: Optional[datetime] = Field(None, description="Data de validade do produto.", example="2025-12-31T23:59:59")
    images: Optional[List[str]] = Field(None, description="Lista de URLs das imagens do produto.", example=["http://example.com/img_pro.jpg"])

    _validate_barcode = field_validator('barcode')(validate_barcode)
    _validate_expiration_date = field_validator('expiration_date')(validate_future_date)

    @field_validator('images')
    @classmethod
    def validate_image_urls(cls, v):
        if v is None:
            return v
        for url in v:
            if not url.startswith(('http://', 'https://')):
                raise ValueError("URLs de imagens devem começar com http:// ou https://")
        return v

    class Config:
        from_attributes = True
