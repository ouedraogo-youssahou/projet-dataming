# ============================================
# Docker Test Runner - PowerShell version for Windows
# ============================================

param(
    [string]$Mode = "all",  # all, unit, integration, coverage
    [switch]$Up,
    [switch]$Logs,
    [switch]$Clean
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  eCommerce Intelligence - Test Suite" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

function Show-Usage {
    Write-Host "Usage: .\run_tests.ps1 [OPTIONS]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -Mode <type>    Test type: all, unit, integration, coverage"
    Write-Host "  -Up             Start persistent test runner container"
    Write-Host "  -Logs           Follow test runner logs"
    Write-Host "  -Clean          Remove coverage artifacts"
    Write-Host "  -Help           Show this help"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\run_tests.ps1                     # Run all tests"
    Write-Host "  .\run_tests.ps1 -Mode unit          # Unit tests only"
    Write-Host "  .\run_tests.ps1 -Mode coverage      # With coverage report"
    exit 0
}

if ($PSBoundParameters.ContainsKey('Help')) {
    Show-Usage
}

if ($Clean) {
    Write-Host "Cleaning test artifacts..." -ForegroundColor Yellow
    if (Test-Path "htmlcov") { Remove-Item -Recurse -Force htmlcov }
    if (Test-Path ".coverage") { Remove-Item -Force .coverage }
    if (Test-Path "coverage-report") { Remove-Item -Recurse -Force coverage-report }
    Write-Host "Cleaned." -ForegroundColor Green
    exit 0
}

if ($Logs) {
    Write-Host "Tailing test runner logs..." -ForegroundColor Yellow
    docker compose --profile test logs -f test-runner
    exit 0
}

# Determine test command
switch ($Mode) {
    "unit" {
        $TestCmd = "python -m pytest tests/unit -v --tb=short"
    }
    "integration" {
        $TestCmd = "python -m pytest tests/integration -v --tb=short -m integration"
    }
    "coverage" {
        $TestCmd = "python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term"
    }
    default {
        $TestCmd = "python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing --cov-fail-under=70"
    }
}

Write-Host "Test command: $TestCmd" -ForegroundColor Yellow
Write-Host ""

if ($Up) {
    # Persistent service
    Write-Host "Starting persistent test runner service..." -ForegroundColor Yellow
    docker compose --profile test up -d test-runner
    Write-Host "Test runner started." -ForegroundColor Green
    Write-Host "Use 'docker compose --profile test logs -f test-runner' to view logs." -ForegroundColor Cyan
    exit 0
} else {
    # One-off execution
    Write-Host "Starting one-off test runner container..." -ForegroundColor Yellow
    docker compose --profile test run --rm test-runner bash -c "$TestCmd"
    $ExitCode = $LASTEXITCODE

    if ($ExitCode -eq 0) {
        Write-Host "`nAll tests passed!" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "`nTests failed with exit code $ExitCode" -ForegroundColor Red
        exit $ExitCode
    }
}
