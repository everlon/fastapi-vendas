from pydantic import BaseModel, Field
from typing import Optional


class Token(BaseModel):
    access_token: str = Field(..., description="Token de acesso JWT.", example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(..., description="Tipo do token, geralmente 'bearer'.", example="bearer")


class UserBase(BaseModel):
    username: str = Field(..., description="Nome de usuário único.", example="john_doe")
    email: Optional[str] = Field(None, description="Endereço de e-mail do usuário.", example="john.doe@example.com")
    full_name: Optional[str] = Field(None, description="Nome completo do usuário.", example="John Doe")
    disabled: Optional[bool] = Field(False, description="Indica se a conta do usuário está desativada.", example=False)


class UserCreate(UserBase):
    password: str = Field(..., description="Senha do usuário.", example="senhaSegura123")


class UserUpdate(UserBase):
    password: Optional[str] = Field(None, description="Nova senha para o usuário (opcional).")


class User(UserBase):
    id: int = Field(..., description="ID único do usuário.", example=1)

    class Config:
        # orm_mode = True # orm_mode foi renomeado para from_attributes no Pydantic v2+
        from_attributes = True 