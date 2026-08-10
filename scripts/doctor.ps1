[CmdletBinding()]
param()

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$HasError = $false

function Write-Check([string]$Name, [string]$Status, [string]$Detail) {
    $color = if ($Status -eq "OK") { "Green" } elseif ($Status -eq "WARNING") { "Yellow" } else { "Red" }
    Write-Host ("{0,-24} {1,-8} {2}" -f $Name, $Status, $Detail) -ForegroundColor $color
    if ($Status -eq "ERROR") { $script:HasError = $true }
}

Write-Host "Multimodal Video Intelligence - environment doctor"
Write-Host "Repository: $ProjectRoot"
Write-Host ""

$systemPython = Get-Command python -ErrorAction SilentlyContinue
$pythonPrefix = @()
if ($null -eq $systemPython) {
    $systemPython = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $systemPython) { $pythonPrefix = @("-3") }
}
if ($null -eq $systemPython) {
    Write-Check "Python" "ERROR" "Not found. Install Python 3.12+ and enable Add Python to PATH."
} else {
    $pythonExecutable = $systemPython.Source
    $version = (& $pythonExecutable @pythonPrefix --version 2>&1) -replace '^Python\s+', ''
    & $pythonExecutable @pythonPrefix -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" 2>$null
    Write-Check "Python" $(if ($LASTEXITCODE -eq 0) { "OK" } else { "ERROR" }) "Version $version"
}

if (Test-Path -LiteralPath $VenvPython -PathType Leaf) {
    Write-Check "Virtual environment" "OK" ".venv is available."
    $packageVersion = & $VenvPython -c "import video_intelligence; print(video_intelligence.__version__)" 2>$null
    Write-Check "Package installation" $(if ($LASTEXITCODE -eq 0) { "OK" } else { "ERROR" }) $(if ($LASTEXITCODE -eq 0) { "Version $packageVersion in .venv." } else { "Run SETUP.bat again." })
} else {
    Write-Check "Virtual environment" "ERROR" "Missing. Run SETUP.bat."
    Write-Check "Package installation" "ERROR" "Unavailable until setup completes."
}

try {
    $artifactDir = Join-Path $ProjectRoot "artifacts"
    New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
    $probe = Join-Path $artifactDir ".write-test"
    Set-Content -LiteralPath $probe -Value "ok" -Encoding ascii
    Remove-Item -LiteralPath $probe
    Write-Check "Writable artifacts" "OK" $artifactDir
} catch {
    Write-Check "Writable artifacts" "ERROR" "The artifacts directory is not writable."
}

if (Get-Command git -ErrorAction SilentlyContinue) {
    & git -C $ProjectRoot rev-parse --is-inside-work-tree 2>$null | Out-Null
    Write-Check "Git repository" $(if ($LASTEXITCODE -eq 0) { "OK" } else { "ERROR" }) $(if ($LASTEXITCODE -eq 0) { "Local clone detected." } else { "No Git checkout detected." })
    $branch = & git -C $ProjectRoot branch --show-current 2>$null
    Write-Check "Current branch" $(if ($branch) { "OK" } else { "WARNING" }) $(if ($branch) { $branch } else { "Detached or unavailable." })
    $remote = & git -C $ProjectRoot remote get-url origin 2>$null
    Write-Check "Git remote" $(if ($LASTEXITCODE -eq 0) { "OK" } else { "WARNING" }) $(if ($remote) { "origin is configured." } else { "No origin configured." })
} else {
    Write-Check "Git" "WARNING" "Not found. Basic demo works; developer synchronization does not."
}

$node = Get-Command node -ErrorAction SilentlyContinue
if ($null -ne $node) {
    $nodeVersion = & node --version
    $nodeMajor = & node -p "Number(process.versions.node.split('.')[0])"
    Write-Check "Node.js" $(if ([int]$nodeMajor -ge 20) { "OK" } else { "WARNING" }) "$nodeVersion (required only for extension development)"
} else {
    Write-Check "Node.js" "WARNING" "Not found; required only for extension development."
}
if ($null -ne $node -and (Test-Path -LiteralPath (Join-Path $ProjectRoot "extension\node_modules") -PathType Container)) {
    Push-Location (Join-Path $ProjectRoot "extension")
    try {
        & npm ls --depth=0 --silent *> $null
        Write-Check "Extension tools" $(if ($LASTEXITCODE -eq 0) { "OK" } else { "WARNING" }) $(if ($LASTEXITCODE -eq 0) { "Installed and consistent." } else { "Run SETUP.bat -RequireExtension." })
    } finally {
        Pop-Location
    }
} else {
    Write-Check "Extension tools" "WARNING" "Not installed; optional for the basic demo."
}

foreach ($binary in @("ffmpeg", "ffprobe")) {
    $found = Get-Command $binary -ErrorAction SilentlyContinue
    Write-Check $binary $(if ($null -ne $found) { "OK" } else { "WARNING" }) $(if ($null -ne $found) { $found.Source } else { "Optional for the synthetic demo; required for real media." })
}

if (Test-Path -LiteralPath $VenvPython -PathType Leaf) {
    Write-Host ""
    Write-Host "Application checks:"
    & $VenvPython -m video_intelligence.cli doctor
    if ($LASTEXITCODE -ne 0) { $HasError = $true }
}

Write-Host ""
if ($HasError) {
    Write-Host "Doctor found required problems. Follow the messages above and run DOCTOR.bat again." -ForegroundColor Red
    exit 1
}
Write-Host "Required checks passed. Warnings apply only to advanced features." -ForegroundColor Green
exit 0
