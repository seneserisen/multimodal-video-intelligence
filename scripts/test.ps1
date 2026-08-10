[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

try {
    if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
        throw "The local environment is missing. Run SETUP.bat first."
    }
    Push-Location $ProjectRoot
    try {
        & $VenvPython -m pytest
        if ($LASTEXITCODE -ne 0) { throw "Python tests failed." }
        & $VenvPython -m ruff check .
        if ($LASTEXITCODE -ne 0) { throw "Python lint failed." }
        & $VenvPython -m ruff format --check .
        if ($LASTEXITCODE -ne 0) { throw "Python formatting check failed." }
        & $VenvPython -m mypy backend/src
        if ($LASTEXITCODE -ne 0) { throw "Python type checking failed." }
        & (Join-Path $PSScriptRoot "run.ps1") -NoOpen
        if ($LASTEXITCODE -ne 0) { throw "The deterministic demo verification failed." }

        if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
            throw "npm is missing. Install Node.js 20+ and run SETUP.bat -RequireExtension."
        }
        if (-not (Test-Path (Join-Path $ProjectRoot "extension\node_modules"))) {
            throw "Extension dependencies are missing. Run SETUP.bat -RequireExtension."
        }
        Push-Location (Join-Path $ProjectRoot "extension")
        try {
            & npm test
            if ($LASTEXITCODE -ne 0) { throw "Extension tests failed." }
            & npm run lint
            if ($LASTEXITCODE -ne 0) { throw "Extension lint failed." }
            & npm run build
            if ($LASTEXITCODE -ne 0) { throw "Extension build failed." }
            & npm audit
            if ($LASTEXITCODE -ne 0) { throw "Extension dependency audit failed." }
        } finally {
            Pop-Location
        }
    } finally {
        Pop-Location
    }
    Write-Host ""
    Write-Host "All project verification completed successfully."
    exit 0
} catch {
    Write-Host ""
    Write-Host "TESTS FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}
