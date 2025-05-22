#!/bin/bash

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Limpando arquivos temporários e caches...${NC}"

# Remover arquivos Python compilados
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type f -name "*.pyd" -delete

# Remover diretórios de cache
rm -rf .pytest_cache/
rm -rf .coverage
rm -rf htmlcov/
rm -rf .mypy_cache/
rm -rf .ruff_cache/

# Remover arquivos de ambiente virtual (se existirem)
if [ -d ".venv" ]; then
    echo -e "${YELLOW}Removendo ambiente virtual...${NC}"
    rm -rf .venv
fi

# Limpar logs
find . -type f -name "*.log" -delete

echo -e "${GREEN}Limpeza concluída!${NC}"
echo -e "Para recriar o ambiente virtual, execute: ${YELLOW}poetry install${NC}" 