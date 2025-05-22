from sqlalchemy import Column, Integer, String, Float, Enum, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from database import Base
from src.schemas.product import ProductStatusEnum


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    status = Column(Enum(ProductStatusEnum), nullable=False)
    stock_quantity = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    barcode = Column(String, unique=True, nullable=False, index=True)
    section = Column(String, nullable=False)
    expiration_date = Column(DateTime, nullable=True)
    images = Column(JSON, nullable=True)  # Lista de URLs de imagens
