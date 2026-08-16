<#
.SYNOPSIS
    Start the Retail Personalisation backend the canonical way.

.DESCRIPTION
    ALWAYS use this script (or stop_backend.ps1 before manual starts). It:

      1. Kills every existing backend process (port owner + stale app.main
         python processes + old live_pid.txt reference) so no duplicate
         server can linger or hold the SQLite file open.
      2. Starts a fresh uvicorn on a single port (default 8000, matching the
         Vite proxy and the deployed frontend build).
      3. Writes the real PID to live_pid.txt and waits for /api/health.

    Do NOT start uvicorn manually in extra terminals while the server is
    already running - that is what caused the recurring "Something went
    wrong" errors (backend down / wrong port / duplicate processes).

.PARAMETER Port
    Default 8000. Port for the backend (must match the Vite proxy target).

.PARAMETER NoLog
    Do not write stdout/stderr to backend/logs/backend_*.log.
#>
[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8000,
    [switch]$NoLog
)

$ErrorActionPreference = "Stop"
$BackendDir  = Split-Path -Parent $PSScriptRoot        # <repo>/backend
$ProjectRoot = Split-Path -Parent $BackendDir          # <repo>
$VenvPython  = Join-Path $BackendDir "venv\Scripts\python.exe"
$DataDir     = Join-Path $BackendDir "data"
$LogDir      = Join-Path $BackendDir "logs"
$OutLog      = Join-Path $LogDir "backend_out.log"
$ErrLog      = Join-Path $LogDir "backend_err.log"
$PidFile     = Join-Path $BackendDir "live_pid.txt"

# Ensure prereqs.
if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Error "Virtualenv Python not found at: $VenvPython`nRun:  python -m venv venv" +
        "`n      .\venv\Scripts\pip install -r requirements.txt"
    exit 1
}
New-Item -ItemType Directory -Force -Path $DataDir, $LogDir | Out-Null

# ---- 1. Kill anything old so a clean, single process starts ----------------
Write-Host "[1/3] Stopping any existing backend on port $Port ..."
& (Join-Path $PSScriptRoot "stop_backend.ps1") -Port $Port

# ---- 2. Start the backend (no --reload: reload spawns duplicate workers) ---
Write-Host "[2/3] Starting backend on port $Port ..."
$args = @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$Port")
if ($NoLog) {
    $proc = Start-Process -FilePath $VenvPython -ArgumentList $args `
        -WorkingDirectory $BackendDir -PassThru -WindowStyle Hidden
} else {
    $proc = Start-Process -FilePath $VenvPython -ArgumentList $args `
        -WorkingDirectory $BackendDir `
        -RedirectStandardOutput $OutLog `
        -RedirectStandardError $ErrLog `
        -PassThru -WindowStyle Hidden
}

# Record the PID (venv's python.exe is a tiny launcher that spawns the real
# interpreter, so the PID file is informational only - stop_backend.ps1 also
# matches by port and command line, which always catches the true listener).
$proc.Id | Set-Content -LiteralPath $PidFile -Encoding ASCII
Write-Host "    Started PID $($proc.Id) -> $OutLog (errors: $ErrLog)"

# ---- 3. Wait for health (up to ~30s; first boot may seed data) -------------
Write-Host "[3/3] Waiting for /api/health on port $Port ..."
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 1000
    try {
        $h = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 3
        Write-Host "    Backend healthy after $($i + 1)s: $($h.status) ($($h.title) v$($h.version))"
        Write-Host "Backend is UP on port $Port. Open http://localhost:$Port or the Vite dev server."
        exit 0
    } catch {
        # keep waiting
    }
}
Write-Host "Backend started but is NOT healthy yet - check $ErrLog"
exit 1