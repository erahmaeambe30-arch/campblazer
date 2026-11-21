# CampBlazer: start everything on this laptop and open a free public HTTPS link.
# Run from the campblazer folder in the VS Code terminal:
#     powershell -ExecutionPolicy Bypass -File .\start-public.ps1
# Needs (once): Docker Desktop running, backend\.venv set up, frontend npm install done,
# cloudflared installed (winget install --id Cloudflare.cloudflared),
# and in backend\.env:  DJANGO_DEBUG=False
#                       DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,.trycloudflare.com
#                       SERVE_MEDIA=1

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "1/4 Starting PostgreSQL + Redis (Docker)..." -ForegroundColor Cyan
docker compose up -d
if ($LASTEXITCODE -ne 0) { Write-Host "Docker failed. Open Docker Desktop first, then run this again." -ForegroundColor Red; exit 1 }

Write-Host "2/4 Starting Django backend with 4 worker processes (new window)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; .\.venv\Scripts\Activate.ps1; python run_server_windows.py --workers 4"

Write-Host "3/4 Building and serving the frontend (new window)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run build; npm run preview"

Write-Host "    Waiting 25 seconds for both to start..."
Start-Sleep -Seconds 25

Write-Host "4/4 Opening the public tunnel (new window)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cloudflared tunnel --url http://localhost:4173"

Write-Host ""
Write-Host "Done. In the cloudflared window, copy the https://....trycloudflare.com link and share it." -ForegroundColor Green
Write-Host "To stop: close the three new windows, then run: docker compose stop"
