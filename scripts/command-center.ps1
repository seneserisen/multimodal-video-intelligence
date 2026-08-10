[CmdletBinding()]
param(
    [ValidateSet("start", "status", "stop", "update")]
    [string]$Action = "start",
    [switch]$Apply,
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

try {
    if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
        Write-Host "The project is not set up yet. Running setup now..."
        & (Join-Path $PSScriptRoot "setup.ps1")
        if ($LASTEXITCODE -ne 0) { throw "Automatic setup did not complete." }
    }

    $Arguments = @("-m", "video_intelligence.cli", $Action)
    if ($Action -eq "start" -and $NoOpen) { $Arguments += "--no-open" }
    if ($Action -eq "update" -and $Apply) { $Arguments += "--apply" }

    & $VenvPython @Arguments
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    exit 0
} catch {
    Write-Host ""
    Write-Host "COMMAND CENTER FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host "Run DOCTOR.bat, correct the reported problem, and try again."
    exit 1
}
