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


## ADR-010 — Produção: gunicorn + WhiteNoise servindo a SPA na mesma imagem

- **Status:** aceito (agosto/2026)
- **Contexto:** até aqui o `web` rodava `runserver` com `DEBUG=True` e a SPA só
  existia no servidor do Vite. Isso não é um ambiente publicável: o servidor de
  desenvolvimento do Django não é feito para produção, `DEBUG=True` expõe stack
  traces e desliga as proteções, e não havia nada servindo os estáticos nem o
  `index.html` do front.
- **Decisão:** uma única imagem, construída em dois estágios — `node` compila a
  SPA, e o estágio Python copia o `dist/` para `/app/spa`, roda `collectstatic`
  no build e sobe **gunicorn**. O **WhiteNoise** serve os estáticos no próprio
  processo, e o `index.html` vira template do Django, devolvido por uma rota
  curinga para o React Router funcionar em recarregamento de página.
- **Alternativas consideradas:**
  1. **nginx como serviço separado**, servindo `dist/` e fazendo proxy para o
     gunicorn. É o arranjo clássico e o mais eficiente para estáticos, mas
     acrescenta um contêiner, um arquivo de configuração e uma segunda camada
     onde errar rota. Para o volume deste projeto, o ganho não paga o custo.
  2. **Servir a SPA fora da aplicação** (Netlify/Vercel apontando para a API).
     Bom para escala, mas cria CORS e uma origem separada para a sessão do
     Django — hoje a autenticação é por cookie de sessão.
- **Consequências:**
  - `docker compose up` entrega a aplicação completa, front e API na mesma
    origem: sem CORS, sem uma segunda implantação para coordenar.
  - As configurações que dependem de HTTPS (redirecionamento, cookies
    `Secure`, HSTS) ficam atrás de `DJANGO_SECURE_SSL`, desligada por padrão —
    com ela ligada, `manage.py check --deploy` não acusa nenhum aviso; sem
    ela, acusa os quatro esperados, e é assim que se roda em `http://localhost`
    sem laço de redirecionamento.
  - O `base` do Vite passou a ser `/static/`, que é por onde o WhiteNoise
    serve. Mudar isso quebra o carregamento dos assets em produção.
  - Custo: rebuild da imagem a cada mudança de front (não há hot reload nesse
    modo). O fluxo de desenvolvimento continua sendo `npm run dev` com proxy
    para o Django.


## ADR-012 — Resumo: ligado ao pipeline, lendo os anexos, com recorte de exibição

