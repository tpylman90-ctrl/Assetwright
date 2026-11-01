# Stops and removes the scheduled worker; leaves learning data and models intact.
$ErrorActionPreference = "Stop"
$taskName = "Assetwright Mini AI Background Training"
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $existing) {
    Write-Host "No Assetwright background task is registered."
    exit 0
}
if ($existing.State -eq "Running") {
    Stop-ScheduledTask -TaskName $taskName
}
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
Write-Host "Removed Assetwright background task. Training records were not deleted."
