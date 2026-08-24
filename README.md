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
| `scheduler` | — | Executa em ciclo `coletar` → `enviar_digest` → `notificar_push` (ADR-008) |

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
| `DJANGO_EMAIL_BACKEND` | Backend de e-mail do digest | console (imprime no log) |
| `EMAIL_HOST` / `EMAIL_PORT` | Servidor SMTP (só com o backend SMTP) | `localhost` / `587` |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Credenciais SMTP | — |
| `EMAIL_USE_TLS` | TLS no envio | `True` |
| `DEFAULT_FROM_EMAIL` | Remetente do digest | `UFCA Newsletter <noreply@ufca.edu.br>` |
| `SCHEDULER_INTERVALO_SEGUNDOS` | Intervalo do ciclo do agendador | `900` (15 min) |

O `.env` não é versionado (está no `.gitignore`); `make up` cria um automaticamente a partir do `.env.example` caso ainda não exista.

### Como usar

```bash
make build      # constrói a imagem
make up         # sobe web + Postgres + agendador e aplica as migrações
make seed-demo  # popula o banco com conteúdos fictícios (ver abaixo)
make logs       # acompanha os logs
make shell      # bash interativo no container
make down       # derruba os containers
```

#### Conteúdos de demonstração

Enquanto o coletor automático não existe ([#16](https://github.com/Ruan-Pablo-Oli/UfcaNewsLetter/issues/16)),
o feed de um clone novo nasce vazio. O comando `seed_conteudos` cria fontes,
categorias e 30 conteúdos fictícios cobrindo os três caminhos da personalização
(universal, por curso e por interesse):

```bash
make seed-demo
# ou: docker compose exec web python manage.py seed_conteudos
```

É idempotente e **não** roda sozinho na subida dos contêineres — são dados
falsos, então executá-lo é uma decisão explícita.

### Tarefas periódicas

O serviço `scheduler` roda, em ciclo, os três comandos que fazem a aplicação
funcionar sozinha: `coletar` (varre as fontes devidas), `enviar_digest` (envia a
newsletter aos perfis elegíveis) e `notificar_push`. Cada comando decide
sozinho se já é hora de agir — o intervalo do ciclo é só a resolução do
agendamento (ver ADR-008).

```bash
docker compose logs -f scheduler        # acompanha os ciclos
```

Com o backend padrão de e-mail (console), o digest é **impresso no log do
agendador** em vez de enviado — nada sai para estudantes de verdade em
desenvolvimento. Para enviar mesmo, troque `DJANGO_EMAIL_BACKEND` para
`django.core.mail.backends.smtp.EmailBackend` e preencha as credenciais SMTP.

Para rodar qualquer tarefa na mão, sem esperar o ciclo:

```bash
docker compose exec web python manage.py coletar --fonte <id> --limite-paginas 2
docker compose exec web python manage.py enviar_digest --dry-run
docker compose exec web python manage.py notificar_push --dry-run
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
  frontend/               # SPA React (Vite) que consome a API
```

## Frontend

SPA em React + Vite, em `frontend/`. O servidor de desenvolvimento faz proxy de
`/accounts`, `/feed` e `/feedback` para o Django em `localhost:8000` — suba o
backend antes (`make up`) e acesse a aplicação pela porta do Vite.

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm test         # vitest
npm run lint
npm run build
```

## Testes

O backend usa `pytest` + `pytest-django`; o frontend usa `vitest` +
Testing Library (`cd frontend && npm test`).

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

O workflow do GitHub Actions (`.github/workflows/tests.yml`) roda, em todo `push` e `pull_request`:

- `pytest` (subindo um serviço PostgreSQL para os testes que dependem de banco);
- `ruff check .`;
- no `frontend/`: `npm run lint`, `npm test` e `npm run build`.
