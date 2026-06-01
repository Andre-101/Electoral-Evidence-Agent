Write-Host "Resetting Docker volumes..." -ForegroundColor Yellow
docker compose down -v
docker compose up --build
