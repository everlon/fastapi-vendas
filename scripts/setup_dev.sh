#!/bin/bash

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Iniciando setup do ambiente de desenvolvimento...${NC}"

# Verificar se o Poetry está instalado
if ! command -v poetry &> /dev/null; then
    echo "Poetry não encontrado. Instalando..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Instalar dependências
echo -e "${YELLOW}Instalando dependências...${NC}"
poetry install

# Criar arquivo .env se não existir
if [ ! -f .env ]; then
    echo -e "${YELLOW}Criando arquivo .env...${NC}"
    cp .env.example .env
    echo -e "${GREEN}Arquivo .env criado. Por favor, configure as variáveis de ambiente.${NC}"
fi

# Executar migrações
echo -e "${YELLOW}Executando migrações do banco de dados...${NC}"
poetry run alembic upgrade head

# Iniciar containers Docker
echo -e "${YELLOW}Iniciando containers Docker...${NC}"
docker-compose up -d

echo -e "${GREEN}Setup concluído!${NC}"
echo -e "Para iniciar o servidor de desenvolvimento, execute: ${YELLOW}poetry run uvicorn app.main:app --reload${NC}" 