Write-Host "Setting up Electoral Evidence Agent MVP..." -ForegroundColor Cyan

if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env created from .env.example" -ForegroundColor Green
} else {
    Write-Host ".env already exists" -ForegroundColor Yellow
}

docker compose up --build
