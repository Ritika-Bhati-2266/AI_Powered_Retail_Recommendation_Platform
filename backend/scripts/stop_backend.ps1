<#
.SYNOPSIS
    Stop the Retail Personalisation backend cleanly.

.DESCRIPTION
    Kills every process that belongs to this project's backend:
      - anything listening on the target port,
      - any python process running `app.main:app` from this project,
      - the stale PID recorded in live_pid.txt (if any).

    Use this instead of closing individual terminals - it guarantees no
    orphan/duplicate backend processes remain before a fresh start.

.PARAMETER Port
    Default 8000. The backend port this project is configured to use
    (the Vite proxy and the start script both default to 8000).
#>
[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8000
)

$ErrorActionPreference = "Continue"
$BackendDir  = Split-Path -Parent $PSScriptRoot
$ProjectRoot = Split-Path -Parent $BackendDir

$stopped = [System.Collections.Generic.List[int]]::new()

# 1) Kill anything currently listening on the target port.
foreach ($l in (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) {
    $pid_ = $l.OwningProcess
    if ($pid_ -and $pid_ -ne $PID) {
        try {
            Stop-Process -Id $pid_ -Force -ErrorAction Stop | Out-Null
            $stopped.Add([int]$pid_)
        } catch {}
    }
}

# 2) Kill any python process running this app (catches leftover reloader
#    workers and the venv->base-python child, even when they hold no port).
$matches = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "app\.main:app" -and $_.CommandLine -match [regex]::Escape($ProjectRoot) }
foreach ($m in $matches) {
    if ($m.ProcessId -and $m.ProcessId -ne $PID) {
        try {
            Stop-Process -Id $m.ProcessId -Force -ErrorAction Stop | Out-Null
            $stopped.Add([int]$m.ProcessId)
        } catch {}
    }
}

# 3) Stale pid-file reference.
$pidFile = Join-Path $BackendDir "live_pid.txt"
if (Test-Path -LiteralPath $pidFile) {
    $old = (Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if ($old -match '^\d+$') {
        try {
            Stop-Process -Id ([int]$old) -Force -ErrorAction Stop | Out-Null
            $stopped.Add([int]$old)
        } catch {}
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

if ($stopped.Count -gt 0) {
    Write-Host "Stopped $($stopped.Count) backend process(es): $($stopped -join ', ')"
} else {
    Write-Host "No backend process was running on port $Port."
}

# Double-check the port is now free.
$leftover = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($leftover) {
    Write-Warning "Port $Port is still in use (PID $($leftover.OwningProcess -join ',')) - closing it anyway."
    foreach ($l in $leftover) { try { Stop-Process -Id $l.OwningProcess -Force -ErrorAction Stop | Out-Null } catch {} }
    Start-Sleep -Milliseconds 300
} else {
    Write-Host "Port $Port is free."
}