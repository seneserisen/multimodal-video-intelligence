[CmdletBinding(SupportsShouldProcess)]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Split-Path -Parent $PSScriptRoot)).Path
$Targets = @(
    "artifacts",
    "build",
    "extension\dist",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache"
)

try {
    foreach ($relative in $Targets) {
        $target = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $relative))
        if (-not $target.StartsWith($ProjectRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean a path outside the repository: $target"
        }
        if (Test-Path -LiteralPath $target) {
            if ($PSCmdlet.ShouldProcess($target, "Remove generated output")) {
                Remove-Item -LiteralPath $target -Recurse -Force
                Write-Host "Removed $relative"
            }
        }
    }
    foreach ($sourceRoot in @("backend", "tests", "scripts")) {
        $sourcePath = Join-Path $ProjectRoot $sourceRoot
        if (Test-Path -LiteralPath $sourcePath) {
            Get-ChildItem -LiteralPath $sourcePath -Directory -Recurse -Filter "__pycache__" | ForEach-Object {
                $resolved = $_.FullName
                if ($resolved.StartsWith($ProjectRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
                    if ($PSCmdlet.ShouldProcess($resolved, "Remove Python cache")) {
                        Remove-Item -LiteralPath $resolved -Recurse -Force
                    }
                }
            }
        }
    }
    if ($WhatIfPreference) {
        Write-Host "Dry run completed. No files were removed."
    } else {
        Write-Host "Generated outputs were cleaned. .venv and extension/node_modules were preserved."
    }
    exit 0
} catch {
    Write-Host "CLEAN FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}
