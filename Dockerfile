FROM python:3.12-slim

WORKDIR /infog2

# Instalar dependências do sistema necessárias
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Adicionar Poetry ao PATH
ENV PATH="/root/.local/bin:$PATH"

# Configurar o Poetry
RUN poetry config virtualenvs.create false \
    && poetry config installer.max-workers 10

# Copiar arquivos de dependências
COPY pyproject.toml ./

# Gerar poetry.lock e instalar dependências
RUN poetry lock \
    && poetry install --no-interaction --no-root --no-cache

# Copiar o resto do código
COPY . .

EXPOSE 8000

# Usar o caminho completo para o uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
