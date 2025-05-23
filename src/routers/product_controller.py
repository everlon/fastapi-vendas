from http import HTTPStatus
from typing_extensions import List
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
# from fastapi.encoders import jsonable_encoder

from sqlalchemy.orm import Session
from database import get_db

from src.services.product_service import (
    create_product,
    list_products,
    get_product_by_id,
    update_product,
    delete_product)

from src.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductByIdResponse,
    PaginatedProductResponse,
    ProductUpdate
)

from typing import Annotated, Optional
from auth import User, get_current_active_user, get_current_admin_user


router = APIRouter()


@router.post("/", status_code=HTTPStatus.CREATED, response_model=ProductResponse)
async def create_product_endpoint(
    product: ProductCreate = Body(..., description="Dados do produto a ser criado"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin_user)
):
    """
    **Criação de um novo Produto**

    Este endpoint permite criar um novo produto na base de dados.
    É necessário que o usuário esteja autenticado e tenha permissões de administrador.

    **Corpo da Requisição (`ProductCreate`):**
    - `name`: Nome do produto (string, obrigatório, mínimo 3 caracteres)
    - `description`: Descrição detalhada do produto (string, opcional)
    - `barcode`: Código de barras do produto (string, obrigatório, deve ser único)
    - `price`: Preço de venda do produto (float, obrigatório, maior que zero)
    - `cost_price`: Preço de custo do produto (float, obrigatório, maior que zero)
    - `stock`: Quantidade em estoque (integer, obrigatório, maior ou igual a zero)
    - `min_stock`: Quantidade mínima em estoque (integer, obrigatório, maior ou igual a zero)
    - `category`: Categoria do produto (string, obrigatório)
    - `brand`: Marca do produto (string, opcional)
    - `expiration_date`: Data de validade do produto (date, opcional, formato: YYYY-MM-DD)
    - `status`: Status do produto (string, obrigatório, enum: "active", "inactive", "discontinued")

    **Regras de Negócio:**
    - O campo `barcode` deve ser único na base de dados
    - O preço de venda (`price`) deve ser maior que o preço de custo (`cost_price`)
    - O estoque (`stock`) não pode ser negativo
    - O estoque mínimo (`min_stock`) não pode ser negativo
    - A data de validade (`expiration_date`) deve ser futura (se fornecida)
    - Apenas usuários autenticados com permissões de administrador podem criar produtos
    - O status inicial do produto deve ser "active"

    **Casos de Uso:**
    - Cadastro de novos produtos no sistema
    - Adição de produtos ao catálogo
    - Registro de produtos para controle de estoque
    - Inclusão de produtos para venda

    **Exemplo de Requisição:**
    ```json
    {
      "name": "Arroz Integral 1kg",
      "description": "Arroz integral tipo 1, embalagem de 1kg",
      "barcode": "7891234567890",
      "price": 12.90,
      "cost_price": 8.50,
      "stock": 100,
      "min_stock": 20,
      "category": "Alimentos",
      "brand": "Marca Premium",
      "expiration_date": "2024-12-31",
      "status": "active"
    }
    ```

    **Exemplo de Resposta (201 - Sucesso):**
    ```json
    {
      "id": 1,
      "name": "Arroz Integral 1kg",
      "description": "Arroz integral tipo 1, embalagem de 1kg",
      "barcode": "7891234567890",
      "price": 12.90,
      "cost_price": 8.50,
      "stock": 100,
      "min_stock": 20,
      "category": "Alimentos",
      "brand": "Marca Premium",
      "expiration_date": "2024-12-31",
      "status": "active",
      "created_at": "2024-03-20T10:00:00.000Z",
      "updated_at": "2024-03-20T10:00:00.000Z"
    }
    ```

    **Códigos de Erro:**
    - `400 Bad Request`: 
      - Código de barras já cadastrado
      - Preço de venda menor que preço de custo
      - Estoque negativo
      - Estoque mínimo negativo
      - Data de validade no passado
      - Status inválido
      - Campos obrigatórios não fornecidos
    - `401 Unauthorized`: Token de autenticação não fornecido ou inválido
    - `403 Forbidden`: Usuário não tem permissões de administrador

    **Exemplo de Resposta de Erro (400 - Código de Barras Duplicado):**
    ```json
    {
      "detail": "Código de barras já cadastrado"
    }
    ```

    **Exemplo de Resposta de Erro (400 - Preço Inválido):**
    ```json
    {
      "detail": "O preço de venda deve ser maior que o preço de custo"
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

    **Notas:**
    - O código de barras deve ser único para cada produto
    - O preço de venda deve ser maior que o preço de custo para garantir margem de lucro
    - A data de validade é opcional, mas quando fornecida deve ser futura
    - O status inicial do produto é sempre "active"
    - As datas são retornadas no formato ISO 8601
    """
    return await create_product(product, db)


