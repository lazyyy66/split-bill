# Локальный запуск всего проекта: .\dev.ps1
# Поднимает Postgres + Redis в Docker, применяет миграции и открывает 4 окна:
# бот, API, Mini App (Vite) и ngrok-туннель. Закрыть — просто закрыть окна (или Ctrl+C в каждом).

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

# Домен ngrok берём из .env (NGROK_DOMAIN=...)
$domain = (Get-Content .env | Where-Object { $_ -match '^NGROK_DOMAIN=' }) -replace '^NGROK_DOMAIN=', ''
if (-not $domain) { throw "Добавь в .env строку NGROK_DOMAIN=<твой-домен>.ngrok-free.dev" }

# ngrok: из PATH, иначе — распакованный вручную в C:\ngrok
$ngrok = (Get-Command ngrok -ErrorAction SilentlyContinue).Source
if (-not $ngrok -and (Test-Path "C:\ngrok\ngrok.exe")) { $ngrok = "C:\ngrok\ngrok.exe" }
if (-not $ngrok) { throw "Не нашёл ngrok: установи (winget install ngrok.ngrok) или распакуй в C:\ngrok" }

Write-Host "Postgres и Redis..." -ForegroundColor Cyan
docker compose up -d --wait db redis
if ($LASTEXITCODE -ne 0) { throw "Docker не запустился — открой Docker Desktop и подожди 'Engine running'" }

Write-Host "Миграции..." -ForegroundColor Cyan
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Миграции не применились" }

if (-not (Test-Path "$root\webapp\node_modules")) {
    Write-Host "Зависимости Mini App..." -ForegroundColor Cyan
    Push-Location "$root\webapp"; npm install; Pop-Location
}

function Start-Window($title, $command, $dir = $root) {
    Start-Process powershell -WorkingDirectory $dir -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = '$title'; $command"
}

Start-Window "Split Bill: бот" "uv run python -m app.bot"
Start-Window "Split Bill: API" "uv run uvicorn app.api.main:create_app --factory --reload --port 8000"
Start-Window "Split Bill: Mini App" "npm run dev" "$root\webapp"
Start-Window "Split Bill: ngrok" "& '$ngrok' http 5173 --url=$domain"

Write-Host ""
Write-Host "Готово! Mini App: https://$domain" -ForegroundColor Green
Write-Host "Открывай через кнопку '📱 Открыть приложение' в группе (/start или /balance)."
