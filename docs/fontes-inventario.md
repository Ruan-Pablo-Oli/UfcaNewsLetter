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

## Pró-Reitorias e Direções (P2/P3) — categorias de informe

**Levantamento feito em 23/08/2026** a partir do `wp-sitemap.xml` do portal, não
de lista manual. As 46 categorias abaixo são as taxonomias reais de informe; a
coluna "Itens" foi medida requisitando cada página (`10+` significa que a
primeira página encheu — há mais).

Todas retornaram **HTTP 200** e são **permitidas pelo `robots.txt`**, que só
proíbe `/portal/wp-admin/`.

> **Bloqueio técnico — leia antes de implementar.** O `NewsInformeCollector`
> extrai **zero** itens dessas páginas hoje. Não é markup ruim: `_is_article_path`
> exige que o artigo esteja sob o path da listagem, e aqui a listagem é
> `/noticias/informe_category/<slug>/` enquanto os itens ficam em `/informes/<slug>/`.
> Todo link é rejeitado pelo filtro de prefixo. Verificado ao vivo: o mesmo
> coletor extrai 14 itens de `/noticias/` e 10 de `/informes/`.
>
> Implementar esta US exige, antes, permitir listagens cujos itens vivem fora do
> próprio prefixo — a "variação de markup" que as tarefas da issue já previam.

As colunas **Responsável** e **Valor** são decisão humana. O valor proposto
abaixo é sugestão baseada no público do produto (estudante de graduação), não
validação — confirme antes de marcar "Validada".

| Categoria | URL | Tipo | Prioridade | Itens | Responsável | Valor p/ estudante | Validada |
|---|---|---|---|---|---|---|---|
| `acessibilidade` | `https://www.ufca.edu.br/noticias/informe_category/acessibilidade/` | `html` | P2 | 10+ | | alta (proposta) | não |
| `acoes-de-extensao` | `https://www.ufca.edu.br/noticias/informe_category/acoes-de-extensao/` | `html` | P2 | 10+ | | alta (proposta) | não |
| `assuntos-estudantis` | `https://www.ufca.edu.br/noticias/informe_category/assuntos-estudantis/` | `html` | P2 | 10+ | | alta (proposta) | não |
| `auxilios` | `https://www.ufca.edu.br/noticias/informe_category/auxilios/` | `html` | P2 | 10+ | | alta (proposta) | não |
| `bibliotecas` | `https://www.ufca.edu.br/noticias/informe_category/bibliotecas/` | `html` | P2 | 10+ | | alta (proposta) | não |
| `cultura` | `https://www.ufca.edu.br/noticias/informe_category/cultura/` | `html` | P2 | 10+ | | alta (proposta) | não |
| `editais` | `https://www.ufca.edu.br/noticias/informe_category/editais/` | `html` | P2 | 10+ | | alta (proposta) | não |
| `educacao-a-distancia` | `https://www.ufca.edu.br/noticias/informe_category/educacao-a-distancia/` | `html` | P2 | 10+ | | alta (proposta) | não |
| `ensino` | `https://www.ufca.edu.br/noticias/informe_category/ensino/` | `html` | P2 | 10+ | | alta (proposta) | não |
| `estagio` | `https://www.ufca.edu.br/noticias/informe_category/estagio/` | `html` | P2 | 10+ | | alta (proposta) | não |
| `extensao` | `https://www.ufca.edu.br/noticias/informe_category/extensao/` | `html` | P2 | 10+ | | alta (proposta) | não |
| `graduacao` | `https://www.ufca.edu.br/noticias/informe_category/graduacao/` | `html` | P2 | 10+ | | alta (proposta) | não |
| `internacional` | `https://www.ufca.edu.br/noticias/informe_category/internacional/` | `html` | P2 | 10+ | | alta (proposta) | não |
| `integralizacao` | `https://www.ufca.edu.br/noticias/informe_category/integralizacao/` | `html` | P2 | 4 | | alta (proposta) | não |
| `chamada-para-trabalhos` | `https://www.ufca.edu.br/noticias/informe_category/chamada-para-trabalhos/` | `html` | P2 | 2 | | alta (proposta) | não |
| `cursos` | `https://www.ufca.edu.br/noticias/informe_category/cursos/` | `html` | P2 | 2 | | alta (proposta) | não |
| `bolsistas` | `https://www.ufca.edu.br/noticias/informe_category/bolsistas/` | `html` | P2 | 1 | | alta (proposta) | não |
| `empresa-junior` | `https://www.ufca.edu.br/noticias/informe_category/empresa-junior/` | `html` | P2 | 1 | | alta (proposta) | não |
| `administracao` | `https://www.ufca.edu.br/noticias/informe_category/administracao/` | `html` | P3 | 10+ | | baixa (proposta) | não |
| `administrativo` | `https://www.ufca.edu.br/noticias/informe_category/administrativo/` | `html` | P3 | 10+ | | baixa (proposta) | não |
| `corregedoria` | `https://www.ufca.edu.br/noticias/informe_category/corregedoria/` | `html` | P3 | 10+ | | baixa (proposta) | não |
| `covid-19` | `https://www.ufca.edu.br/noticias/informe_category/covid-19/` | `html` | P3 | 10+ | | baixa (proposta) | não |
| `gestao-de-pessoas` | `https://www.ufca.edu.br/noticias/informe_category/gestao-de-pessoas/` | `html` | P3 | 10+ | | baixa (proposta) | não |
| `infraestrutura` | `https://www.ufca.edu.br/noticias/informe_category/infraestrutura/` | `html` | P3 | 10+ | | baixa (proposta) | não |
| `institucional` | `https://www.ufca.edu.br/noticias/informe_category/institucional/` | `html` | P3 | 10+ | | baixa (proposta) | não |
| `licitacoes` | `https://www.ufca.edu.br/noticias/informe_category/licitacoes/` | `html` | P3 | 10+ | | baixa (proposta) | não |
| `orgaos-complementares` | `https://www.ufca.edu.br/noticias/informe_category/orgaos-complementares/` | `html` | P3 | 10+ | | baixa (proposta) | não |
| `pesquisa-e-inovacao` | `https://www.ufca.edu.br/noticias/informe_category/pesquisa-e-inovacao/` | `html` | P3 | 10+ | | a decidir | não |
| `pros-reitorias` | `https://www.ufca.edu.br/noticias/informe_category/pros-reitorias/` | `html` | P3 | 10+ | | baixa (proposta) | não |
| `reitoria-informa` | `https://www.ufca.edu.br/noticias/informe_category/reitoria-informa/` | `html` | P3 | 10+ | | baixa (proposta) | não |
| `ti` | `https://www.ufca.edu.br/noticias/informe_category/ti/` | `html` | P3 | 10+ | | baixa (proposta) | não |
| `pos-graduacao` | `https://www.ufca.edu.br/noticias/informe_category/pos-graduacao/` | `html` | P3 | 8 | | a decidir | não |
| `sustentabilidade` | `https://www.ufca.edu.br/noticias/informe_category/sustentabilidade/` | `html` | P3 | 7 | | baixa (proposta) | não |
| `avaliacao-institucional` | `https://www.ufca.edu.br/noticias/informe_category/avaliacao-institucional/` | `html` | P3 | 6 | | baixa (proposta) | não |
| `encontro-de-extensao` | `https://www.ufca.edu.br/noticias/informe_category/encontro-de-extensao/` | `html` | P3 | 6 | | a decidir | não |
| `pos-graduacao-pros-reitorias` | `https://www.ufca.edu.br/noticias/informe_category/pos-graduacao-pros-reitorias/` | `html` | P3 | 6 | | a decidir | não |
| `ufca-itinerante` | `https://www.ufca.edu.br/noticias/informe_category/ufca-itinerante/` | `html` | P3 | 6 | | a decidir | não |
| `ouvidoria` | `https://www.ufca.edu.br/noticias/informe_category/ouvidoria/` | `html` | P3 | 5 | | baixa (proposta) | não |
| `planejamento` | `https://www.ufca.edu.br/noticias/informe_category/planejamento/` | `html` | P3 | 5 | | baixa (proposta) | não |
| `orgaos-suplementares` | `https://www.ufca.edu.br/noticias/informe_category/orgaos-suplementares/` | `html` | P3 | 2 | | baixa (proposta) | não |
| `premio-voce-faz-a-extensao` | `https://www.ufca.edu.br/noticias/informe_category/premio-voce-faz-a-extensao/` | `html` | P3 | 2 | | a decidir | não |
| `revista-entreacoes` | `https://www.ufca.edu.br/noticias/informe_category/revista-entreacoes/` | `html` | P3 | 2 | | a decidir | não |
| `cerimonial` | `https://www.ufca.edu.br/noticias/informe_category/cerimonial/` | `html` | P3 | 1 | | baixa (proposta) | não |
| `expediente` | `https://www.ufca.edu.br/noticias/informe_category/expediente/` | `html` | P3 | 1 | | baixa (proposta) | não |
| `proex-mais-perto-de-voce` | `https://www.ufca.edu.br/noticias/informe_category/proex-mais-perto-de-voce/` | `html` | P3 | 1 | | a decidir | não |
| `programa-de-formacao` | `https://www.ufca.edu.br/noticias/informe_category/programa-de-formacao/` | `html` | P3 | 1 | | a decidir | não |

