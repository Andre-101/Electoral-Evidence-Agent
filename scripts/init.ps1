Write-Host "Initializing database..." -ForegroundColor Cyan

docker compose exec api alembic upgrade head
docker compose exec api python db/seeds/seed_catalogs.py
docker compose exec api python db/seeds/seed_pilot_election.py

Write-Host "Database initialized." -ForegroundColor Green
