[CmdletBinding()]
param(
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$OutputDir = Join-Path $ProjectRoot "artifacts\demo"

try {
    if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
        Write-Host "The project is not set up yet. Running setup now..."
        & (Join-Path $PSScriptRoot "setup.ps1")
        if ($LASTEXITCODE -ne 0) { throw "Automatic setup did not complete." }
    }

    Write-Host "Running the deterministic multimodal evidence demonstration..."
    & $VenvPython -m video_intelligence.cli analyze-evidence `
        --input (Join-Path $ProjectRoot "tests\fixtures\contradiction_case.json") `
        --profile balanced `
        --output-dir $OutputDir
    if ($LASTEXITCODE -ne 0) { throw "The demonstration analysis failed." }

    & $VenvPython (Join-Path $ProjectRoot "scripts\validate_example.py") `
        (Join-Path $OutputDir "analysis.json") `
        (Join-Path $ProjectRoot "schemas\analysis-result.schema.json")
    if ($LASTEXITCODE -ne 0) { throw "The generated result did not pass schema validation." }

    @"
Multimodal Video Intelligence - deterministic demonstration

Open summary.md for the readable result.
Open analysis.json for the complete versioned evidence output.

This demo uses synthetic checked-in evidence. It makes no network or AI-provider calls.
"@ | Set-Content -LiteralPath (Join-Path $OutputDir "README.txt") -Encoding utf8

    Write-Host ""
    Write-Host "Demo completed successfully."
    Write-Host "The result identifies a contradiction across speech and screen evidence."
    Write-Host "Results: $OutputDir"
    Write-Host "Open: $(Join-Path $OutputDir 'summary.md')"
    if (-not $NoOpen -and $env:CI -ne "true") {
        Start-Process explorer.exe -ArgumentList @($OutputDir)
    }
    exit 0
} catch {
    Write-Host ""
    Write-Host "DEMO FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host "Run DOCTOR.bat, correct the reported problem, and try RUN.bat again."
    exit 1
}
