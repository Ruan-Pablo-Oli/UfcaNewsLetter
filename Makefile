.PHONY: up down build logs restart ps shell seed-demo

.env:
	cp .env.example .env

up: build
	docker compose up -d

down:
	docker compose down

build: .env
	docker compose build

logs:
	docker compose logs -f

restart:
	docker compose restart

ps:
	docker compose ps

shell:
	docker compose exec web bash

# Popula o banco com conteúdos fictícios (dados falsos, só para desenvolvimento
# e demonstração enquanto o coletor automático não existe — ver #16).
seed-demo:
	docker compose exec web python manage.py seed_conteudos