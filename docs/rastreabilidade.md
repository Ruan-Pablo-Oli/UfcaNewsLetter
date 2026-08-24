# Matriz de Rastreabilidade

Liga cada **User Story / tarefa técnica → issue → PR → status**, por sprint
(milestone). É a ponte entre os requisitos (Notion) e a implementação (GitHub).

> **Espelhar no Notion:** este arquivo é markdown; cole/importe no Notion e
> mantenha os números de issue/PR como link. A **fonte de verdade** do status é
> o board do GitHub.

**Legenda:** ✅ concluído · 🔜 próximo · ⏳ a fazer · Prioridade = MoSCoW · Est. = estimativa (Fibonacci)

> **Estado geral (24/08/2026):** as três milestones (M1, M2, M3) estão com
> **0 issues abertas**, não há issue nem PR aberto, e todo o trabalho está
> mergeado na `main` (até o PR #88). Depois de fechar as user stories, uma
> segunda leva de PRs (#80–#88) pôs o sistema para funcionar de ponta a ponta
> com dados reais — está na seção [Endurecimento e
> operação](#endurecimento-e-operação-pós-m3), que também registra os defeitos
> encontrados ao rodar o pipeline de verdade.

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

## Endurecimento e operação (pós-M3)

As user stories fechadas não bastavam para o sistema funcionar sozinho com
conteúdo real. Estes PRs não abriram issues novas — cada um corrige ou completa
uma US já entregue, e todos foram verificados executando o pipeline contra os
portais da UFCA, não só em teste.

| PR | O que resolveu | US/issue | ADR |
|---|---|---|---|
| #80 | Host do repositório de PDFs estava grafado em inglês (`documents`), que não resolve em DNS — o `PDFProcessor` **nunca** processou um anexo | US-03.1.2 (#54) | — |
| #81 | Conteúdo classificado passa a ser **aprovado automaticamente**; sem revisor de plantão o feed não recebia nada | US-05.2 (#27), US-03.2 (#17) | ADR-009 |
| #82 | **Agendador** das tarefas periódicas (serviço `scheduler`) e configuração de e-mail — antes nada disparava coleta, digest ou push | US-04.1 (#24), US-04.3 (#22), US-03.1 (#16) | ADR-008 (proposta → aceito) |
| #83 | `URLField` com o padrão de 200 caracteres estourava nas URLs reais da UFCA e **abortava a coleta da fonte inteira** | US-03.1 (#16), #52 | — |
| #84 | **Modo produção**: gunicorn, WhiteNoise, SPA servida pela aplicação, headers de segurança | — | ADR-010 |
| #85 | Conteúdo coletado não era direcionado a ninguém: 0 universais, 0 interesses — o perfil sem curso via **zero** notícias | US-01.2 (#14), US-03.2 (#17) | ADR-011 |
| #86 | Resumidor estava órfão (nenhum caminho o chamava) e só olhava o corpo; passa a ler o texto dos PDFs anexados | US-03.3 (#18) | ADR-012 |
| #87 | Feed não devolvia `url` nem `prazo` — o estudante não conseguia abrir o edital nem sabia até quando se inscrever | US-01.2 (#14), US-03.3 (#18) | — |
| #88 | **Tela de moderação** da fila de revisão; a #27 tinha entregue só a API JSON | US-05.2 (#27) | — |

**Padrão que se repetiu:** três módulos foram entregues com testes verdes e
**nunca chamados por nenhum caminho de execução** — o `PDFProcessor` (#80/#67),
o direcionamento do conteúdo (#85) e o resumidor (#86). Testes de unidade não
pegam integração ausente; foi rodar a coleta real que expôs os três.

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
| PR #79 | Atualização desta matriz até o PR #78 | ✅ |

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

_Última atualização: 24/08/2026 (após o PR #88) — cruzada com as issues, PRs e milestones do GitHub. Nenhuma issue ou PR aberto; M1–M3 fechadas e mergeadas na `main`. As decisões técnicas dos PRs #80–#88 estão nas ADR-008 a ADR-012 em [decisoes.md](decisoes.md). Atualizar a cada merge relevante ou fechamento de sprint._
