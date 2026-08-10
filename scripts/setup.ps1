[CmdletBinding()]
param(
    [switch]$RequireExtension
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

function Find-CompatiblePython {
    $candidates = @(
        @{ Executable = "py"; Prefix = @("-3") },
        @{ Executable = "python"; Prefix = @() },
        @{ Executable = "python3"; Prefix = @() }
    )
    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.Executable -ErrorAction SilentlyContinue)) { continue }
        $prefix = $candidate.Prefix
        & $candidate.Executable @prefix -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { return $candidate }
    }
    return $null
}

try {
    $python = Find-CompatiblePython
    if ($null -eq $python) {
        throw "Python 3.12 or newer was not found. Install Python from python.org, enable 'Add Python to PATH', then run SETUP.bat again."
    }
    if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
        Write-Host "Creating the local Python environment..."
        $prefix = $python.Prefix
        & $python.Executable @prefix -m venv (Join-Path $ProjectRoot ".venv")
        if ($LASTEXITCODE -ne 0) { throw "Python could not create .venv." }
    } else {
        Write-Host "Existing .venv detected; reusing it."
    }

    Write-Host "Installing the project and test tools..."
    & $VenvPython -m pip install --disable-pip-version-check -e "${ProjectRoot}[dev]"
    if ($LASTEXITCODE -ne 0) { throw "Python package installation failed." }

    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if ($null -ne $npm) {
        $nodeMajor = & node -p "Number(process.versions.node.split('.')[0])"
        if ($LASTEXITCODE -eq 0 -and [int]$nodeMajor -ge 20) {
            Push-Location (Join-Path $ProjectRoot "extension")
            try {
                $extensionReady = $false
                $lockStream = [System.IO.File]::OpenRead((Join-Path (Get-Location) "package-lock.json"))
                try {
                    $hasher = [System.Security.Cryptography.SHA256]::Create()
                    try {
                        $lockHash = [System.BitConverter]::ToString(
                            $hasher.ComputeHash($lockStream)
                        ).Replace("-", "")
                    } finally {
                        $hasher.Dispose()
                    }
                } finally {
                    $lockStream.Dispose()
                }
                $lockMarker = "node_modules\.mvi-package-lock.sha256"
                if (
                    (Test-Path -LiteralPath $lockMarker -PathType Leaf) -and
                    ((Get-Content -Raw -LiteralPath $lockMarker).Trim() -eq $lockHash)
                ) {
                    & npm ls --depth=0 --silent *> $null
                    $extensionReady = $LASTEXITCODE -eq 0
                }
                if ($extensionReady) {
                    Write-Host "Extension dependencies already installed; reusing them."
                } else {
                    Write-Host "Node.js detected; installing the Chrome extension tools..."
                    & npm ci --no-audit --no-fund
                    if ($LASTEXITCODE -ne 0) { throw "Extension dependency installation failed." }
                    Set-Content -LiteralPath $lockMarker -Value $lockHash -Encoding ascii
                }
            } finally {
                Pop-Location
            }
        } elseif ($RequireExtension) {
            throw "Node.js 20 or newer is required for extension development. The basic demo does not require Node.js."
        } else {
            Write-Warning "Node.js 20+ was not found. The basic demo is ready; extension development is not."
        }
    } elseif ($RequireExtension) {
        throw "npm was not found. Install Node.js 20+ and run SETUP.bat -RequireExtension again."
    } else {
        Write-Warning "npm was not found. The basic demo is ready; extension development is not."
    }

    Write-Host ""
    Write-Host "Setup completed successfully."
    Write-Host "Next: double-click RUN.bat to generate the deterministic demonstration."
    exit 0
} catch {
    Write-Host ""
    Write-Host "SETUP FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host "Run DOCTOR.bat for a detailed environment report."
    exit 1
}
