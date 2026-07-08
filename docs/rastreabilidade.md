# Matriz de Rastreabilidade

Liga cada **User Story / tarefa técnica → issue → PR → status**, por sprint
(milestone). É a ponte entre os requisitos (Notion) e a implementação (GitHub).

> **Espelhar no Notion:** este arquivo é markdown; cole/importe no Notion e
> mantenha os números de issue/PR como link. A **fonte de verdade** do status é
> o board do GitHub.

**Legenda:** ✅ concluído · 🔜 próximo · ⏳ a fazer · Prioridade = MoSCoW · Est. = estimativa (Fibonacci)

## M1 — Base de dados e personalização (venc. 25/07)

### Fundação técnica — ✅ concluída (épico #38)

| Issue | Tarefa | Prioridade | Est. | PR | Status |
|---|---|---|---|---|---|
| #36 | Configurar PostgreSQL e variáveis de ambiente | must | 3 | #39 | ✅ |
| #37 | Testes automatizados e CI (pytest + ruff) | must | 3 | #40 | ✅ |
| #34 | Modelar entidades centrais do domínio | must | 8 | #41 | ✅ |
| #35 | Autenticação e cadastro de usuários | must | 5 | #43 | ✅ |
| #21 | Definir requisitos funcionais e não funcionais | must | — | — | ✅ (doc) |

### FEAT-01 — Motor de Personalização (user stories)

| Issue | US | Título | Prioridade | Est. | PR | Status |
|---|---|---|---|---|---|---|
| #12 | US-01 | Definir filtros de conteúdos (história-mãe) | — | — | — | ⏳ |
| #13 | US-01.1 | Configurar perfil acadêmico | must | 3 | — | 🔜 |
| #14 | US-01.2 | Receber conteúdo personalizado | must | 5 | — | ⏳ |
| #15 | US-01.3 | Ajustar nível de relevância | must | 3 | — | ⏳ |

## M2 — Coleta e processamento de conteúdo (venc. 15/08)

### FEAT-03 — Extração e Indexação (épico #30)

| Issue | US | Título | Prioridade | Est. | Status |
|---|---|---|---|---|---|
| #16 | US-03.1 | Coletar conteúdo automaticamente | must | 8 | ⏳ |
| #17 | US-03.2 | Classificar conteúdo por categoria | must | 5 | ⏳ |
| #18 | US-03.3 | Resumir conteúdo extenso | must | 5 | ⏳ |

## M3 — Integração e MVP funcional (venc. 05/09)

### FEAT-04 — Distribuição da Newsletter (épico #31)

| Issue | US | Título | Prioridade | Est. | Status |
|---|---|---|---|---|---|
| #24 | US-04.1 | Receber newsletter por e-mail | must | 8 | ⏳ |
| #25 | US-04.2 | Configurar frequência e canais de entrega | should | 3 | ⏳ |
| #22 | US-04.3 | Notificações no sistema (push) | should | 5 | ⏳ |

### FEAT-05 — Painel de Administração (épico #32)

| Issue | US | Título | Prioridade | Est. | Status |
|---|---|---|---|---|---|
| #26 | US-05.1 | Gerenciar fontes de conteúdo | must | 5 | ⏳ |
| #27 | US-05.2 | Moderar fila de conteúdo para revisão | should | 5 | ⏳ |

### FEAT-07 — Histórico e Busca (épico #33)

| Issue | US | Título | Prioridade | Est. | Status |
|---|---|---|---|---|---|
| #28 | US-07.1 | Buscar conteúdos | should | 5 | ⏳ |
| #29 | US-07.2 | Acessar histórico de conteúdos | should | 3 | ⏳ |

## Melhorias de processo (sem user story)

| Issue/PR | Descrição | Status |
|---|---|---|
| PR #23 | Configuração inicial do agente Claude (GitHub Actions) | ✅ |
| PR #42 | Liberar comandos de build/test ao agente (`--allowedTools`) | ✅ |

---

_Última atualização: julho/2026 (após conclusão da M1 — fundação técnica). Atualizar a cada merge relevante ou fechamento de sprint._
