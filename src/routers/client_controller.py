from http import HTTPStatus
from typing_extensions import List
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, Response

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

from typing import Annotated, Optional
from auth import User, get_current_active_user, get_current_admin_user


router = APIRouter()


@router.post("/", status_code=HTTPStatus.CREATED, response_model=ClientResponse)
async def create_client_endpoint(client: ClientCreate, db: Session = Depends(get_db), user: User = Depends(get_current_admin_user)):
    """
    **Criação de um novo Cliente**

    Este endpoint permite criar um novo cliente na base de dados.
    É necessário que o usuário esteja autenticado e tenha permissões de administrador.

    **Corpo da Requisição (`ClientCreate`):**
    - `name`: Nome completo do cliente (string, obrigatório, mínimo 3 caracteres).
    - `email`: Endereço de e-mail do cliente (string, obrigatório, deve ser único, formato válido de email).
    - `phone`: Número de telefone do cliente (string, opcional, formato: (XX) XXXXX-XXXX).
    - `cpf`: CPF do cliente (string, obrigatório, deve ser único, formato: XXXXXXXXXXX).
    - `address`: Objeto contendo o endereço completo (obrigatório):
      - `street`: Nome da rua (string, obrigatório)
      - `number`: Número do endereço (string, obrigatório)
      - `complement`: Complemento do endereço (string, opcional)
      - `neighborhood`: Bairro (string, obrigatório)
      - `city`: Cidade (string, obrigatório)
      - `state`: Estado (string, obrigatório, 2 caracteres)
      - `zip_code`: CEP (string, obrigatório, formato: XXXXXXXX)

    **Regras de Negócio:**
    - O campo `email` deve ser único na base de dados.
    - O campo `cpf` deve ser único na base de dados e válido.
    - Apenas usuários autenticados com permissões de administrador podem criar clientes.
    - O CPF é validado quanto à sua estrutura e dígitos verificadores.

    **Casos de Uso:**
    - Registrar um novo cliente no sistema.
    - Utilizado por administradores para adicionar novos clientes.
    - Cadastro inicial de clientes para permitir a realização de pedidos.

    **Exemplo de Requisição:**
    ```json
    {
      "name": "João da Silva",
      "email": "joao.silva@email.com",
      "phone": "(11) 98765-4321",
      "cpf": "52998224725",
      "address": {
        "street": "Rua das Flores",
        "number": "123",
        "complement": "Apto 45",
        "neighborhood": "Centro",
        "city": "São Paulo",
        "state": "SP",
        "zip_code": "01234567"
      }
    }
    ```

    **Exemplo de Resposta (Cliente Criado - 201):**
    ```json
    {
      "id": 1,
      "name": "João da Silva",
      "email": "joao.silva@email.com",
      "phone": "(11) 98765-4321",
      "cpf": "52998224725",
      "address": {
        "street": "Rua das Flores",
        "number": "123",
        "complement": "Apto 45",
        "neighborhood": "Centro",
        "city": "São Paulo",
        "state": "SP",
        "zip_code": "01234567"
      },
      "created_at": "2024-03-20T10:00:00.000Z",
      "updated_at": "2024-03-20T10:00:00.000Z"
    }
    ```

    **Códigos de Erro:**
    - `400 Bad Request`: 
      - Email já cadastrado
      - CPF já cadastrado
      - CPF inválido
      - Dados de endereço incompletos
      - Formato de email inválido
      - Formato de telefone inválido
      - Formato de CEP inválido
    - `401 Unauthorized`: Token de autenticação não fornecido ou inválido
    - `403 Forbidden`: Usuário não tem permissões de administrador

    **Exemplo de Resposta de Erro (400 - Email Duplicado):**
    ```json
    {
      "detail": "Email já cadastrado"
    }
    ```

    **Exemplo de Resposta de Erro (400 - CPF Inválido):**
    ```json
    {
      "detail": "CPF inválido"
    }
    ```

    **Exemplo de Resposta de Erro (401 - Não Autenticado):**
    ```json
    {
      "detail": "Não foi possível validar as credenciais",
      "headers": {
        "WWW-Authenticate": "Bearer"
      }
    }
    ```

    **Exemplo de Resposta de Erro (403 - Sem Permissão):**
    ```json
    {
      "detail": "Não autorizado: apenas administradores podem realizar esta ação."
    }
    ```
    """
    return await create_client(client, db)


