Write-Host "Running demo pipeline..." -ForegroundColor Cyan
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/demo/run"
