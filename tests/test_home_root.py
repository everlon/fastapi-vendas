from http import HTTPStatus
from fastapi.testclient import TestClient

from app.main import app


def test_root_ok_message_ok():
    client = TestClient(app)
    response = client.get('/')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"message": "Veja bem-vindo(a) a nossa API!"}
