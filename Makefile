.PHONY: up down build logs restart ps shell

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