from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from src.schemas.user import User, UserCreate
from src.services.user_service import create_user, get_user_by_username, get_user_by_email
from auth import get_current_active_user

router = APIRouter()

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    **Criação de um novo Usuário**

    Este endpoint permite criar um novo usuário na base de dados.

    **Corpo da Requisição (`UserCreate`):**
    - `username`: Nome de usuário (string, obrigatório, deve ser único).
    - `email`: Endereço de e-mail (string, opcional, se fornecido deve ser único).
    - `password`: Senha do usuário (string, obrigatório).
    - `full_name`: Nome completo (string, opcional).
    - `disabled`: Indica se o usuário está desativado (boolean, padrão: `False`).

    **Regras de Negócio:**
    - O `username` fornecido deve ser único na base de dados.
    - O `email`, se fornecido, deve ser único na base de dados.
    - A senha (`password`) é criptografada antes de ser armazenada.

    **Casos de Uso:**
    - Registrar um novo usuário para acessar a aplicação.
    - Utilizado no processo de cadastro de novos usuários.

    **Exemplo de Requisição:**
    ```json
    {
      "username": "novo_usuario",
      "email": "novo.usuario@email.com",
      "password": "senhaSegura123",
      "full_name": "Novo Usuário"
    }
    ```

    **Exemplo de Resposta (Usuário Criado):**
    ```json
    {
      "id": 1,
      "username": "novo_usuario",
      "email": "novo.usuario@email.com",
      "full_name": "Novo Usuário",
      "disabled": false,
      "created_at": "2023-01-01T10:00:00.000Z",
      "updated_at": "2023-01-01T10:00:00.000Z"
    }
    ```
    """
    db_user_by_username = await get_user_by_username(db, username=user.username)
    if db_user_by_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    
    if user.email:
        db_user_by_email = await get_user_by_email(db, email=user.email)
        if db_user_by_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    return await create_user(db=db, user=user)

@router.get("/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    **Obtenção do Usuário Autenticado**

    Este endpoint retorna as informações do usuário atualmente autenticado.
    Requer que um token de acesso válido seja fornecido no cabeçalho `Authorization: Bearer <token>`.

    **Regras de Negócio:**
    - Apenas usuários autenticados podem acessar este endpoint.
    - As informações retornadas são referentes ao usuário cujo token de acesso foi utilizado.

    **Casos de Uso:**
    - Exibir o perfil do usuário logado.
    - Obter informações do usuário para personalizar a interface da aplicação.

    **Exemplo de Resposta (Usuário Autenticado):**
    ```json
    {
      "id": 1,
      "username": "usuario_logado",
      "email": "usuario.logado@email.com",
      "full_name": "Usuário Logado",
      "disabled": false,
      "created_at": "2023-01-01T09:00:00.000Z",
      "updated_at": "2023-01-01T09:00:00.000Z"
    }
    ```
    """
    return current_user 