# Inventário de fontes monitoradas

Registro das fontes que o coletor monitora ou pode vir a monitorar. Existe para
satisfazer o primeiro critério da [US-03.1.5](https://github.com/Ruan-Pablo-Oli/UfcaNewsLetter/issues/57):
cada unidade precisa ter URL, tipo de conteúdo, prioridade e responsável pela
validação registrados **antes** de virar código.

> **Regra que não se contorna:** nenhuma URL é implementada como fonte
> monitorada sem validação manual registrada aqui. Apontar o coletor para uma
> página não verificada gera conteúdo errado no feed dos estudantes, e o
> adaptador não tem como perceber isso sozinho.

## O que "validar" significa

Antes de marcar uma linha como validada, confirme os cinco itens:

1. **A URL existe e é estável** — não é redirect temporário, não muda de path a cada semestre.
2. **`robots.txt` permite a coleta** daquele path (`https://<host>/robots.txt`).
3. **O markup é extraível** — a listagem tem itens identificáveis, com link, título e data.
4. **O conteúdo tem valor para o público do produto** — estudante de graduação da UFCA. Página institucional estática, organograma e histórico da unidade não têm.
5. **Há um responsável nomeado** por reconferir a fonte quando ela quebrar.

## Tipos de conteúdo

O valor da coluna "Tipo" deve ser um dos `Fonte.Tipo` que já têm adaptador
(`app/newsletter/coleta.py`, `REGISTRO_COLETORES`):

| Tipo | Adaptador | Entregue em |
|---|---|---|
| `html` | `NewsInformeCollector` | US-03.1.1 (PR #59) |
| `concurso` | `ConcursosSelecoesCollector` | US-03.1.4 (PR #65) |
| `calendario` | `CalendarioCollector` | US-03.1.3 (PR #68) |

Uma fonte cujo tipo não tenha adaptador é **pulada** pelo orquestrador, com
motivo registrado — não quebra a coleta, mas também não coleta nada.

## Fontes já implementadas (P0/P1)

URLs extraídas do código já em produção. Onde a coluna "Validada" diz
*confirmar*, a URL aparece apenas em fixtures de teste e no seed — o adaptador
recebe a listagem por parâmetro e não fixa nenhum host —, então ela **não** é
prova de que a página real foi verificada.

| Unidade / Origem | URL | Tipo | Prioridade | Responsável | Validada |
|---|---|---|---|---|---|
| Portal UFCA — Notícias e Informes | `https://www.ufca.edu.br/noticias/` | `html` | P0 | — | confirmar (só em fixtures/seed) |
| Portal UFCA — Concursos e Seleções | `https://www.ufca.edu.br/admissao/concursos-e-selecoes/` | `concurso` | P1 | — | sim (US-03.1.4) |
| Portal UFCA — Docentes efetivos | `https://www.ufca.edu.br/admissao/concursos-e-selecoes/docentes/efetivo/` | `concurso` | P1 | — | sim (US-03.1.4) |
| Portal UFCA — Calendários e Eventos | `https://www.ufca.edu.br/calendarios/` | `calendario` | P1 | — | sim (US-03.1.3, documentada no adaptador) |

A coluna "Responsável" está vazia porque essas fontes entraram antes de este
inventário existir. Vale preencher retroativamente — sem responsável nomeado,
ninguém percebe quando a fonte quebra.

As duas URLs de concursos são as únicas fixadas em código
(`app/newsletter/collectors/concursos_selecoes.py`); a de calendários está
documentada no adaptador; a de notícias, não.

## Pró-Reitorias e Direções (P2) — a preencher

| Unidade | URL | Tipo | Prioridade | Responsável | robots.txt OK | Validada |
|---|---|---|---|---|---|---|
| _(exemplo do formato — substituir)_ | `https://…` | `html` | P2 | Nome | sim/não | não |

## Campi e Unidades Acadêmicas (P3) — a preencher

| Unidade | URL | Tipo | Prioridade | Responsável | robots.txt OK | Validada |
|---|---|---|---|---|---|---|
| _(exemplo do formato — substituir)_ | `https://…` | `html` | P3 | Nome | sim/não | não |

## Fontes recusadas

Registrar aqui o que foi avaliado e **descartado**, com o motivo. Evita que a
mesma URL seja reavaliada do zero daqui a seis meses.

| Unidade | URL | Motivo da recusa | Quem avaliou |
|---|---|---|---|
| | | | |

## Depois de preencher

Com as linhas P2/P3 validadas, a implementação da US-03.1.5 é mecânica:
criar os registros `Fonte` correspondentes e adicionar fixtures de teste por
unidade, cobrindo ao menos uma variação de markup — o formato de registro
extraído e a deduplicação são os mesmos da US-03.1.1, sem código novo de
pipeline.
