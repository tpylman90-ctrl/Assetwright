# Installs Assetwright local training watcher for the current Windows user.
# No network service, administrator privileges or public model uploads.
# Runs while this user is signed in and the PC is awake. Uninstall separately.
[CmdletBinding()]
param([switch]$StartNow)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$launcher = Join-Path $PSScriptRoot "background_training.ps1"
if (!(Test-Path $launcher)) { throw "Missing background_training.ps1" }
$taskName = "Assetwright Mini AI Background Training"
$actionArgs = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $launcher + '"'
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2) -StartWhenAvailable
$description = "Watches approved local Assetwright feedback, catalogs licensed GLB candidates and validates new model packs. Data stays local."
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description $description -Force | Out-Null
Write-Host "Installed scheduled task: $taskName"
Write-Host "Runs at sign-in while Windows is awake (not an always-on cloud service)."
Write-Host "Training logs: $root\local-data\mini-ai\background-worker.log"
Write-Host "Training reports: $root\local-data\mini-ai\trained\latest_report.json"
if ($StartNow) {
    Start-ScheduledTask -TaskName $taskName
    Write-Host "Start requested. Check Task Scheduler and the background log for errors."
}
Write-Host "To remove: powershell -ExecutionPolicy Bypass -File tools/mini_ai/uninstall_background_training.ps1"
