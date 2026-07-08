# Fluxo de trabalho

## Fonte de verdade

- **Backlog / status / código:** GitHub (issues, board do projeto, PRs).
- **Pesquisa/UX e relatório:** Notion.

O board do GitHub é o **único** backlog. O Notion referencia issue/PR por número
(ver [rastreabilidade](rastreabilidade.md)).

## Ambiente local

```bash
cp .env.example .env       # cria o arquivo de variáveis (se ainda não existir)
make up                    # sobe web + Postgres e aplica as migrações
make logs                  # acompanha os logs
make down                  # derruba os contêineres
```

Criar um usuário administrador e acessar o painel:

```bash
docker compose exec web python manage.py createsuperuser
# depois: http://localhost:8000/admin/
```

## Testes e lint (mesma coisa que o CI roda)

```bash
pip install -r requirements-dev.txt
pytest                     # testes
ruff check .               # lint
python app/manage.py makemigrations --check --dry-run   # confere migrações
```

## Fluxo de Pull Request

1. Criar um branch a partir do `main` (nunca commitar direto no `main`).
2. Implementar + garantir `pytest`, `ruff` e migrações OK localmente.
3. Abrir o PR com `Closes #<issue>` na descrição.
4. O CI (`pytest`, `lint`) roda automaticamente; o `claude-review` comenta uma revisão.
5. **1 aprovação humana** é obrigatória (o autor não aprova o próprio PR).
6. Merge só com **aprovação + checks verdes**.

### Proteção do `main` (resumo)

- Requer PR + **1 aprovação**; descarta aprovações antigas a cada novo commit.
- Checks obrigatórios: **`pytest`** e **`lint`**.
- Sem push direto, force-push ou deleção do `main`.
- Admin (dono) pode dar bypass em caso de necessidade.

## Agente `@claude`

- **Como acionar:** comentar `@claude <instrução>` numa **issue** ou **PR**.
  Só o **dono do repositório** consegue acionar (para não gastar tokens de
  colaboradores).
- **O que ele faz:** lê a issue/thread, implementa num branch `claude/issue-N-...`,
  se autovalida (`pytest`/`ruff`/`makemigrations`) e disponibiliza o PR.
- **Revisão automática:** todo PR do dono recebe um comentário de review do Claude
  (é comentário, **não** conta como aprovação).
- **Limitações conhecidas:**
  - O GitHub App do agente **não pode criar/editar** arquivos em
    `.github/workflows/` (falta a permissão `workflows`) — esses arquivos são
    adicionados manualmente ao branch.
  - Às vezes ele deixa o branch pronto mas **não abre o PR** (basta abrir pelo
    link "Create PR" do comentário, ou pedir para abrir).

## Convenções

- **Commits:** prefixos no estilo *conventional commits* (`feat:`, `ci:`,
  `docs:`, `fix:`, `refactor:`).
- **Branches:** `feat/...`, `chore/...`, `docs/...`; os do agente vêm como
  `claude/issue-<n>-<timestamp>`.
- **Migrações:** sempre geradas por `makemigrations` (não editar à mão); revisar
  com `makemigrations --check` antes do merge.
