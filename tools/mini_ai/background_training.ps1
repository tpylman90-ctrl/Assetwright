# Entrypoint used by the scheduled task; does not expose a network port.
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$data = Join-Path $repoRoot "local-data/mini-ai"
$inbox = Join-Path $data "inbox"
New-Item -ItemType Directory -Force -Path $inbox | Out-Null
$log = Join-Path $data "background-worker.log"
Set-Location $repoRoot
"[$((Get-Date).ToUniversalTime().ToString('o'))] Assetwright background worker starting" | Out-File -FilePath $log -Append -Encoding utf8
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 tools/mini_ai/home_train.py --watch --poll-seconds 120 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python tools/mini_ai/home_train.py --watch --poll-seconds 120 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
} else {
    "Python 3 not found on PATH" | Out-File -FilePath $log -Append -Encoding utf8
    throw "Python 3 is required to start background training."
}
if ($LASTEXITCODE -ne 0) {
    throw "Assetwright background worker exited with code $LASTEXITCODE. Read $log."
}
