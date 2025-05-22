from http import HTTPStatus

# from pydantic import version
import pytest
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db

from app.main import app


# Configuração do banco de dados de teste.
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Substituir a dependência get_db com a versão de teste
app.dependency_overrides[get_db] = override_get_db

Base.metadata.create_all(bind=engine)

client = TestClient(app)

version_prefix = "/api/v1/products"


def login_token():
    # Efetuar login para obter Token
    response = client.post("/api/v1/auth/token", data={"username": "everlon", "password": "secret"})
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    return {"Authorization": f"Bearer {data["access_token"]}"}


def test_create_product():
    product_data = {
        "name": "Produto de Teste",
        "description": "Descrição do Produto teste",
        "price": 99.99,
        "status": "em estoque",
        "stock_quantity": 10,
        "barcode": "1234567890124",
        "section": "Eletrônicos",
        "expiration_date": "2030-12-31T00:00:00",
        "images": ["http://example.com/img1.jpg", "http://example.com/img2.jpg"]
    }

    response = client.post(f"{version_prefix}/", json=product_data, headers=login_token())

    assert response.status_code == HTTPStatus.CREATED, f"Erro: {response.text}"

    response_data = response.json()
    assert response_data["name"] == product_data["name"]
    assert response_data["description"] == product_data["description"]
    assert response_data["price"] == product_data["price"]
    assert response_data["status"] == "em estoque"
    assert response_data["stock_quantity"] == product_data["stock_quantity"]
    assert response_data["barcode"] == product_data["barcode"]
    assert response_data["section"] == product_data["section"]
    assert response_data["expiration_date"].startswith("2030-12-31")
    assert response_data["images"] == product_data["images"]
    assert response_data["active"] is True
    assert "created_at" in response_data


def test_list_products():
    client.post(f"{version_prefix}/", json={
        "name": "Produto Teste",
        "description": "Descrição do produto",
        "price": 99.99,
        "status": "em estoque",
        "stock_quantity": 20
    }, headers=login_token())

    response = client.get(f"{version_prefix}/", headers=login_token())

    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json(), dict)
    assert len(response.json()) > 0


def test_get_product_by_id():
    # Criar um produto para garantir que a lista não esteja vazia
    response = client.post(f"{version_prefix}/", json={
        "name": "Produto Teste",
        "description": "Descrição do produto",
        "price": 99.99,
        "status": "em estoque",
        "stock_quantity": 20,
        "barcode": "1234567890125",
        "section": "Eletrônicos"
    }, headers=login_token())

    assert response.status_code == HTTPStatus.CREATED
    product_id = response.json()["id"]

    response = client.get(f"{version_prefix}/{product_id}", headers=login_token())
    assert response.status_code == HTTPStatus.OK
    assert response.json()["product"]["name"] == "Produto Teste"

    response_get_views = client.get(f"{version_prefix}/{product_id}", headers=login_token())
    assert response_get_views.status_code == HTTPStatus.OK


def test_create_product_barcode_unique():
    product_data = {
        "name": "Produto 1",
        "description": "Primeiro produto",
        "price": 10.0,
        "status": "em estoque",
        "stock_quantity": 5,
        "barcode": "9999999999999",
        "section": "Eletrônicos"
    }
    response1 = client.post(f"{version_prefix}/", json=product_data, headers=login_token())
    assert response1.status_code == HTTPStatus.CREATED

    product_data2 = product_data.copy()
    product_data2["name"] = "Produto 2"
    response2 = client.post(f"{version_prefix}/", json=product_data2, headers=login_token())
    assert response2.status_code == HTTPStatus.BAD_REQUEST
    assert "Código de barras já cadastrado" in response2.text


def test_update_product():
    # Criar um produto para garantir que a lista não esteja vazia
    response = client.post(f"{version_prefix}/", json={
        "name": "Produto Teste Atualização",
        "description": "Descrição do produto para atualização",
        "price": 49.99,
        "status": "em estoque",
        "stock_quantity": 50,
        "barcode": "1234567890126",
        "section": "Eletrônicos"
    }, headers=login_token())

    assert response.status_code == HTTPStatus.CREATED
    product_id = response.json()["id"]

    update_data = {
        "name": "Produto Atualizado",
        "price": 89.99,
        "status": "em reposição",
        "stock_quantity": 30,
        "section": "Casa",
        "expiration_date": "2031-01-01T00:00:00",
        "images": ["http://example.com/img3.jpg"]
    }
    response = client.put(f"{version_prefix}/{product_id}", json=update_data, headers=login_token())
    assert response.status_code == HTTPStatus.OK

    updated_product = response.json()
    assert updated_product["name"] == "Produto Atualizado"
    assert updated_product["price"] == 89.99
    assert updated_product["status"] == "em reposição"
    assert updated_product["stock_quantity"] == 30
    assert updated_product["section"] == "Casa"
    assert updated_product["expiration_date"].startswith("2031-01-01")
    assert updated_product["images"] == ["http://example.com/img3.jpg"]


def test_delete_product():
    # Criar um produto para garantir que a lista não esteja vazia
    response = client.post(f"{version_prefix}/", json={
        "name": "Produto Teste Deleção",
        "description": "Descrição do produto para deleção",
        "price": 29.99,
        "status": "em estoque",
        "stock_quantity": 10,
        "barcode": "1234567890127",
        "section": "Eletrônicos"
    }, headers=login_token())

    assert response.status_code == HTTPStatus.CREATED
    product_id = response.json()["id"]

    response = client.delete(f"{version_prefix}/{product_id}", headers=login_token())
    assert response.status_code == HTTPStatus.NO_CONTENT
    # assert response.json() == {"detail": "Produto deletado com sucesso"}

    response = client.get(f"{version_prefix}/{product_id}", headers=login_token())
    assert response.status_code == HTTPStatus.NOT_FOUND
    # assert response.json() == {"detail": "Produto não encontrado"}
