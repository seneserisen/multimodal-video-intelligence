[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("START", "STOP", "RESTART", "STATUS", "OPEN_APP", "OPEN_FOLDER", "OPEN_RESULTS", "OPEN_LOGS", "BACKUP", "RESTORE", "UPDATE")]
    [string]$Action,
    [string]$BackupPath,
    [switch]$Confirm,
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    & (Join-Path $PSScriptRoot "setup.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-Mvi([string[]]$Arguments) {
    & $Python -m video_intelligence.cli @Arguments
    $script:MviExitCode = $LASTEXITCODE
}

switch ($Action) {
    "START" { Invoke-Mvi @("start", "--no-open"); exit $MviExitCode }
    "STOP" { Invoke-Mvi @("stop"); exit $MviExitCode }
    "STATUS" { Invoke-Mvi @("status"); exit $MviExitCode }
    "RESTART" {
        Invoke-Mvi @("stop")
        if ($MviExitCode -ne 0) { exit $MviExitCode }
        Invoke-Mvi @("start", "--no-open")
        exit $MviExitCode
    }
    "OPEN_APP" { Invoke-Mvi @("start"); exit $MviExitCode }
    "OPEN_FOLDER" {
        Start-Process explorer.exe -ArgumentList @($ProjectRoot)
        exit 0
    }
    "OPEN_RESULTS" {
        $dataDir = & $Python -c "from video_intelligence.command_center.data import prepare_data_dir; print(prepare_data_dir())"
        Start-Process explorer.exe -ArgumentList @($dataDir)
        exit 0
    }
    "OPEN_LOGS" {
        $logFile = & $Python -c "from video_intelligence.command_center.state import log_path, prepare_state_dir; d=prepare_state_dir(); print(log_path(d))"
        $logDirectory = Split-Path -Parent $logFile
        Start-Process explorer.exe -ArgumentList @($logDirectory)
        exit 0
    }
    "BACKUP" { Invoke-Mvi @("backup"); exit $MviExitCode }
    "RESTORE" {
        if (-not $BackupPath) {
            Write-Host "RESTORE requires -BackupPath followed by an MVI backup archive."
            exit 2
        }
        $arguments = @("restore", "--input", $BackupPath)
        if ($Confirm) { $arguments += "--confirm" }
        Invoke-Mvi $arguments
        exit $MviExitCode
    }
    "UPDATE" {
        $arguments = @("update")
        if ($Apply) { $arguments += "--apply" }
        Invoke-Mvi $arguments
        exit $MviExitCode
    }
}
