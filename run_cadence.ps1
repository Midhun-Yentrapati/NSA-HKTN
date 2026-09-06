# Launch the Cadence agent network.
#
# Everything Cadence needs lives in My-Project. The neuro-san-studio checkout is
# used only as the installed framework - this script never writes to it.
#
#   neuro-san server : http://localhost:8080
#   nsflow UI        : http://localhost:4173

$ErrorActionPreference = "Stop"

$Root    = Split-Path -Parent $MyInvocation.MyCommand.Path
$NsaRoot = Split-Path -Parent $Root
$Studio  = Join-Path $NsaRoot "neuro-san-studio"
$Python  = Join-Path $NsaRoot ".virenv\Scripts\python.exe"

# Load secrets from My-Project\.env (gitignored).
$EnvFile = Join-Path $Root ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim(), "Process")
        }
    }
    Write-Host "Loaded .env" -ForegroundColor DarkGray
} else {
    Write-Warning "No .env found at $EnvFile - the network will have no API key."
}

# Point neuro-san at this project's registries and coded tools.
# The tool package is named cadence_tools, not coded_tools, so it cannot collide
# with the studio's own coded_tools package on the import path.
$env:AGENT_MANIFEST_FILE = Join-Path $Root "registries\manifest.hocon"
$env:AGENT_TOOL_PATH     = Join-Path $Root "cadence_tools"

# neuro-san resolves the tool path to a module prefix, so this project's root
# must be importable.
$env:PYTHONPATH = $Root

Write-Host ""
Write-Host "Cadence" -ForegroundColor Cyan
Write-Host "  manifest  : $env:AGENT_MANIFEST_FILE"
Write-Host "  tool path : $env:AGENT_TOOL_PATH"
Write-Host "  studio    : $Studio (framework only - never written to)"
Write-Host ""
Write-Host "  nsflow UI : http://localhost:4174" -ForegroundColor Green
Write-Host ""

# Run from this project, not the studio checkout. neuro-san takes its root
# directory from the working directory, so this keeps logs, thinking traces and
# .env loading inside My-Project and leaves the studio clone completely untouched.
Set-Location $Root
& $Python -m neuro_san_studio run --server-http-port 8081 --nsflow-port 4174
