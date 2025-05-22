# Documentação do Projeto InfoG2

## Índice
1. [Visão Geral](#visão-geral)
2. [Arquitetura](#arquitetura)
3. [Configuração do Ambiente](#configuração-do-ambiente)
4. [API](#api)
5. [Banco de Dados](#banco-de-dados)
6. [Desenvolvimento](#desenvolvimento)

## Visão Geral
O InfoG2 é uma API RESTful desenvolvida com FastAPI para gerenciamento de produtos. O sistema permite operações CRUD completas, autenticação de usuários e gerenciamento de estoque.

## Arquitetura
O projeto segue uma arquitetura em camadas:

```
src/
├── routers/     # Controladores da API
├── services/    # Lógica de negócios
├── schemas/     # Modelos Pydantic para validação
└── models/      # Modelos do banco de dados
```

### Componentes Principais
- **Routers**: Endpoints da API e validação de requisições
- **Services**: Implementação da lógica de negócios
- **Schemas**: Definição dos modelos de dados e validação
- **Models**: Mapeamento objeto-relacional (ORM)

## Configuração do Ambiente
### Requisitos
- Python 3.12+
- Docker e Docker Compose
- Poetry (gerenciador de dependências)

### Variáveis de Ambiente
Consulte o arquivo `.env.example` para todas as variáveis de ambiente necessárias.

## API
### Endpoints Principais
- `/auth`: Autenticação e gerenciamento de usuários
- `/products`: Operações CRUD de produtos

### Documentação da API
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Banco de Dados
O projeto utiliza dois bancos de dados:
1. **SQLite**: Para dados principais (produtos)
2. **MongoDB**: Para dados complementares

### Migrations
As migrações são gerenciadas pelo Alembic. Para executar migrações:
```bash
alembic upgrade head
```

## Desenvolvimento
### Setup do Ambiente
1. Clone o repositório
2. Instale as dependências: `poetry install`
3. Configure as variáveis de ambiente
4. Execute as migrações
5. Inicie o servidor: `uvicorn app.main:app --reload`

### Testes
```bash
poetry run pytest
```

### Convenções de Código
- PEP 8
- Docstrings em todas as funções e classes
- Type hints em todo o código
- Commits seguindo Conventional Commits 