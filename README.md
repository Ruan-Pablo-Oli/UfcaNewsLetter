# UFCA Newsletter

## Docker

### Stack

| Componente | Versão |
|---|---|
| Python | 3.12-slim |
| Django | 6.0.x |
| requests | 2.34.x |
| beautifulsoup4 | 4.15.x |
| lxml | 6.1.x |
| PyMuPDF | 1.27.x |
| python-dateutil | 2.9.x |

### Serviços

| Serviço | Porta | Descrição |
|---|---|---|
| `web` | `8000` | Aplicação Django |

### Como usar

```bash
make build    # constrói a imagem
make up       # sobe o container
make logs     # acompanha os logs
make shell    # bash interativo no container
make down     # derruba o container
```

Ou diretamente com Docker Compose:

```bash
docker compose up -d
```

### Estrutura

```text
  ./
  Dockerfile
  compose.yaml
  requirements.txt
  Makefile
  README.md   
  app/   # código da aplicação (próximas entregas)

```
