$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$blender = $env:ASSETWRIGHT_BLENDER

if (-not $blender) {
    $command = Get-Command blender.exe -ErrorAction SilentlyContinue
    if ($command) {
        $blender = $command.Source
    }
}

if (-not $blender) {
    $roots = @($env:ProgramFiles, ${env:ProgramFiles(x86)})
    $matches = foreach ($root in $roots) {
        if ($root) {
            Get-ChildItem (Join-Path $root "Blender Foundation") -Filter blender.exe -Recurse -ErrorAction SilentlyContinue
        }
    }
    $candidate = $matches | Sort-Object FullName | Select-Object -Last 1
    if ($candidate) {
        $blender = $candidate.FullName
    }
}

if (-not $blender -or -not (Test-Path $blender)) {
    throw "Blender was not found. Install Blender, add blender.exe to PATH, or set ASSETWRIGHT_BLENDER."
}

$env:ASSETWRIGHT_BLENDER = $blender
$venv = Join-Path $repoRoot ".venv-assetwright"
$python = Join-Path $venv "Scripts/python.exe"

if (-not (Test-Path $python)) {
    py -3 -m venv $venv
}

& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $PSScriptRoot "requirements-local.txt")

Write-Host "Using Blender: $blender"
Write-Host "Starting Assetwright MCP on http://127.0.0.1:8765/mcp"
Write-Host "Keep this terminal open while ChatGPT uses the private MCP tunnel."
& $python (Join-Path $PSScriptRoot "local_mcp_server.py") --host 127.0.0.1 --port 8765