- **Status:** aceito (agosto/2026)
- **Contexto:** o resumidor da US-03.3 (#18) foi entregue com testes e **nunca
  foi chamado por ninguém** — nenhum comando, nem a coleta. Os 224 conteúdos
  reais estavam com `resumo` vazio e o feed mostrava cards sem texto. Ao ligar,
  apareceu um segundo problema: o resumidor só age em corpos com 500+ palavras,
  e os informes da UFCA são curtos (mediana de **177** palavras) — apenas **5**
  dos 224 qualificavam. O conteúdo extenso não está no corpo, está no **PDF
  anexado**: um edital com 8.104 palavras contra 465 no informe que o anuncia.
- **Decisão:** três partes.
  1. **Ligar:** novo `manage.py resumir` (o módulo já tinha
     `resumir_pendentes` "para o comando") e chamada em `_persistir`, para uma
     execução de `coletar` render conteúdo pronto para exibição.
  2. **Somar os anexos:** `texto_completo` junta o corpo ao texto dos PDFs já
     processados pela #54. O alvo passou de 5 para **65** conteúdos.
  3. **Recorte de exibição:** `resumo_para_exibicao` devolve o resumo quando
     existe e, quando não, o início do corpo — regra que o `digest.py` já tinha
     localmente e que agora é uma só, usada por feed, busca, histórico e digest.
     Nenhum card fica vazio.
- **Limpeza do texto de PDF:** a extração do PyMuPDF quebra linha a cada linha
  do documento e mantém timbre, rodapé e numeração de seção. Sem tratamento, o
  resumo saía como *"DA MATRÍCULA 3.1 A matrícula das pessoas..."* ou como o
  endereço da reitoria, e o público-alvo vinha com quebra de linha no meio.
  Junta-se as quebras e descartam-se sentenças que são cabeçalho (`3.1`,
  `DA MATRÍCULA`, `Art. 5º`) ou timbre institucional (endereço, telefone, site,
  e-mail).
- **Consequências:**
  - Cobertura de resumo: **65 de 224 (29%)**; cards sem texto nenhum: **0**.
  - `gerado_por_ia` continua `False` em 100% — nada aqui usa modelo.
  - **Limite reconhecido:** resumo extrativo sobre texto de PDF continua sendo
    recorte de sentenças, não redação. As frases escolhidas são reais e
    informativas, mas às vezes começam no meio do assunto. A porta para
    qualidade melhor já existe e é o `summarizer` injetável do módulo: um
    chamável `(titulo, corpo) -> str` que, quando usado, marca
    `gerado_por_ia=True`. Ligar um LLM ali é mudança de uma linha na chamada.
  - `prazo` foi extraído em 4 conteúdos e `publico_alvo` em 7 — as regex
    dependem de formulações específicas ("até dd/mm/aaaa", "destinadas a ...").
    Ampliá-las é trabalho separado, com ganho direto na tela.


## ADR-013 — Classificação por pontuação, com o título decidindo

- **Status:** aceito (agosto/2026)
- **Contexto:** o classificador (#17) escolhia a categoria pela **primeira**
  regra que casasse, na ordem `edital → prazo → evento → comunicado`. Medido no
  corpus real, **48% dos conteúdos casam com mais de uma categoria** — ou seja,
  em quase metade dos casos a categoria era decidida pela posição na lista, não
  pela evidência. O efeito visível: um congresso com data de inscrição virava
  `prazo`, porque a regra `até \d+ de` vem antes das regras de evento. Com a
  aprovação automática (ADR-009), esse erro chega ao estudante sem revisão.
- **Decisão:** três mudanças.
  1. **Pontuação em vez de primeira regra**: conta quantas regras de cada
     categoria casam.
  2. **O título decide**; o corpo só é consultado quando o título não casa com
     regra nenhuma. O título é o rótulo que a própria fonte deu ao conteúdo
     ("Edital nº…", "Semana de…"); o corpo menciona inscrições e prazos de
     passagem. Somar os dois deixava um corpo longo derrubar um título
     inequívoco — foi o que fez "Prae lança **Edital** Unificado" virar
     comunicado. Empates seguem a ordem de `REGRA_CATEGORIAS`, que codifica a
     importância editorial.
  3. **Vocabulário ampliado a partir do corpus**: fórum, webinário, oficina,
     minicurso, colóquio, aula inaugural, arraiá, sarau (evento);
     funcionamento, horário de atendimento, reajuste, tarifa, suspensão
     (comunicado); "abre seleção", "credenciamento", "seleciona voluntários"
     (edital); "último dia", "deve ser enviado", "comprovação de" (prazo).
- **Falsos positivos encontrados ao medir** (todos silenciosos até então):
  - `\bfeira\b` casava com **"sexta-feira"** e **"segunda-feira"** — qualquer
    aviso com dia da semana virava evento;
  - `\bsemana\b` (regra original) casava com "durante a semana";
  - `\brefeit[óo]rio` casava com **"Auxílio Refeitório"**, nome de benefício num
    título de edital.
  Os três viraram teste.
- **Consequências:**
  - Na base real de 224 conteúdos, **33 mudaram de categoria**; `evento` passou
    de 26 para 41 (os eventos que estavam como `prazo` ou `edital`), `prazo` caiu
    de 31 para 26 e `comunicado` subiu de 18 para 23.
  - `fixtures/titulos_rotulados.json` guarda 35 títulos reais com o rótulo
    humano, e `test_classificador_precisao.py` trava regressão em 90% de acerto.
    **O número não é estimativa de acurácia**: as regras foram ajustadas olhando
    para esse conjunto. A validação independente foi revisar as mudanças no
    corpus inteiro.
  - `classificar --recategorizar` reaplica as regras ao conteúdo já
    classificado, **sobrescrevendo inclusive correções manuais** — daí ser uma
    flag explícita, e não o comportamento padrão.
  - Continua sendo classificação por palavra-chave: casos que dependem de
    entender o texto (um resultado de prêmio, um convite institucional) seguem
    errando. O caminho para além disso é o mesmo do resumidor — um modelo — com
    o custo e a dependência que isso traz.
