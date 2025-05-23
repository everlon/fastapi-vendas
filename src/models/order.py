from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) # Relacionar com o usuário que fez o pedido
    total = Column(Float, nullable=False)
    status = Column(String, default="pending") # Ex: pending, processing, completed, cancelled
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Define relationships
    user = relationship("User", back_populates="orders") # Ou Client
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan", lazy='joined')

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False) # Chave estrangeira para o pedido
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False) # Chave estrangeira para o produto
    quantity = Column(Integer, nullable=False)
    price_at_time_of_purchase = Column(Float, nullable=False) # Preço do produto no momento da compra

    # Relação de volta para o pedido e para o produto
    order = relationship("Order", back_populates="items")
    product = relationship("Product") 