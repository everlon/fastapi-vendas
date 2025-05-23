# InfoG2 - Sistema de Gestão de Pedidos

Sistema de gestão de pedidos desenvolvido em Python com FastAPI, incluindo funcionalidades de cadastro de clientes, produtos, pedidos e usuários.

## 🚀 Tecnologias Utilizadas

- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL
- Docker
- Docker Compose
- Pytest
- JWT para autenticação

## 📋 Pré-requisitos

- Docker
- Docker Compose
- Git

## 🔧 Instalação e Execução

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/infog2.git
cd infog2
```

2. Configure as variáveis de ambiente:
```bash
cp .env.example .env
```
Edite o arquivo `.env` com suas configurações locais.

3. Inicie os containers com Docker Compose:
```bash
docker-compose up -d
```

4. Acesse a aplicação:
- API: http://localhost:8000
- Documentação Swagger: http://localhost:8000/docs
- Documentação ReDoc: http://localhost:8000/redoc

## 🧪 Testes

### Executando os Testes

1. **Testes Unitários**
```bash
# Executar todos os testes unitários
docker-compose exec infog2 pytest tests/unit/ -v

# Executar testes de um módulo específico
docker-compose exec infog2 pytest tests/unit/test_client_service.py -v
docker-compose exec infog2 pytest tests/unit/test_product_service.py -v
docker-compose exec infog2 pytest tests/unit/test_order_service.py -v
docker-compose exec infog2 pytest tests/unit/test_user_service.py -v
```

2. **Testes de Integração**
```bash
# Executar todos os testes de integração
docker-compose exec infog2 pytest tests/test_clients_operations.py -v
docker-compose exec infog2 pytest tests/test_products_operations.py -v
docker-compose exec infog2 pytest tests/test_orders_operations.py -v
docker-compose exec infog2 pytest tests/test_auth_permissions.py -v
```

3. **Testes de Autenticação**
```bash
# Executar testes de autenticação e permissões
docker-compose exec infog2 pytest tests/test_auth_permissions.py -v
```

### Estrutura dos Testes

- `tests/unit/`: Testes unitários dos serviços
  - `test_client_service.py`: Testes do serviço de clientes
  - `test_product_service.py`: Testes do serviço de produtos
  - `test_order_service.py`: Testes do serviço de pedidos
  - `test_user_service.py`: Testes do serviço de usuários

- `tests/`: Testes de integração
  - `test_clients_operations.py`: Testes das operações de clientes
  - `test_products_operations.py`: Testes das operações de produtos
  - `test_orders_operations.py`: Testes das operações de pedidos
  - `test_auth_permissions.py`: Testes de autenticação e permissões

## 📚 Documentação da API

A documentação completa da API está disponível em:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Principais Endpoints

#### Clientes
- `POST /clients/`: Criar novo cliente (requer admin)
- `GET /clients/`: Listar clientes
- `GET /clients/{id}`: Buscar cliente por ID
- `PUT /clients/{id}`: Atualizar cliente (requer admin)
- `DELETE /clients/{id}`: Excluir cliente (requer admin)

#### Produtos
- `POST /products/`: Criar novo produto (requer admin)
- `GET /products/`: Listar produtos
- `GET /products/{id}`: Buscar produto por ID
- `PUT /products/{id}`: Atualizar produto (requer admin)
- `DELETE /products/{id}`: Excluir produto (requer admin)

#### Pedidos
- `POST /orders/`: Criar novo pedido
- `GET /orders/`: Listar pedidos
- `GET /orders/{id}`: Buscar pedido por ID
- `PUT /orders/{id}`: Atualizar pedido
- `DELETE /orders/{id}`: Excluir pedido

#### Usuários
- `POST /users/`: Criar novo usuário (requer admin)
- `GET /users/me`: Obter dados do usuário atual
- `PUT /users/me`: Atualizar dados do usuário atual

#### Autenticação
- `POST /token`: Obter token de acesso
- `POST /token/refresh`: Renovar token de acesso

## 🔐 Autenticação

A API utiliza autenticação JWT (JSON Web Token). Para acessar endpoints protegidos:

1. Obtenha um token de acesso:
```bash
curl -X POST "http://localhost:8000/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=seu_usuario&password=sua_senha"
```

2. Use o token retornado no header das requisições:
```bash
curl -X GET "http://localhost:8000/clients/" \
     -H "Authorization: Bearer seu_token_aqui"
```

## 📦 Estrutura do Projeto

```
infog2/
├── src/
│   ├── controllers/    # Controladores da API
│   ├── models/         # Modelos do banco de dados
│   ├── routers/        # Rotas da API
│   ├── schemas/        # Schemas Pydantic
│   ├── services/       # Lógica de negócio
│   └── utils/          # Utilitários
├── tests/
│   ├── unit/          # Testes unitários
│   └── ...            # Testes de integração
├── .env               # Variáveis de ambiente
├── .env.example       # Exemplo de variáveis de ambiente
├── docker-compose.yml # Configuração do Docker Compose
├── Dockerfile         # Configuração do Docker
└── requirements.txt   # Dependências do projeto
```

## 🛠️ Desenvolvimento

### Ambiente de Desenvolvimento

1. Instale as dependências de desenvolvimento:
```bash
pip install -r requirements-dev.txt
```

2. Configure o ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Execute os testes durante o desenvolvimento:
```bash
pytest tests/ -v --cov=src
```

### Convenções de Código

- PEP 8 para estilo de código
- Docstrings em formato Google
- Type hints em todas as funções
- Testes unitários para serviços
- Testes de integração para endpoints

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📧 Suporte

Para suporte, envie um email para seu-email@exemplo.com ou abra uma issue no GitHub.
