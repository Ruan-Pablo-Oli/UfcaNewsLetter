# Decisões de Arquitetura (ADRs)

Registros curtos do **porquê** das principais decisões técnicas. Formato:
contexto → decisão → consequências. Data de referência: **julho/2026**.

---

## ADR-001 — Django + PostgreSQL como stack

- **Status:** aceito
- **Contexto:** precisamos de um framework web maduro para modelar o domínio,
  com admin pronto, ORM e ecossistema de testes; e de um banco relacional
  robusto para as relações entre perfis, conteúdos, entregas e feedback.
- **Decisão:** Django 6 + PostgreSQL 16.
- **Consequências:** ganhamos o Django Admin de graça (gestão de dados sem UI
  própria já no início); ORM e migrações versionadas; Postgres suporta bem as
  constraints (unicidade, `unique_together`). Custo: dependência de um banco
  externo (resolvido via Docker Compose).

## ADR-002 — Configuração por variáveis de ambiente + Docker Compose

- **Status:** aceito (issue #36)
- **Contexto:** desenvolvimento em equipe e futura implantação exigem
  configuração sem segredos no código.
- **Decisão:** `settings.py` lê `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` e as
  credenciais do Postgres de variáveis de ambiente; `compose.yaml` sobe `web` +
  `db` (Postgres) com healthcheck, aplicando migrações no start. `.env.example`
  documenta as variáveis; `.env` é gitignorado.
- **Consequências:** `make up` sobe o ambiente completo; nenhum segredo
  versionado. Trocar de SQLite para Postgres exigiu ajustar o driver e o compose.

## ADR-003 — App de domínio (`newsletter`) + app de contas (`accounts`)

- **Status:** aceito (issues #34, #35)
- **Contexto:** separar responsabilidades entre os dados do domínio e a
  autenticação.
- **Decisão:** um app `newsletter` para as entidades centrais e um app
  `accounts` para cadastro/login/perfil. A configuração fica no pacote de
  projeto `ufcanewsletter`.
- **Consequências:** organização clara; espaço para novos apps (ex.: `coleta`,
  `distribuicao`) sem inchar um único módulo.

## ADR-004 — Autenticação padrão do Django com e-mail institucional

- **Status:** aceito (issue #35)
- **Contexto:** o público-alvo são estudantes da UFCA; não há necessidade (por
  ora) de um modelo de usuário customizado.
- **Decisão:** usar o `User` padrão do Django; o cadastro público exige e-mail
  `@aluno.ufca.edu.br` e cria um `Perfil` vazio automaticamente. Administradores
  são criados via `createsuperuser`/admin (`is_staff`), fora do fluxo público.
- **Consequências:** menos código e mais segurança (auth testado do framework).
  Se no futuro for preciso login por SSO/e-mail-como-username, será uma migração
  mais trabalhosa — aceitável no estágio atual.

## ADR-005 — CI com pytest + ruff no GitHub Actions

- **Status:** aceito (issue #37)
- **Contexto:** manter o `main` saudável e padronizar qualidade desde cedo.
- **Decisão:** workflow `tests.yml` com dois jobs — `pytest` (sobe serviço
  PostgreSQL 16) e `lint` (`ruff check .`) — rodando em `push` e `pull_request`.
  Migrations são excluídas do lint (são geradas pelo Django).
- **Consequências:** todo PR é validado automaticamente; base para tornar os
  checks obrigatórios (ver ADR-006).

## ADR-006 — Proteção do branch `main`

- **Status:** aceito
- **Contexto:** evitar merge de código quebrado ou sem revisão, especialmente
  com PRs abertos por um agente.
- **Decisão:** branch protection no `main` exigindo **1 aprovação humana** +
  checks obrigatórios **`pytest`** e **`lint`**; descarte de aprovações antigas a
  cada novo commit; exigir aprovação do último push; sem force-push/deleção;
  conversas resolvidas. **Não** vale para admins (`enforce_admins=false`) — o
  dono pode dar bypass em necessidade.
- **Consequências:** ninguém (exceto o dono via bypass) mergeia sem revisão + CI
  verde. Como o agente não aprova o próprio PR, sempre há um humano no circuito.

## ADR-007 — Uso do agente `@claude`

- **Status:** aceito (issues/PR #23, #42)
- **Contexto:** acelerar a implementação com um agente, sem gastar tokens de
  terceiros nem comprometer segurança.
- **Decisão:** o Action é **acionável apenas pelo dono** (`github.actor ==
  'Ruan-Pablo-Oli'`); roda em runner efêmero; recebe uma allowlist **restrita**
  de comandos (`pip`, `python`, `pytest`, `ruff`) para gerar migrações reais e se
  autovalidar antes de abrir o PR.
- **Consequências:** PRs chegam mais prontos. Limitação conhecida: o GitHub App
  do agente **não tem permissão `workflows`**, então arquivos em
  `.github/workflows/` precisam ser adicionados manualmente. A segurança se apoia
  em "só o dono aciona" + revisão humana no merge.
