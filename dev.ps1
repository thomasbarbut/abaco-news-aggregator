# dev.ps1 — Start the ABACO News local dev server (no Docker required)
#
# Usage (from the repo root):
#   .\dev.ps1               # starts backend + frontend
#   .\dev.ps1 -BackendOnly  # starts only the FastAPI backend
#   .\dev.ps1 -FrontendOnly # starts only the Vite frontend
#
# URLs once running:
#   http://localhost:5173        — full app (Vite dev server + API proxy)
#   http://localhost:8000/docs   — FastAPI Swagger UI
#   http://localhost:8000/health — backend health check

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
if (-not $Root) { $Root = (Get-Location).Path }

$BackendDir  = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$VenvDir     = Join-Path $BackendDir ".venv"
$VenvPip     = Join-Path $VenvDir "Scripts\pip.exe"
$VenvUvicorn = Join-Path $VenvDir "Scripts\uvicorn.exe"

$BackendProc = $null

function Stop-Backend {
    if ($BackendProc -and -not $BackendProc.HasExited) {
        Write-Host "`nStopping backend (PID $($BackendProc.Id))..."
        $BackendProc.Kill()
    }
}

# ── Dev environment variables ─────────────────────────────────────────────────
# Use SQLite so no PostgreSQL install is needed. These env vars are inherited
# by all child processes (Start-Process picks up $env: variables automatically).
$DbPath = ($BackendDir -replace '\\', '/') + '/dev.db'
$env:DATABASE_URL             = "sqlite+aiosqlite:///$DbPath"
$env:DEBUG                    = "true"
$env:DOMAIN                   = "localhost"
$env:JWT_SECRET               = "dev_insecure_secret_do_not_use_in_production"
$env:CELERY_TASK_ALWAYS_EAGER = "true"
$env:MICROSOFT_CLIENT_ID      = "placeholder"
$env:MICROSOFT_CLIENT_SECRET  = "placeholder"
$env:MICROSOFT_TENANT_ID      = "placeholder"
$env:MICROSOFT_REDIRECT_URI   = "http://localhost:8000/api/auth/callback"
$env:REDIS_URL                = "redis://localhost:6379/0"
$env:SMTP_HOST                = ""
$env:SMTP_USER                = ""
$env:SMTP_PASSWORD            = ""
$env:ALERT_EMAIL              = "dev@localhost"
$env:SYNC_INTERVAL_MINUTES    = "15"

# ── Backend ───────────────────────────────────────────────────────────────────
if (-not $FrontendOnly) {
    if (-not (Test-Path $VenvDir)) {
        Write-Host "[backend] Creating Python virtual environment..."
        python -m venv $VenvDir
    }

    Write-Host "[backend] Installing dependencies (this may take a minute on first run)..."
    & $VenvPip install -r (Join-Path $BackendDir "requirements.txt") -q

    Write-Host "[backend] Starting FastAPI on http://localhost:8000 ..."
    $BackendProc = Start-Process -FilePath $VenvUvicorn `
        -ArgumentList "app.main:app", "--port", "8000", "--reload" `
        -WorkingDirectory $BackendDir `
        -PassThru `
        -NoNewWindow

    Write-Host "[backend] PID $($BackendProc.Id) — waiting 4 s for startup..."
    Start-Sleep -Seconds 4

    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-Host "[backend] Health check OK: $($resp.Content)"
    } catch {
        Write-Host "[backend] Health check timed out — backend may still be starting."
    }
}

# ── Frontend ──────────────────────────────────────────────────────────────────
if (-not $BackendOnly) {
    Write-Host ""
    Write-Host "========================================================"
    Write-Host "  App:      http://localhost:5173"
    Write-Host "  API docs: http://localhost:8000/docs"
    Write-Host "========================================================"
    Write-Host ""

    Push-Location $FrontendDir
    try {
        if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
            Write-Host "[frontend] Installing npm dependencies..."
            npm install
        }
        Write-Host "[frontend] Starting Vite dev server..."
        npm run dev
    } finally {
        Pop-Location
        Stop-Backend
    }
} else {
    Write-Host ""
    Write-Host "Backend running. Press Ctrl+C to stop."
    $BackendProc.WaitForExit()
}