@router.get("/", response_model=PaginatedClientResponse)
async def list_clients_endpoint(
    skip: int = Query(0, description="Número de registros para pular (paginação)"),
    limit: int = Query(10, description="Número máximo de registros por página"),
    search: Optional[str] = Query(None, description="Termo de busca para filtrar clientes por nome, email ou CPF"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    """
    **Listagem de Clientes**

    Este endpoint permite listar todos os clientes cadastrados no sistema.
    É necessário que o usuário esteja autenticado para acessar esta funcionalidade.

    **Parâmetros de Consulta:**
    - `skip`: Número de registros para pular (paginação, padrão: 0)
    - `limit`: Número máximo de registros por página (padrão: 10, máximo: 100)
    - `search`: Termo de busca opcional para filtrar clientes por:
      - Nome (busca parcial, case-insensitive)
      - Email (busca exata)
      - CPF (busca exata)

    **Regras de Negócio:**
    - A listagem é paginada para melhor performance
    - O parâmetro `limit` não pode exceder 100 registros por página
    - A busca é case-insensitive para o nome do cliente
    - A busca por email e CPF é exata
    - Apenas usuários autenticados podem listar clientes

    **Casos de Uso:**
    - Visualização da lista completa de clientes
    - Busca de clientes específicos
    - Navegação paginada através dos registros
    - Filtragem de clientes por diferentes critérios

    **Exemplo de Requisição:**
    ```
    GET /clients/?skip=0&limit=10&search=joao
    ```

    **Exemplo de Resposta (200 - Sucesso):**
    ```json
    {
      "clients": [
        {
          "id": 1,
          "name": "João da Silva",
          "email": "joao.silva@email.com",
          "phone": "(11) 98765-4321",
          "cpf": "52998224725",
          "address": {
            "street": "Rua das Flores",
            "number": "123",
            "complement": "Apto 45",
            "neighborhood": "Centro",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234567"
          },
          "created_at": "2024-03-20T10:00:00.000Z",
          "updated_at": "2024-03-20T10:00:00.000Z"
        }
      ],
      "total": 1,
      "page": 1,
      "size": 10,
      "pages": 1
    }
    ```

    **Exemplo de Resposta (200 - Lista Vazia):**
    ```json
    {
      "clients": [],
      "total": 0,
      "page": 1,
      "size": 10,
      "pages": 0
    }
    ```

    **Códigos de Erro:**
    - `400 Bad Request`: 
      - Valor inválido para o parâmetro `limit` (deve ser entre 1 e 100)
      - Valor inválido para o parâmetro `skip` (deve ser >= 0)
    - `401 Unauthorized`: Token de autenticação não fornecido ou inválido

    **Exemplo de Resposta de Erro (400 - Parâmetro Inválido):**
    ```json
    {
      "detail": "O parâmetro 'limit' deve estar entre 1 e 100"
    }
    ```

    **Exemplo de Resposta de Erro (401 - Não Autenticado):**
    ```json
    {
      "detail": "Não foi possível validar as credenciais",
      "headers": {
        "WWW-Authenticate": "Bearer"
      }
    }
    ```

    **Notas:**
    - A paginação começa em 0 (zero)
    - O campo `total` representa o número total de registros encontrados
    - O campo `pages` representa o número total de páginas disponíveis
    - O campo `page` representa a página atual
    - O campo `size` representa o tamanho da página atual
    """
    page = (skip // limit) + 1 if limit else 1
    page_size = limit
    clients, total = await list_clients(db, page=page, page_size=page_size, search=search)
    clients_response = [ClientResponse.from_orm(client) for client in clients]
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return {
        'clients': clients_response,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages
    }


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client_by_id_endpoint(
    client_id: int = Path(..., description="ID do cliente a ser buscado", ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    """
    **Busca de Cliente por ID**

    Este endpoint permite buscar os detalhes de um cliente específico através do seu ID.
    É necessário que o usuário esteja autenticado para acessar esta funcionalidade.

    **Parâmetros de Caminho:**
    - `client_id`: ID do cliente (inteiro, obrigatório, maior que zero)

    **Regras de Negócio:**
    - O ID do cliente deve existir na base de dados
    - Apenas usuários autenticados podem buscar clientes
    - O ID deve ser um número inteiro positivo

    **Casos de Uso:**
    - Visualização detalhada de um cliente específico
    - Verificação de dados do cliente antes de operações
    - Consulta rápida de informações do cliente

    **Exemplo de Requisição:**
    ```
    GET /clients/1
    ```

    **Exemplo de Resposta (200 - Sucesso):**
    ```json
    {
      "id": 1,
      "name": "João da Silva",
      "email": "joao.silva@email.com",
      "phone": "(11) 98765-4321",
      "cpf": "52998224725",
      "address": {
        "street": "Rua das Flores",
        "number": "123",
        "complement": "Apto 45",
        "neighborhood": "Centro",
        "city": "São Paulo",
        "state": "SP",
        "zip_code": "01234567"
      },
      "active": true,
      "created_at": "2024-03-20T10:00:00.000Z",
      "updated_at": "2024-03-20T10:00:00.000Z"
    }
    ```

    **Códigos de Erro:**
    - `400 Bad Request`: ID do cliente inválido (menor que 1)
    - `401 Unauthorized`: Token de autenticação não fornecido ou inválido
    - `404 Not Found`: Cliente não encontrado

    **Exemplo de Resposta de Erro (400 - ID Inválido):**
    ```json
    {
      "detail": "O ID do cliente deve ser maior que zero"
    }
    ```

    **Exemplo de Resposta de Erro (401 - Não Autenticado):**
    ```json
    {
      "detail": "Não foi possível validar as credenciais",
      "headers": {
        "WWW-Authenticate": "Bearer"
      }
    }
    ```

    **Exemplo de Resposta de Erro (404 - Cliente Não Encontrado):**
    ```json
    {
      "detail": "Cliente não encontrado"
    }
    ```

    **Notas:**
    - O ID do cliente é um número sequencial gerado automaticamente
    - Todos os campos do cliente são retornados na resposta
    - As datas são retornadas no formato ISO 8601
    """
    client = await get_client_by_id(client_id, db)
    if not client:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cliente não encontrado")
    return ClientResponse.from_orm(client)


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client_endpoint(
    client_id: int = Path(..., description="ID do cliente a ser atualizado", ge=1),
    client_update: ClientUpdate = Body(..., description="Dados do cliente a serem atualizados"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin_user)
):
    """
    **Atualização de Cliente**

    Este endpoint permite atualizar os dados de um cliente existente.
    É necessário que o usuário esteja autenticado e tenha permissões de administrador.

    **Parâmetros de Caminho:**
    - `client_id`: ID do cliente a ser atualizado (inteiro, obrigatório, maior que zero)

    **Corpo da Requisição (`ClientUpdate`):**
    - `name`: Nome completo do cliente (string, opcional, mínimo 3 caracteres)
    - `email`: Endereço de e-mail do cliente (string, opcional, deve ser único, formato válido de email)
    - `phone`: Número de telefone do cliente (string, opcional, formato: (XX) XXXXX-XXXX)
    - `address`: Objeto contendo o endereço completo (opcional):
      - `street`: Nome da rua (string, opcional)
      - `number`: Número do endereço (string, opcional)
      - `complement`: Complemento do endereço (string, opcional)
      - `neighborhood`: Bairro (string, opcional)
      - `city`: Cidade (string, opcional)
      - `state`: Estado (string, opcional, 2 caracteres)
      - `zip_code`: CEP (string, opcional, formato: XXXXXXXX)

    **Regras de Negócio:**
    - O ID do cliente deve existir na base de dados
    - Apenas usuários autenticados com permissões de administrador podem atualizar clientes
    - O campo `email` deve ser único na base de dados (se fornecido)
    - O CPF não pode ser alterado após a criação do cliente
    - Todos os campos são opcionais na atualização
    - Apenas os campos fornecidos serão atualizados

    **Casos de Uso:**
    - Atualização de dados cadastrais do cliente
    - Correção de informações incorretas
    - Atualização de endereço do cliente
    - Alteração de contato (telefone/email)

    **Exemplo de Requisição:**
    ```
    PUT /clients/1
    ```
    ```json
    {
      "name": "João Silva Atualizado",
      "phone": "(11) 91234-5678",
      "address": {
        "street": "Avenida Principal",
        "number": "456",
        "complement": "Sala 789",
        "neighborhood": "Jardim",
        "city": "São Paulo",
        "state": "SP",
        "zip_code": "04567890"
      }
    }
    ```

    **Exemplo de Resposta (200 - Sucesso):**
    ```json
    {
      "id": 1,
      "name": "João Silva Atualizado",
      "email": "joao.silva@email.com",
      "phone": "(11) 91234-5678",
      "cpf": "52998224725",
      "address": {
        "street": "Avenida Principal",
        "number": "456",
        "complement": "Sala 789",
        "neighborhood": "Jardim",
        "city": "São Paulo",
        "state": "SP",
        "zip_code": "04567890"
      },
      "created_at": "2024-03-20T10:00:00.000Z",
      "updated_at": "2024-03-20T11:00:00.000Z"
    }
    ```

    **Códigos de Erro:**
    - `400 Bad Request`: 
      - Email já cadastrado (se fornecido)
      - Formato de email inválido
      - Formato de telefone inválido
      - Formato de CEP inválido
      - ID do cliente inválido (menor que 1)
    - `401 Unauthorized`: Token de autenticação não fornecido ou inválido
    - `403 Forbidden`: Usuário não tem permissões de administrador
    - `404 Not Found`: Cliente não encontrado

    **Exemplo de Resposta de Erro (400 - Email Duplicado):**
    ```json
    {
      "detail": "Email já cadastrado"
    }
    ```

    **Exemplo de Resposta de Erro (401 - Não Autenticado):**
    ```json
    {
      "detail": "Não foi possível validar as credenciais",
      "headers": {
        "WWW-Authenticate": "Bearer"
      }
    }
    ```

    **Exemplo de Resposta de Erro (403 - Sem Permissão):**
    ```json
    {
      "detail": "Não autorizado: apenas administradores podem realizar esta ação."
    }
    ```

    **Exemplo de Resposta de Erro (404 - Cliente Não Encontrado):**
    ```json
    {
      "detail": "Cliente não encontrado"
    }
    ```

    **Notas:**
    - Apenas os campos fornecidos na requisição serão atualizados
    - O campo `updated_at` é atualizado automaticamente
    - O campo `cpf` não pode ser alterado após a criação do cliente
    - As datas são retornadas no formato ISO 8601
    """
    return await update_client(client_id, client_update, db)


@router.delete("/{client_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_client_endpoint(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    **Exclusão de um Cliente**

    Este endpoint permite que um usuário autenticado (com permissão de administrador) exclua um cliente existente, removendo-o permanentemente do banco de dados.

    **Parâmetros de Caminho:**
    - `client_id`: ID do cliente a ser excluído (integer, obrigatório, maior que zero).

    **Regras de Negócio:**
    - É necessário que o usuário esteja autenticado e possua permissão de administrador (is_admin=True) para excluir um cliente.
    - O `client_id` fornecido deve corresponder a um cliente existente.
    - A exclusão é permanente e remove o cliente do banco de dados.
    - Não é possível excluir um cliente que possui pedidos associados a ele.
    - Se o cliente tiver pedidos, a exclusão será bloqueada e retornará um erro 409 Conflict.

    **Casos de Uso:**
    - Um administrador remove um cliente que não deseja mais utilizar o sistema.
    - Integração com um sistema externo que exclui clientes (por exemplo, após um processo de limpeza de dados).

    **Exemplo de Requisição:**
    ```
    DELETE /clients/456
    ```

    **Exemplo de Resposta (Cliente Excluído):**
    ```json
    {
      "message": "Cliente excluído com sucesso."
    }
    ```

    **Códigos de Erro:**
    - `400 Bad Request`: ID do cliente inválido (menor que 1)
    - `401 Unauthorized`: O usuário não está autenticado ou não possui permissão de administrador
    - `404 Not Found`: O cliente com o ID fornecido não foi encontrado
    - `409 Conflict`: O cliente possui pedidos associados e não pode ser excluído

    **Exemplo de Resposta de Erro (409 - Cliente com Pedidos):**
    ```json
    {
      "detail": "Não é possível excluir o cliente pois existem pedidos associados a ele"
    }
    ```

    **Notas:**
    - A exclusão é permanente e não pode ser desfeita
    - Recomenda-se fazer backup dos dados antes de excluir clientes
    - Considere usar a atualização de status para "inactive" em vez da exclusão
    - Clientes com pedidos devem ser mantidos no sistema por questões de histórico e auditoria
    """
    await delete_client(id=client_id, db=db)
    return Response(status_code=HTTPStatus.NO_CONTENT)
 