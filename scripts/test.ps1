Write-Host "Running tests..." -ForegroundColor Cyan
docker compose exec api pytest
