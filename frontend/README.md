# Frontend — UFCA Newsletter

SPA em React 19 + Vite que consome a API do Django. Autenticação por sessão
(cookie + CSRF), roteamento com `react-router-dom`.

## Desenvolvimento

O backend precisa estar no ar (`make up` na raiz do repositório). O dev server
faz proxy de `/accounts`, `/feed` e `/feedback` para `http://localhost:8000`,
então **acesse a aplicação pela porta do Vite** — assim o cookie de sessão e o
CSRF ficam na mesma origem.

```bash
npm install
npm run dev      # http://localhost:5173
```

Sem conteúdo no banco o feed aparece vazio; rode `make seed-demo` na raiz para
popular dados fictícios.

## Testes

`vitest` + Testing Library, em ambiente jsdom.

```bash
npm test         # execução única
npm run test:watch
npm run lint
```

Os testes de `src/pages/Dashboard.test.jsx` mockam o módulo `../api` e o
contexto de autenticação — não exigem backend no ar.

## Estrutura

```text
  src/
    api.js              # wrapper de fetch (JSON + header X-CSRFToken)
    contexts/           # AuthContext: sessão do usuário
    components/         # ProtectedRoute, ReasonTooltip
    pages/              # Login, Signup, Dashboard (feed), Perfil
```
