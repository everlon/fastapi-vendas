from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from auth import create_access_token, authenticate_user, get_current_active_user
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.user import Token, User
from src.schemas.user import User as UserSchema

router = APIRouter()


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: AsyncSession = Depends(get_db)):
    """
    **Obtenção de Token de Acesso (Login)**

    Este endpoint permite que um usuário se autentique fornecendo seu nome de usuário e senha
    e, em caso de sucesso, receba um token de acesso JWT.

    **Corpo da Requisição (form-data):**
    - `username`: Nome de usuário do usuário (string, obrigatório).
    - `password`: Senha do usuário (string, obrigatório).

    **Regras de Negócio:**
    - O nome de usuário e a senha devem corresponder a um usuário ativo na base de dados.
    - O token de acesso gerado tem um tempo de expiração definido (atualmente 30 minutos).
    - Retorna status 401 Unauthorized se as credenciais forem inválidas.

    **Casos de Uso:**
    - Autenticar um usuário ao fazer login na aplicação.
    - Obter um token de acesso para ser usado em requisições subsequentes a endpoints protegidos.

    **Exemplo de Requisição (usando cURL):**
    ```bash
    curl -X POST \
      http://localhost:8000/api/v1/auth/token \
      -d "username=testuser&password=securepassword"
    ```

    **Exemplo de Resposta (Token de Acesso):**
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer"
    }
    ```
    """
    user = await authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}
