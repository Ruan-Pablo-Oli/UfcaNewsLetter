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

## ADR-008 — Agendamento das coletas: management command + serviço agendador

- **Status:** aceito (agosto/2026). Nasceu como proposta na issue #52, para
  destravar #16 (coletor), #24 (digest) e #22 (push); ratificado ao implementar
  o serviço `scheduler` no `compose.yaml`. A questão que ficara em aberto —
  *onde* o agendador roda — está resolvida no fim deste registro.
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
  - **Resolvido (agosto/2026): serviço `scheduler` no `compose.yaml`**, com a
    mesma imagem do `web` mas processo separado, rodando `docker/scheduler.sh`.
    Escolhido em vez do cron do host porque sobe igual para todo mundo com
    `make up`; e em vez de um agendador embutido no `web` porque reiniciar a
    aplicação não derruba o agendamento, e uma segunda réplica do `web` não
    duplicaria as execuções.
  - **Por que um laço de intervalo fixo, e não o `cron` do sistema:** a decisão
    de "já é hora?" **já mora em cada comando** — `coletar` respeita
    `Fonte.intervalo_coleta`, `enviar_digest` respeita `Perfil.frequencia_email`
    (1 ou 7 dias desde a última `Entrega`) e `notificar_push` deduplica por
    `Entrega`. Com isso, o agendador não precisa de expressões cron: basta
    acordar de tempos em tempos e chamar os três. O intervalo
    (`SCHEDULER_INTERVALO_SEGUNDOS`, padrão 900) define a *resolução* do
    agendamento, não a frequência das tarefas. Evita instalar e configurar o
    `cron` na imagem — que ainda exigiria exportar as variáveis de ambiente do
    contêiner para o ambiente do daemon, um ponto clássico de erro.
  - Uma tarefa que falha (rede fora, SMTP recusando) é registrada no log e
    **não interrompe as demais nem o laço** — o ciclo seguinte tenta de novo.
  - Testar sem esperar o intervalo continua direto: os comandos aceitam
    execução manual (`python manage.py coletar --fonte=<id>`) e os testes usam
    `call_command`, sem depender do agendador.


## ADR-009 — Aprovação automática do conteúdo classificado

- **Status:** aceito (agosto/2026)
- **Contexto:** a US-05.2 (#27) fez todo conteúdo coletado nascer `pendente`,
  esperando um administrador aprovar item a item antes de aparecer no feed. Na
  primeira coleta real (uma página de Informes) isso significou **20 itens
  parados na fila** vindos de uma única fonte, de uma única categoria. Com as
  16 fontes cadastradas rodando no intervalo delas, o volume torna a revisão
  manual o gargalo do produto: sem um admin de plantão, o feed do estudante
  simplesmente não recebe nada.
- **Decisão:** o conteúdo é aprovado automaticamente quando o classificador
  (#17) consegue atribuir uma categoria. Ter casado com uma regra de
  palavra-chave é o sinal de que o item é reconhecidamente institucional; o que
  não casa com nenhuma regra continua `pendente` e permanece na fila de revisão.
  A promoção acontece dentro de `classificar_conteudo`, então vale nos dois
  caminhos: na coleta (que passou a classificar cada registro novo) e no
  `manage.py classificar` sobre o backlog.
- **Alternativas consideradas:**
  1. **Aprovar tudo na coleta.** Mais simples, mas entrega ao estudante
     qualquer coisa que o adaptador extraia, incluindo páginas de listagem mal
     parseadas — sem nenhum sinal de qualidade no meio.
  2. **Flag por fonte** (`Fonte.aprovacao_automatica`). Dá controle fino, mas
     exige migração e uma decisão humana por fonte cadastrada; o sinal de
     confiança fica na origem, não no conteúdo.
  3. **Chave global de configuração.** Liga/desliga sem migração, porém é
     tudo-ou-nada e não usa nenhuma evidência sobre o item.
- **Consequências:**
  - Ganho: o pipeline `coletar` → feed funciona sem intervenção humana; a fila
    de revisão deixa de ser obrigatória e passa a ser exceção — na medição da
    fonte 10, 17 de 20 itens seriam automáticos e 3 iriam para a fila.
  - Custo: a qualidade do feed passa a depender da precisão do classificador
    por regras. Um falso positivo (regra casando com algo irrelevante) chega ao
    estudante sem revisão. Mitigações existentes: o revisor ainda pode
    `descartar` depois, e o feedback negativo do estudante (#15) remove o item
    do feed dele e rebaixa a categoria.
  - Conteúdo `descartado` que for reclassificado **não** volta ao feed: a
    promoção só age sobre `pendente`, para uma decisão humana nunca ser
    revertida por um processo automático.
  - Se a precisão se mostrar insuficiente, o passo natural é a alternativa 2
    (flag por fonte) sobre esta política, não o retorno à revisão obrigatória.


## ADR-011 — Direcionamento do conteúdo coletado (universal por padrão + interesses por regra)

- **Status:** aceito (agosto/2026)
- **Contexto:** o feed (`feed_queryset_for_perfil`) mostra um conteúdo se ele
  for `universal`, **ou** se o curso do perfil estiver em `Conteudo.cursos`,
  **ou** se houver interesse em comum. O coletor não preenchia nenhuma das
  três coisas, e o classificador só preenchia `cursos` quando o texto citava um
  curso. Na primeira coleta real de verdade isso ficou evidente: dos 224
  conteúdos coletados, **0 eram universais e 0 tinham interesse**; o perfil sem
  curso/interesses via **zero** conteúdo real, e um perfil completo via 10. O
  pipeline funcionava de ponta a ponta e mesmo assim o estudante não recebia
  quase nada — o elo que faltava era o direcionamento.
- **Decisão:** `direcionar_conteudo` (em `classificador.py`) decide para quem o
  conteúdo aparece:
  - cita curso(s) conhecido(s) → vai só para esses cursos;
  - não cita nenhum → **`universal=True`**, como um mural institucional: aviso
    da UFCA é para toda a comunidade até prova em contrário;
  - interesses mencionados são amarrados em qualquer caso, por regras de
    palavra-chave no mesmo formato das de curso (`REGRA_INTERESSES`).
  Nada é sobrescrito: direcionamento manual ou de seed tem precedência.
- **Alternativas consideradas:**
  1. **Só casar interesses**, sem universal por padrão. Mais fiel à ideia de
     personalização, mas quem não marcou interesses continua com feed vazio — e
     o perfil recém-criado é exatamente esse caso.
  2. **Só ajustar os perfis de teste** (preencher curso e interesses). Resolve a
     demonstração e não resolve o produto: qualquer usuário novo voltaria ao
     feed vazio.
- **Consequências:**
  - Medido na base real (224 conteúdos): universais passaram de 0 para 159 e
    conteúdos com interesse de 0 para 175; o perfil sem curso nem interesses
    passou de **0 para 129** conteúdos reais no feed.
  - O peso da personalização se desloca: com a maioria universal, o que
    diferencia os feeds é sobretudo a **ordenação por relevância** (feedback do
    estudante, US-01.3) e os motivos de recomendação, não mais o filtro de
    visibilidade.
  - Se no futuro o volume tornar o feed genérico demais, o ajuste natural é
    restringir o universal por categoria (ex.: só `comunicado` e `prazo`), sem
    voltar ao estado em que o conteúdo coletado não alcança ninguém.
  - `classificar --redirecionar` reaplica o direcionamento ao conteúdo já
    classificado (backfill), já que `classificar_conteudo` pula o que já tem
    categoria.
