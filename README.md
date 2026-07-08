# UFCA Newsletter

## Documentação

A documentação técnica e de processo fica em [`docs/`](docs/):

- [Arquitetura](docs/arquitetura.md) — stack, apps, modelo de dados (diagrama ER), autenticação e rotas
- [Decisões (ADRs)](docs/decisoes.md) — o *porquê* das principais escolhas técnicas
- [Fluxo de trabalho](docs/fluxo-de-trabalho.md) — ambiente local, testes, PR/CI, agente `@claude`
- [Rastreabilidade](docs/rastreabilidade.md) — matriz User Story → issue → PR → status

## Docker

### Stack

| Componente | Versão |
|---|---|
| Python | 3.12-slim |
| Django | 6.0.x |
| PostgreSQL | 16 |
| psycopg | 3.2.x |
| requests | 2.34.x |
| beautifulsoup4 | 4.15.x |
| lxml | 6.1.x |
| PyMuPDF | 1.27.x |
| python-dateutil | 2.9.x |

### Serviços

| Serviço | Porta | Descrição |
|---|---|---|
| `web` | `8000` | Aplicação Django |
| `db` | `5432` | PostgreSQL 16 |

### Variáveis de ambiente

A configuração é feita por variáveis de ambiente. Copie o arquivo de exemplo antes de subir o projeto:

```bash
cp .env.example .env
```

| Variável | Descrição | Padrão |
|---|---|---|
| `DJANGO_SECRET_KEY` | Chave secreta do Django | — (defina um valor único) |
| `DJANGO_DEBUG` | Ativa modo debug (`True`/`False`) | `True` |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos, separados por vírgula | `*` |
| `POSTGRES_DB` | Nome do banco | `ufcanewsletter` |
| `POSTGRES_USER` | Usuário do banco | `ufcanewsletter` |
| `POSTGRES_PASSWORD` | Senha do banco | — (defina um valor único) |
| `POSTGRES_HOST` | Host do banco | `db` |
| `POSTGRES_PORT` | Porta do banco | `5432` |

O `.env` não é versionado (está no `.gitignore`); `make up` cria um automaticamente a partir do `.env.example` caso ainda não exista.

### Como usar

```bash
make build    # constrói a imagem
make up       # sobe web + Postgres e aplica as migrações
make logs     # acompanha os logs
make shell    # bash interativo no container
make down     # derruba os containers
```

Ou diretamente com Docker Compose:

```bash
cp .env.example .env
docker compose up -d
```

### Estrutura

```text
  ./
  Dockerfile
  compose.yaml
  requirements.txt
  requirements-dev.txt
  pyproject.toml
  Makefile
  README.md
  .env.example
  app/                    # código da aplicação Django
    manage.py
    ufcanewsletter/       # projeto: settings, urls, wsgi, asgi
    newsletter/           # app de domínio: modelos das entidades
    accounts/             # app de autenticação: cadastro, login, perfil
```

## Testes

Os testes usam `pytest` + `pytest-django`.

### Rodando localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Os testes que acessam o banco de dados precisam de um PostgreSQL disponível (as mesmas variáveis de ambiente do `.env.example`). Para rodar apenas a suíte, com Docker Compose de apoio:

```bash
docker compose up -d db
pytest
```

### Lint

```bash
ruff check .
```

### CI

O workflow do GitHub Actions (`.github/workflows/tests.yml`) roda `pytest` e `ruff` em todo `push` e `pull_request`, subindo um serviço PostgreSQL para os testes que dependem de banco.
