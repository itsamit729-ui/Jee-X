# Runs one batch; used by Windows Task Scheduler (see install_schedule_windows.ps1).
# Set $Shard to "1/2" on one laptop and "2/2" on the other when two people split the work.
param([string]$Shard = "")

$ErrorActionPreference = "Continue"
$Home_ = Split-Path -Parent $PSScriptRoot
Set-Location $Home_
New-Item -ItemType Directory -Force -Path "data\logs" | Out-Null
$log = "data\logs\run-$(Get-Date -Format 'yyyyMMdd-HHmm').log"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"

if ($Shard) { python pipeline\run_batch.py --shard $Shard *> $log }
else { python pipeline\run_batch.py *> $log }
python pipeline\status.py *>> $log
