from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    disabled = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)

    created_orders = relationship("Order", back_populates="created_by_user")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>" 