from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True) # Email pode ser opcional
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    disabled = Column(Boolean, default=False)

    # Define relationships
    orders = relationship("Order", back_populates="user")
    # clients = relationship("Client", back_populates="user") # Se houver relação direta com clientes

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>" 