## Fontes recusadas

Registrar aqui o que foi avaliado e **descartado**, com o motivo. Evita que a
mesma URL seja reavaliada do zero daqui a seis meses.

| Unidade | URL | Motivo da recusa | Quem avaliou |
|---|---|---|---|
| | | | |

## Campi (P3) — candidatos do sitemap, não avaliados

O sitemap também expõe páginas por campus:
`/instituicao/campi/{barbalha,brejo-santo,crato,ico,juazeiro-do-norte}/`.
São páginas institucionais (apresentação da unidade), não listagens de
comunicado — provavelmente sem valor recorrente para o feed. Não foram medidas
nem avaliadas; ficam registradas para não serem redescobertas do zero.

## Depois de preencher

Com as linhas validadas e o filtro de prefixo do coletor ajustado, o resto da
US-03.1.5 é mecânico: criar os registros `Fonte` correspondentes e adicionar
fixtures por categoria cobrindo a variação de markup. O formato de registro
extraído e a deduplicação são os mesmos da US-03.1.1, sem código novo de
pipeline.

## Como este levantamento foi feito

Reprodutível, sem lista manual:

1. `robots.txt` → confirma o que é permitido e aponta o `wp-sitemap.xml`.
2. `wp-sitemap-taxonomies-informe_category-1.xml` → as 46 categorias reais.
3. Requisição a cada categoria, contando links para `/informes/<slug>/`.
4. Execução do `NewsInformeCollector` real contra as URLs, que revelou o
   bloqueio do filtro de prefixo.
