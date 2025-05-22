import os
from typing import AsyncGenerator
# from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy import Column, Integer, JSON, select, DateTime
from dotenv import load_dotenv
from datetime import datetime

# Carrega variáveis de ambiente
load_dotenv()

# Configuração do PostgreSQL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/infog2_db"
)

# Engine assíncrona do PostgreSQL
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Log de queries (desativar em produção)
    future=True,
    poolclass=NullPool,  # Desativa o pool de conexões para desenvolvimento
    pool_pre_ping=True,  # Verifica conexão antes de usar
)

# Sessão assíncrona
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base para modelos
Base = declarative_base()

# Dependency para obter sessão do banco
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
