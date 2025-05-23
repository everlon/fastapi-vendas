from http import HTTPStatus
from typing_extensions import List
from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy.orm import Session
from database import get_db

from src.services.client_service import (
    create_client,
    list_clients,
    get_client_by_id,
    update_client,
    delete_client)

from src.schemas.client import (
    ClientCreate,
    ClientResponse,
    ClientUpdate,
    PaginatedClientResponse
)

from typing import Annotated
from auth import User, get_current_active_user


router = APIRouter()


@router.post("/", status_code=HTTPStatus.CREATED, response_model=ClientResponse)
async def create_client_endpoint(client: ClientCreate, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    **Criação de um novo Cliente**

    Este endpoint permite criar um novo cliente na base de dados.
    É necessário que o usuário esteja autenticado para realizar esta operação.

    **Corpo da Requisição (`ClientCreate`):**
    - `name`: Nome completo do cliente (string, obrigatório).
    - `email`: Endereço de e-mail do cliente (string, obrigatório, deve ser único).
    - `phone`: Número de telefone do cliente (string, opcional).
    - `address`: Endereço completo do cliente (string, opcional).

    **Regras de Negócio:**
    - O campo `email` deve ser único na base de dados.
    - Apenas usuários autenticados podem criar clientes.

    **Casos de Uso:**
    - Registrar um novo cliente no sistema.
    - Utilizado por administradores ou usuários com permissão para adicionar novos clientes.

    **Exemplo de Requisição:**
    ```json
    {
      "name": "Cliente Exemplo",
      "email": "cliente.exemplo@email.com",
      "phone": "+55 11 98765-4321",
      "address": "Rua Exemplo, 123, Bairro - Cidade - UF"
    }
    ```

    **Exemplo de Resposta (Cliente Criado):**
    ```json
    {
      "id": 1,
      "name": "Cliente Exemplo",
      "email": "cliente.exemplo@email.com",
      "phone": "+55 11 98765-4321",
      "address": "Rua Exemplo, 123, Bairro - Cidade - UF",
      "created_at": "2023-01-01T10:00:00.000Z",
      "updated_at": "2023-01-01T10:00:00.000Z"
    }
    ```
    """
    return await create_client(client, db)


@router.get("/", status_code=HTTPStatus.OK, response_model=PaginatedClientResponse)
async def list_clients_endpoint(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(10, ge=1, le=100, description="Número de itens por página"),
    search: str = Query(None, description="Filtrar por busca em nome ou email do cliente"),
    user: User = Depends(get_current_active_user)):
    """
    **Listagem e Busca de Clientes (Paginada)**

    Este endpoint permite listar clientes com opções de busca e paginação.
    É necessário que o usuário esteja autenticado para acessar esta lista.

    **Parâmetros de Query:**
    - `page`: Número da página (padrão: 1, mínimo: 1).
    - `page_size`: Número de itens por página (padrão: 10, mínimo: 1, máximo: 100).
    - `search`: Termo para buscar no nome ou e-mail do cliente (opcional).

    **Regras de Negócio:**
    - A paginação é obrigatória.
    - A busca por termo (`search`) procura tanto no nome quanto no e-mail do cliente e é case-insensitive.
    - Apenas usuários autenticados podem listar clientes.

    **Casos de Uso:**
    - Exibir a lista de clientes para usuários com permissão (ex: administradores).
    - Permitir a busca rápida de clientes por nome ou e-mail.
    - Implementar a navegação paginada na interface de gerenciamento de clientes.

    **Exemplo de Resposta:**
    ```json
    {
      "clients": [
        {
          "id": 1,
          "name": "Cliente Exemplo",
          "email": "cliente.exemplo@email.com",
          "phone": "+55 11 98765-4321",
          "address": "Rua Exemplo, 123, Bairro - Cidade - UF",
          "created_at": "2023-01-01T10:00:00.000Z",
          "updated_at": "2023-01-01T10:00:00.000Z"
        }
      ],
      "total": 50,
      "page": 1,
      "page_size": 10,
      "total_pages": 5
    }
    ```
    """
    clients, total = await list_clients(
        db,
        page=page,
        page_size=page_size,
        search=search)

    response_data = {
        "clients": clients,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

    return response_data


@router.get("/{id}", status_code=HTTPStatus.OK, response_model=ClientResponse)
async def get_client_by_id_endpoint(id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    **Obtenção de Cliente por ID**

    Este endpoint permite obter os detalhes completos de um cliente específico utilizando seu ID.
    É necessário que o usuário esteja autenticado para realizar esta operação.

    **Parâmetros de Path:**
    - `id`: O ID único do cliente a ser buscado (integer).

    **Regras de Negócio:**
    - O ID fornecido deve corresponder a um cliente existente na base de dados.
    - Apenas usuários autenticados podem obter detalhes de clientes.
    - Retorna status 404 se o cliente não for encontrado.

    **Casos de Uso:**
    - Exibir a página de detalhes de um cliente específico.
    - Obter informações de um cliente para edição ou visualização.

    **Exemplo de Resposta:**
    ```json
    {
      "id": 1,
      "name": "Cliente Exemplo",
      "email": "cliente.exemplo@email.com",
      "phone": "+55 11 98765-4321",
      "address": "Rua Exemplo, 123, Bairro - Cidade - UF",
      "created_at": "2023-01-01T10:00:00.000Z",
      "updated_at": "2023-01-01T10:00:00.000Z"
    }
    ```
    """
    client = await get_client_by_id(id, db)

    if not client:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cliente não encontrado")

    return client


@router.put("/{id}", status_code=HTTPStatus.OK, response_model=ClientResponse)
async def update_client_endpoint(id: int, client_data: ClientUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    **Atualização de Cliente por ID**

    Este endpoint permite atualizar parcialmente ou totalmente os dados de um cliente existente utilizando seu ID.
    É necessário que o usuário esteja autenticado para realizar esta operação.

    **Parâmetros de Path:**
    - `id`: O ID único do cliente a ser atualizado (integer).

    **Corpo da Requisição (`ClientUpdate`):**
    Permite enviar apenas os campos que deseja atualizar. Os campos opcionais incluem `name`, `email`, `phone`, e `address`.

    **Regras de Negócio:**
    - O ID fornecido deve corresponder a um cliente existente na base de dados.
    - O campo `email`, se fornecido e diferente do atual, deve ser único na base de dados.
    - Apenas usuários autenticados podem atualizar clientes.
    - Retorna status 404 se o cliente não for encontrado.

    **Casos de Uso:**
    - Corrigir informações de cadastro de um cliente (ex: nome, endereço).
    - Atualizar o contato telefônico ou e-mail de um cliente.

    **Exemplo de Requisição:**
    ```json
    {
      "phone": "+55 11 99887-7665",
      "address": "Nova Rua, 456, Outro Bairro - Outra Cidade - MG"
    }
    ```

    **Exemplo de Resposta (Cliente Atualizado):**
    ```json
    {
      "id": 1,
      "name": "Cliente Exemplo",
      "email": "cliente.exemplo@email.com",
      "phone": "+55 11 99887-7665",
      "address": "Nova Rua, 456, Outro Bairro - Outra Cidade - MG",
      "created_at": "2023-01-01T10:00:00.000Z",
      "updated_at": "2023-01-01T10:20:00.000Z" # Data de atualização mudaria
    }
    ```
    """
    updated_client = await update_client(id, client_data, db)

    return updated_client


@router.delete("/{id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_client_endpoint(id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    **Exclusão de Cliente por ID**

    Este endpoint permite excluir um cliente existente utilizando seu ID.
    É necessário que o usuário esteja autenticado para realizar esta operação.

    **Parâmetros de Path:**
    - `id`: O ID único do cliente a ser excluído (integer).

    **Regras de Negócio:**
    - O ID fornecido deve corresponder a um cliente existente na base de dados.
    - Apenas usuários autenticados podem excluir clientes.
    - Retorna status 404 se o cliente não for encontrado.

    **Casos de Uso:**
    - Remover o cadastro de um cliente que não é mais relevante ou que foi cadastrado incorretamente.

    **Resposta de Sucesso:**
    - Retorna status 204 No Content se a exclusão for bem-sucedida.
    """
    await delete_client(id, db)

    return True
