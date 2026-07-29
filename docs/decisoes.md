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

## ADR-008 — Agendamento das coletas: management command + cron

- **Status:** proposta (issue #52) — decisão de infraestrutura ainda não
  ratificada pelo time; registrada aqui para destravar #16 (coletor), #24 (job
  de envio do digest) e #22 (disparo de push), que dependem de *alguma* forma
  de "rodar algo a cada N minutos" existir.
- **Contexto:** o coletor da #16 precisa varrer as `Fonte` ativas
  periodicamente, respeitando `Fonte.intervalo_coleta` e atualizando
  `Fonte.ultima_coleta` a cada execução bem-sucedida. É o mesmo tipo de
  necessidade do envio do digest (#24) e do disparo de push (#22): um
  agendador que dispare tarefas em intervalos, sem interação do usuário.
- **Alternativas consideradas:**
  1. **Celery + broker (Redis) + worker dedicado.** Padrão de mercado para
     filas de tarefas assíncronas, com retry, agendamento (`celery beat`) e
     monitoramento maduros.
     - Contras: exige subir um serviço novo (Redis) no `compose.yaml`, um
       processo `worker` (e possivelmente um `beat`) separado do `web`, mais
       variáveis de ambiente, e mais superfície de CI (novo serviço nos
       workflows) — tudo isso para um caso de uso que hoje é só "rodar a cada
       N minutos". Curva de configuração desproporcional ao volume atual
       (poucas fontes, coleta pouco frequente).
  2. **`django-crontab` / `django-apscheduler`** (agendador embutido no
     processo Django).
     - Contras: acopla o agendamento ao ciclo de vida do processo `web`
       (reinício do container derruba o agendamento; múltiplas réplicas do
       `web` duplicariam a execução sem coordenação extra); menos
       transparente para depurar do que "rodar um comando e ver o log".
  3. **Management command (`python manage.py coletar`, `enviar_digest`,
     etc.) + `cron`** — cada tarefa periódica é um comando Django comum,
     testável isoladamente com `call_command` (como já se faz em
     `test_seed_conteudos.py`), disparado de fora do processo web por um
     agendador simples.
- **Decisão (recomendação em aberto):** opção 3. Cada necessidade periódica
  (coleta, digest, push) vira um management command; a orquestração de
  *quando* rodar fica fora do código da aplicação, em um agendador simples.
- **Consequências:**
  - Ganho: zero infraestrutura nova para o volume atual; cada comando é
    testável sozinho via `call_command`, sem precisar simular um worker;
    "arrancar" para Celery mais tarde (se o volume justificar) é migração,
    não reescrita — os management commands continuam existindo, só passam a
    ser chamados por tasks Celery em vez de por cron.
  - Custo: sem retry/backoff automático, sem fila de prioridade, sem
    monitoramento de execução pronto — se algo disso vier a ser necessário
    antes do volume justificar Celery, precisa ser construído à mão.
  - **Em aberto para o time decidir:** onde o cron roda no ambiente local —
    um serviço `scheduler` próprio no `compose.yaml` (ex.: imagem baseada em
    `ofelia`/`supercronic`, ou um container simples com `cron` do sistema
    operacional chamando `docker compose exec web python manage.py ...`) vs.
    cron do host do desenvolvedor (mais simples, porém não reproduz o
    ambiente de todo mundo igual). Também em aberto: como testar sem esperar
    o `intervalo_coleta` — a proposta é os comandos aceitarem execução manual
    direta (`python manage.py coletar --fonte=<id>`) e os testes de cada
    comando usarem `call_command` diretamente, sem depender do cron.
