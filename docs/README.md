# Documentação — UFCA Newsletter

Documentação **técnica e de processo** do projeto. A pesquisa de UX e os
requisitos (entrevistas, AEIOU, mapas de empatia, HMW, personas, user stories)
ficam no **Notion**; aqui mora o que muda junto com o código.

## Índice

| Documento | O que contém |
|---|---|
| [Arquitetura](arquitetura.md) | Stack, estrutura de apps, modelo de dados (diagrama ER), autenticação e rotas |
| [Decisões (ADRs)](decisoes.md) | Registro do *porquê* das principais decisões técnicas |
| [Fluxo de trabalho](fluxo-de-trabalho.md) | Ambiente local, testes, fluxo de PR/CI, proteção do `main`, uso do agente `@claude` |
| [Rastreabilidade](rastreabilidade.md) | Matriz User Story → issue → PR → status (espelhar no Notion) |

## Fonte de verdade

- **Backlog, status e código:** GitHub (issues, [board do projeto](https://github.com/Ruan-Pablo-Oli/UfcaNewsLetter/issues), PRs, este repositório).
- **Pesquisa/UX e relatório narrativo:** Notion.

Para evitar backlog duplicado e desatualizado, o **board do GitHub é a única
fonte do backlog**; o Notion referencia os números de issue/PR.
