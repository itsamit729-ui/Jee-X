# Creates a Windows scheduled task that runs a batch every 5 hours (while the laptop is on).
# Run once in PowerShell from the solution-pipeline folder:
#   powershell -ExecutionPolicy Bypass -File scripts\install_schedule_windows.ps1            # all questions
#   powershell -ExecutionPolicy Bypass -File scripts\install_schedule_windows.ps1 -Shard 2/2 # friend's half
# Remove it later with:  Unregister-ScheduledTask -TaskName "JeeEdgeSolutions" -Confirm:$false
param([string]$Shard = "", [int]$EveryHours = 5)

$script = Join-Path $PSScriptRoot "run_scheduled.ps1"
$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$script`""
if ($Shard) { $arg += " -Shard $Shard" }
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg -WorkingDirectory (Split-Path -Parent $PSScriptRoot)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Hours $EveryHours)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "JeeEdgeSolutions" -Action $action -Trigger $trigger -Settings $settings `
    -Description "Jee Edge: solve and verify the next batch of questions with Claude Code" -Force | Out-Null
Write-Host "Scheduled 'JeeEdgeSolutions' every $EveryHours hours (first run in 2 minutes). Logs: data\logs\"
