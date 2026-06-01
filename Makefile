.PHONY: up down logs test migrate seed api dashboard

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

test:
	docker compose exec api pytest

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python db/seeds/seed_catalogs.py && docker compose exec api python db/seeds/seed_pilot_election.py

api:
	docker compose up api

dashboard:
	docker compose up dashboard
