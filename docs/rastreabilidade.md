# Matriz de Rastreabilidade

Liga cada **User Story / tarefa técnica → issue → PR → status**, por sprint
(milestone). É a ponte entre os requisitos (Notion) e a implementação (GitHub).

> **Espelhar no Notion:** este arquivo é markdown; cole/importe no Notion e
> mantenha os números de issue/PR como link. A **fonte de verdade** do status é
> o board do GitHub.

**Legenda:** ✅ concluído · 🔜 próximo · ⏳ a fazer · Prioridade = MoSCoW · Est. = estimativa (Fibonacci)

> **Estado geral (24/08/2026):** as três milestones (M1, M2, M3) estão com
> **0 issues abertas** e todo o trabalho correspondente está mergeado na `main`
> (até o PR #78).

## M1 — Base de dados e personalização (venc. 25/07) — ✅ concluída

### Fundação técnica — épico #38 ✅

| Issue | Tarefa | Prioridade | Est. | PR | Status |
|---|---|---|---|---|---|
| #36 | Configurar PostgreSQL e variáveis de ambiente | must | 3 | #39 | ✅ |
| #37 | Testes automatizados e CI (pytest + ruff) | must | 3 | #40 | ✅ |
| #34 | Modelar entidades centrais do domínio | must | 8 | #41 | ✅ |
| #35 | Autenticação e cadastro de usuários | must | 5 | #43 | ✅ |
| #21 | Definir requisitos funcionais e não funcionais | must | — | — | ✅ (doc) |

### FEAT-01 — Motor de Personalização

| Issue | US | Título | Prioridade | Est. | PR | Status |
|---|---|---|---|---|---|---|
| #12 | US-01 | Definir filtros de conteúdos (história-mãe) | — | — | — | ✅ (fechada pelas filhas) |
| #13 | US-01.1 | Configurar perfil acadêmico | must | 3 | #45 | ✅ |
| #14 | US-01.2 | Receber conteúdo personalizado | must | 5 | #48 | ✅ |
| #15 | US-01.3 | Ajustar nível de relevância | must | 3 | #49 | ✅ |
| #47 | US-01.2-FE | Tela de feed personalizado (frontend) | — | — | #51 | ✅ |

> #47 está na milestone M3 no board, mas fecha o front da US-01.2 — listada aqui
> junto da história que ela completa.

## M2 — Coleta e processamento de conteúdo (venc. 28/08) — ✅ concluída

### FEAT-03 — Extração e Indexação (épico #30)

| Issue | US | Título | Prioridade | Est. | PR | Status |
|---|---|---|---|---|---|---|
| #52 | — | [TECH] Campos de coleta no modelo e decisão do scheduler (ADR-008) | must | — | #58 | ✅ |
| #16 | US-03.1 | Coletar conteúdo automaticamente | must | 8 | #61 (via #64) | ✅ |
| #53 | US-03.1.1 | Adaptador de Notícias e Informes | P0 | — | #59 | ✅ |
| #54 | US-03.1.2 | Processar documentos e anexos (PDF) | must | — | #60 (processador) + #67 (integração) | ✅ |
| #17 | US-03.2 | Classificar conteúdo por categoria | must | 5 | #62 (via #64) | ✅ |
| #18 | US-03.3 | Resumir conteúdo extenso | must | 5 | #69 | ✅ |

> O PR #64 (`develop` → `main`) integrou de uma vez os PRs #60, #61, #62 e #63,
> que haviam sido mergeados no branch `develop`.

## M3 — Integração e MVP funcional (venc. 05/09) — ✅ concluída

### FEAT-03 (continuação) — demais adaptadores de fonte

| Issue | US | Título | Prioridade | Est. | PR | Status |
|---|---|---|---|---|---|---|
| #55 | US-03.1.3 | Adaptador de calendários e eventos | — | — | #68 | ✅ |
| #56 | US-03.1.4 | Adaptador de concursos e seleções | — | — | #65 (+ correção #66) | ✅ |
| #57 | US-03.1.5 | Inventariar e coletar fontes de unidades | — | — | #77 (inventário) + #78 (coletor) | ✅ |

### FEAT-04 — Distribuição da Newsletter (épico #31)

| Issue | US | Título | Prioridade | Est. | PR | Status |
|---|---|---|---|---|---|---|
| #24 | US-04.1 | Receber newsletter por e-mail | must | 8 | #71 | ✅ |
| #25 | US-04.2 | Configurar frequência e canais de entrega | should | 3 | #73 | ✅ |
| #22 | US-04.3 | Notificações no sistema (push) | should | 5 | #74 (backend) + #75 (frontend) | ✅ |

### FEAT-05 — Painel de Administração (épico #32)

| Issue | US | Título | Prioridade | Est. | PR | Status |
|---|---|---|---|---|---|---|
| #26 | US-05.1 | Gerenciar fontes de conteúdo | must | 5 | #70 | ✅ |
| #27 | US-05.2 | Moderar fila de conteúdo para revisão | should | 5 | #72 | ✅ |

### FEAT-07 — Histórico e Busca (épico #33)

| Issue | US | Título | Prioridade | Est. | PR | Status |
|---|---|---|---|---|---|---|
| #28 | US-07.1 | Buscar conteúdos | should | 5 | #63 (via #64) | ✅ |
| #29 | US-07.2 | Acessar histórico de conteúdos | should | 3 | #63 (via #64) | ✅ |

## Épicos

| Issue | Épico | Status |
|---|---|---|
| #38 | Fundação Técnica (M1) | ✅ |
| #30 | FEAT-03 — Extração e Indexação | ✅ |
| #31 | FEAT-04 — Distribuição da Newsletter | ✅ |
| #32 | FEAT-05 — Painel de Administração | ✅ |
| #33 | FEAT-07 — Histórico e Busca | ✅ |

## Melhorias de processo e apoio (sem user story)

| Issue/PR | Descrição | Status |
|---|---|---|
| PR #23 | Configuração inicial do agente Claude (GitHub Actions) | ✅ |
| PR #42 | Liberar comandos de build/test ao agente (`--allowedTools`) | ✅ |
| PR #44 | Documentação de implementação (`docs/`) | ✅ |
| PR #46 | Comando `seed_interesses` + execução no `make up` | ✅ |
| PR #50 | Rodar o CI de `push` só na `main` (elimina run duplicado) | ✅ |
| PR #51 | Comando `seed_conteudos` (`make seed-demo`) e CI do frontend | ✅ |
| PR #64 | Integração de `develop` na `main` (#16, #17, #28, #29, #54) | ✅ |
| PR #76 | Liberar `npm` ao agente para validar o frontend | ✅ |

## Pesquisa e requisitos (Sprint 1)

As issues #1–#11 (guião AEIOU, entrevistas, mapas de empatia, persona, cenários
e levantamento das user stories) estão fechadas; os artefatos vivem no **Notion**
— aqui ficam apenas os números para referência cruzada.

## Como conferir esta matriz

O status de cada linha sai direto do board; para revalidar tudo de uma vez:

```bash
gh issue list --state all --limit 100 --json number,title,state,milestone
gh pr list --state merged --limit 60 --json number,title,closingIssuesReferences
gh api "repos/Ruan-Pablo-Oli/UfcaNewsLetter/milestones?state=all"
```

---

_Última atualização: 24/08/2026 — cruzada com as issues, PRs e milestones do GitHub. Todas as issues de M1–M3 fechadas e mergeadas na `main` até o PR #78. Atualizar a cada merge relevante ou fechamento de sprint._
