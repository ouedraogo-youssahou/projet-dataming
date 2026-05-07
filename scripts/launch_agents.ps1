# ============================================
# Agent Cluster Launcher - PowerShell version for Windows
# ============================================

param(
    [string]$TargetsFile,
    [string]$TargetsJson
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  A2A Agent Cluster Launcher" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Run the Python script
$Env:PYTHONPATH = "$PWD\src"

$ArgsList = @()
if ($TargetsFile) { $ArgsList += "--targets-file"; $ArgsList += $TargetsFile }
if ($TargetsJson) { $ArgsList += "--targets"; $ArgsList += $TargetsJson }

python -m src.scraping.agents.main @ArgsList

if ($LASTEXITCODE -ne 0) {
    Write-Host "Agent cluster terminated with error." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Agent cluster stopped." -ForegroundColor Green
