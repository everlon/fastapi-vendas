from fastapi import FastAPI, Depends

# from database import Base, engine

from src.routers import product_controller
from src.routers import client_controller
from src.routers import user_controller
from src.routers import order_controller

from auth import get_current_active_user

version = "v1"
version_prefix =f"/api/{version}"
description = "Desenvolvimento de API CRUD de Produtos em Python"

app = FastAPI(
    title="Teste InfoG2 FastApi",
    description=description,
    version=version,
    contact={
        "name": "Everlon Passos",
        "url": "https://github.com/everlon",
        "email": "everlon@protonmail.com",
    },
    openapi_url=f"{version_prefix}/openapi.json",
    docs_url=f"{version_prefix}/docs",
    redoc_url=f"{version_prefix}/redoc"
)

# Base.metadata.create_all(bind=engine)


@app.get("/")
async def root():
    return {"message": "Veja bem-vindo(a) a nossa API!"}


app.include_router(
    product_controller.router,
    prefix=f"{version_prefix}/products",
    tags=["products"],
    dependencies=[Depends(get_current_active_user)]
)

app.include_router(
    order_controller.router,
    prefix=f"{version_prefix}/orders",
    tags=["orders"],
    dependencies=[Depends(get_current_active_user)]
)

app.include_router(
    client_controller.router,
    prefix=f"{version_prefix}/clients",
    tags=["clients"],
    dependencies=[Depends(get_current_active_user)]
)

app.include_router(
    user_controller.router,
    prefix=f"{version_prefix}/users",
    tags=["users"]
)
