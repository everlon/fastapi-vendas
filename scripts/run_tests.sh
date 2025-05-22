#!/bin/bash

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Executando testes...${NC}"

# Executar testes com cobertura
poetry run pytest --cov=src --cov-report=term-missing --cov-report=html

# Verificar se os testes passaram
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Todos os testes passaram!${NC}"
    echo -e "Relatório de cobertura gerado em: ${YELLOW}htmlcov/index.html${NC}"
else
    echo -e "${RED}Alguns testes falharam. Por favor, verifique o output acima.${NC}"
    exit 1
fi 