@router.get("/", response_model=List[ProductResponse])
async def list_products_endpoint(
    skip: int = Query(0, description="Número de registros para pular (paginação)"),
    limit: int = Query(10, description="Número máximo de registros por página"),
    search: Optional[str] = Query(None, description="Termo de busca para filtrar produtos por nome, descrição ou código de barras"),
    category: Optional[str] = Query(None, description="Filtrar produtos por categoria"),
    status: Optional[str] = Query(None, description="Filtrar produtos por status (active, inactive, discontinued)"),
    min_price: Optional[float] = Query(None, description="Filtrar produtos com preço maior ou igual ao valor informado"),
    max_price: Optional[float] = Query(None, description="Filtrar produtos com preço menor ou igual ao valor informado"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    """
    **Listagem de Produtos**

    Este endpoint permite listar todos os produtos cadastrados no sistema.
    É necessário que o usuário esteja autenticado para acessar esta funcionalidade.

    **Parâmetros de Consulta:**
    - `skip`: Número de registros para pular (paginação, padrão: 0)
    - `limit`: Número máximo de registros por página (padrão: 10, máximo: 100)
    - `search`: Termo de busca opcional para filtrar produtos por:
      - Nome (busca parcial, case-insensitive)
      - Descrição (busca parcial, case-insensitive)
      - Código de barras (busca exata)
    - `category`: Filtrar produtos por categoria específica
    - `status`: Filtrar produtos por status (active, inactive, discontinued)
    - `min_price`: Filtrar produtos com preço maior ou igual ao valor informado
    - `max_price`: Filtrar produtos com preço menor ou igual ao valor informado

    **Regras de Negócio:**
    - A listagem é paginada para melhor performance
    - O parâmetro `limit` não pode exceder 100 registros por página
    - A busca é case-insensitive para nome e descrição
    - A busca por código de barras é exata
    - Os filtros de preço podem ser combinados para definir um intervalo
    - Apenas usuários autenticados podem listar produtos

    **Casos de Uso:**
    - Visualização do catálogo de produtos
    - Busca de produtos específicos
    - Filtragem de produtos por categoria
    - Consulta de produtos por faixa de preço
    - Verificação de produtos ativos/inativos
    - Navegação paginada através dos registros

    **Exemplo de Requisição:**
    ```
    GET /products/?skip=0&limit=10&search=arroz&category=Alimentos&min_price=10&max_price=20&status=active
    ```

    **Exemplo de Resposta (200 - Sucesso):**
    ```json
    {
      "items": [
        {
          "id": 1,
          "name": "Arroz Integral 1kg",
          "description": "Arroz integral tipo 1, embalagem de 1kg",
          "barcode": "7891234567890",
          "price": 12.90,
          "cost_price": 8.50,
          "stock": 100,
          "min_stock": 20,
          "category": "Alimentos",
          "brand": "Marca Premium",
          "expiration_date": "2024-12-31",
          "status": "active",
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
      "items": [],
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
      - Valor inválido para o parâmetro `status` (deve ser um dos valores permitidos)
      - Valor inválido para os parâmetros de preço (devem ser números positivos)
    - `401 Unauthorized`: Token de autenticação não fornecido ou inválido

    **Exemplo de Resposta de Erro (400 - Parâmetro Inválido):**
    ```json
    {
      "detail": "O parâmetro 'limit' deve estar entre 1 e 100"
    }
    ```

    **Exemplo de Resposta de Erro (400 - Status Inválido):**
    ```json
    {
      "detail": "Status inválido. Valores permitidos: active, inactive, discontinued"
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
    - Os filtros podem ser combinados para refinar a busca
    - A busca por texto é case-insensitive
    """
    return await list_products(skip, limit, search, category, status, min_price, max_price, db)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product_by_id_endpoint(
    product_id: int = Path(..., description="ID do produto a ser buscado", ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    """
    **Busca de Produto por ID**

    Este endpoint permite buscar os detalhes de um produto específico através do seu ID.
    É necessário que o usuário esteja autenticado para acessar esta funcionalidade.

    **Parâmetros de Caminho:**
    - `product_id`: ID do produto (inteiro, obrigatório, maior que zero)

    **Regras de Negócio:**
    - O ID do produto deve existir na base de dados
    - Apenas usuários autenticados podem buscar produtos
    - O ID deve ser um número inteiro positivo
    - Produtos inativos ou descontinuados também podem ser consultados

    **Casos de Uso:**
    - Visualização detalhada de um produto específico
    - Verificação de dados do produto antes de operações
    - Consulta rápida de informações do produto
    - Verificação de estoque e preços

    **Exemplo de Requisição:**
    ```
    GET /products/1
    ```

    **Exemplo de Resposta (200 - Sucesso):**
    ```json
    {
      "id": 1,
      "name": "Arroz Integral 1kg",
      "description": "Arroz integral tipo 1, embalagem de 1kg",
      "barcode": "7891234567890",
      "price": 12.90,
      "cost_price": 8.50,
      "stock": 100,
      "min_stock": 20,
      "category": "Alimentos",
      "brand": "Marca Premium",
      "expiration_date": "2024-12-31",
      "status": "active",
      "created_at": "2024-03-20T10:00:00.000Z",
      "updated_at": "2024-03-20T10:00:00.000Z"
    }
    ```

    **Códigos de Erro:**
    - `400 Bad Request`: ID do produto inválido (menor que 1)
    - `401 Unauthorized`: Token de autenticação não fornecido ou inválido
    - `404 Not Found`: Produto não encontrado

    **Exemplo de Resposta de Erro (400 - ID Inválido):**
    ```json
    {
      "detail": "O ID do produto deve ser maior que zero"
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

    **Exemplo de Resposta de Erro (404 - Produto Não Encontrado):**
    ```json
    {
      "detail": "Produto não encontrado"
    }
    ```

    **Notas:**
    - O ID do produto é um número sequencial gerado automaticamente
    - Todos os campos do produto são retornados na resposta
    - As datas são retornadas no formato ISO 8601
    - O campo `status` indica se o produto está ativo, inativo ou descontinuado
    - O campo `expiration_date` é opcional e pode ser nulo
    """
    return await get_product_by_id(product_id, db)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product_endpoint(
    product_id: int = Path(..., description="ID do produto a ser atualizado", ge=1),
    product_update: ProductUpdate = Body(..., description="Dados do produto a serem atualizados"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin_user)
):
    """
    **Atualização de Produto**

    Este endpoint permite atualizar os dados de um produto existente.
    É necessário que o usuário esteja autenticado e tenha permissões de administrador.

    **Parâmetros de Caminho:**
    - `product_id`: ID do produto a ser atualizado (inteiro, obrigatório, maior que zero)

    **Corpo da Requisição (`ProductUpdate`):**
    - `name`: Nome do produto (string, opcional, mínimo 3 caracteres)
    - `description`: Descrição detalhada do produto (string, opcional)
    - `price`: Preço de venda do produto (float, opcional, maior que zero)
    - `cost_price`: Preço de custo do produto (float, opcional, maior que zero)
    - `stock`: Quantidade em estoque (integer, opcional, maior ou igual a zero)
    - `min_stock`: Quantidade mínima em estoque (integer, opcional, maior ou igual a zero)
    - `category`: Categoria do produto (string, opcional)
    - `brand`: Marca do produto (string, opcional)
    - `expiration_date`: Data de validade do produto (date, opcional, formato: YYYY-MM-DD)
    - `status`: Status do produto (string, opcional, enum: "active", "inactive", "discontinued")

    **Regras de Negócio:**
    - O ID do produto deve existir na base de dados
    - Apenas usuários autenticados com permissões de administrador podem atualizar produtos
    - O preço de venda (`price`) deve ser maior que o preço de custo (`cost_price`)
    - O estoque (`stock`) não pode ser negativo
    - O estoque mínimo (`min_stock`) não pode ser negativo
    - A data de validade (`expiration_date`) deve ser futura (se fornecida)
    - O código de barras (`barcode`) não pode ser alterado após a criação do produto
    - Todos os campos são opcionais na atualização
    - Apenas os campos fornecidos serão atualizados

    **Casos de Uso:**
    - Atualização de preços do produto
    - Ajuste de estoque
    - Alteração de status do produto
    - Atualização de informações cadastrais
    - Correção de dados incorretos

    **Exemplo de Requisição:**
    ```
    PUT /products/1
    ```
    ```json
    {
      "name": "Arroz Integral 1kg Premium",
      "price": 13.90,
      "cost_price": 9.00,
      "stock": 150,
      "min_stock": 25,
      "brand": "Marca Premium Plus",
      "expiration_date": "2025-01-31",
      "status": "active"
    }
    ```

    **Exemplo de Resposta (200 - Sucesso):**
    ```json
    {
      "id": 1,
      "name": "Arroz Integral 1kg Premium",
      "description": "Arroz integral tipo 1, embalagem de 1kg",
      "barcode": "7891234567890",
      "price": 13.90,
      "cost_price": 9.00,
      "stock": 150,
      "min_stock": 25,
      "category": "Alimentos",
      "brand": "Marca Premium Plus",
      "expiration_date": "2025-01-31",
      "status": "active",
      "created_at": "2024-03-20T10:00:00.000Z",
      "updated_at": "2024-03-20T11:00:00.000Z"
    }
    ```

    **Códigos de Erro:**
    - `400 Bad Request`: 
      - Preço de venda menor que preço de custo
      - Estoque negativo
      - Estoque mínimo negativo
      - Data de validade no passado
      - Status inválido
      - ID do produto inválido (menor que 1)
    - `401 Unauthorized`: Token de autenticação não fornecido ou inválido
    - `403 Forbidden`: Usuário não tem permissões de administrador
    - `404 Not Found`: Produto não encontrado

    **Exemplo de Resposta de Erro (400 - Preço Inválido):**
    ```json
    {
      "detail": "O preço de venda deve ser maior que o preço de custo"
    }
    ```

    **Exemplo de Resposta de Erro (400 - Estoque Negativo):**
    ```json
    {
      "detail": "O estoque não pode ser negativo"
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

    **Exemplo de Resposta de Erro (404 - Produto Não Encontrado):**
    ```json
    {
      "detail": "Produto não encontrado"
    }
    ```

    **Notas:**
    - Apenas os campos fornecidos na requisição serão atualizados
    - O campo `updated_at` é atualizado automaticamente
    - O campo `barcode` não pode ser alterado após a criação do produto
    - A data de validade é opcional, mas quando fornecida deve ser futura
    - As datas são retornadas no formato ISO 8601
    """
    return await update_product(product_id, product_update, db)


@router.delete("/{product_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_product_endpoint(
    product_id: int = Path(..., description="ID do produto a ser excluído", ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin_user)
):
    """
    **Exclusão de Produto**

    Este endpoint permite excluir um produto existente do sistema.
    É necessário que o usuário esteja autenticado e tenha permissões de administrador.

    **Parâmetros de Caminho:**
    - `product_id`: ID do produto a ser excluído (inteiro, obrigatório, maior que zero)

    **Regras de Negócio:**
    - O ID do produto deve existir na base de dados
    - Apenas usuários autenticados com permissões de administrador podem excluir produtos
    - A exclusão é permanente e não pode ser desfeita
    - Produtos com pedidos associados não podem ser excluídos
    - O sistema verifica se existem pedidos antes de permitir a exclusão
    - Produtos inativos ou descontinuados também podem ser excluídos

    **Casos de Uso:**
    - Remoção de produtos duplicados
    - Exclusão de produtos descontinuados
    - Limpeza de cadastros inválidos
    - Remoção de produtos que não são mais comercializados
    - Exclusão de produtos com dados incorretos

    **Exemplo de Requisição:**
    ```
    DELETE /products/1
    ```

    **Exemplo de Resposta (204 - Sucesso):**
    ```
    [Sem corpo de resposta]
    ```

    **Códigos de Erro:**
    - `400 Bad Request`: ID do produto inválido (menor que 1)
    - `401 Unauthorized`: Token de autenticação não fornecido ou inválido
    - `403 Forbidden`: Usuário não tem permissões de administrador
    - `404 Not Found`: Produto não encontrado
    - `409 Conflict`: Produto possui pedidos associados

    **Exemplo de Resposta de Erro (400 - ID Inválido):**
    ```json
    {
      "detail": "O ID do produto deve ser maior que zero"
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

    **Exemplo de Resposta de Erro (404 - Produto Não Encontrado):**
    ```json
    {
      "detail": "Produto não encontrado"
    }
    ```

    **Exemplo de Resposta de Erro (409 - Produto com Pedidos):**
    ```json
    {
      "detail": "Não é possível excluir o produto pois existem pedidos associados a ele"
    }
    ```

    **Notas:**
    - A exclusão é permanente e não pode ser desfeita
    - O sistema verifica automaticamente se existem pedidos associados
    - Recomenda-se fazer backup dos dados antes de excluir produtos
    - A exclusão de um produto não afeta os pedidos existentes
    - Produtos inativos ou descontinuados também podem ser excluídos
    - Considere usar a atualização de status para "inactive" ou "discontinued" em vez da exclusão
    """
    await delete_product(product_id, db)

    return True
