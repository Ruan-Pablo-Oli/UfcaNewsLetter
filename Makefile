.PHONY: up down build logs restart ps shell

up: build
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

restart:
	docker compose restart

ps:
	docker compose ps

shell:
	docker compose exec web bash