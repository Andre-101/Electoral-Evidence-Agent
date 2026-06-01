# Setup

## Requirements

- Docker Desktop
- Docker Compose
- Git
- PowerShell, Bash or a compatible terminal

## Start

```powershell
copy .env.example .env
docker compose up --build
```

In another terminal:

```powershell
docker compose exec api alembic upgrade head
docker compose exec api python db/seeds/seed_catalogs.py
docker compose exec api python db/seeds/seed_pilot_election.py
docker compose exec api pytest
```

## URLs

```text
Dashboard: http://localhost:8501
API docs:  http://localhost:8000/docs
Health:    http://localhost:8000/health
```

## Reset

```powershell
docker compose down -v
docker compose up --build
```
