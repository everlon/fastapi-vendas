import os
from pydantic_settings import BaseSettings
from pydantic import EmailStr
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Configurações do Banco de Dados (manter as existentes)
    DATABASE_URL: str = "postgresql+asyncpg://user:password@host:port/database"
    SECRET_KEY: str = "sua-chave-secreta-aqui"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Configurações do Email para Notificações
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = os.getenv("SMTP_HOST")
    SMTP_USER: str = os.getenv("SMTP_USER")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD")
    EMAILS_FROM_EMAIL: EmailStr = os.getenv("EMAILS_FROM_EMAIL")
    EMAILS_FROM_NAME: str = os.getenv("EMAILS_FROM_NAME")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = 'ignore'

settings = Settings()
