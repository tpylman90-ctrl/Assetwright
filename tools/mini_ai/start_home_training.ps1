# Assetwright: private home training loop (no cloud, no paid services).
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $repoRoot
$inbox = Join-Path $repoRoot "local-data/mini-ai/inbox"
New-Item -ItemType Directory -Path $inbox -Force | Out-Null
Write-Host "Assetwright local learning inbox: $inbox"
Write-Host "Copy exported phone JSONL files into this folder; the watcher validates them."
Write-Host "Press Ctrl+C to stop monitoring."
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 tools/mini_ai/home_train.py --watch --poll-seconds 60
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python tools/mini_ai/home_train.py --watch --poll-seconds 60
} else {
    throw "Python 3 is required. Install Python and run this launcher again."
}
