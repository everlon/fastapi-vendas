from datetime import datetime, timedelta
from typing import Annotated

import os
import jwt
from typing import Optional
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status

from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.user import User, Token
from src.schemas.user import User as UserSchema
from src.services.user_service import get_user_by_username
from src.services.user_service import verify_password as verify_password_service

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt

async def get_user(db: AsyncSession, username: str):
    return await get_user_by_username(db, username)

async def authenticate_user(db: AsyncSession, username: str, password: str):
    user = await get_user(db, username)

    if not user:
        return False

    if not verify_password_service(password, user.hashed_password):
        return False

    return user

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

    except InvalidTokenError:
        raise credentials_exception

    user = await get_user(db, username=username)

    if user is None:
        raise credentials_exception

    return user

async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário inativo"
        )
    return current_user

async def get_current_admin_user(current_user: Annotated[User, Depends(get_current_active_user)]) -> User:
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Não autorizado: apenas administradores podem realizar esta ação."
        )
    return current_user
