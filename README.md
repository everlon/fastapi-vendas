# FastApi (v1) para analise da InfoG2

### Desenvolvimento de API CRUD de Produtos em Python com FastAPI.

---

## Requisitos utilizados:

- Python 3.12.3
- FastAPI
- SQLAlchemy
- SQLite
- MongoDB
- Docker

---

### Instalação:

Depois de clonar o repositório, não tem segredo, é somente chamar os endpoints.

`docker-compose up --build -d`

[Documentação gerada pelo FastAPI](http://localhost:8000/api/v1/redoc): http://localhost:8000/api/v1/redoc

![Redoc](redocly.png)

[EndPoints gerados pelo FastAPI](http://localhost:8000/api/v1/docs): http://localhost:8000/api/v1/docs

![EndPoints](endpoints.jpeg)

---

### EndPoints para o Postman:
![Postman](postman.png)

---

### Endpoint de Listar Produdos:

No endpoint de Listar temos alguns detalhes importantes a observar.

[Listar produtos](http://localhost:8000/api/v1/products/?page=1&page_size=25&search=&status=)

**http://localhost:8000/api/v1/products/?page=1&page_size=10&search=pedal&status=em estoque**

Temos os seguintes parâmetros: PAGE, PAGE_SIZE, SEARCH e STATUS onde podemos trabalhar nossas listas.

```
- PAGE = Número da página da paginação.
- PAGE_SIZE = Número de produtos por página.
- SEARCH = É um termo que será buscado em Nome ou Descrição do Produto.
- STATUS = Colocamos uma das opções: "em estoque", "em reposição" ou "em falta" (sem aspas) para listas os Produtos com os seguintes status.
```

---

### Execução dos Tests:
![PyTest](pytest_print.png)
