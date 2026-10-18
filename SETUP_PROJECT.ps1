# First-time setup for this Windows computer. Safe to run again.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "scripts\native-common.ps1")

$Root = Get-ProjectRoot
Initialize-LaunchFolders -Root $Root
Write-LaunchLog -Root $Root -Message "SETUP requested"
Set-Location $Root

function Fail-Setup {
    param([string]$Message)
    Write-Host ""
    Write-Host "SETUP FAILED"
    Write-Host $Message
    Write-LaunchLog -Root $Root -Message $Message
    exit 1
}

Write-Host "Checking Python, Node.js, and PostgreSQL..."

$python = Get-PythonExe
if (-not $python) { Fail-Setup "Python 3.12 was not found. Install Python from https://www.python.org/downloads/ and tick Add python.exe to PATH. Then run this script again." }
$pyVersion = & $python -c "import sys; print(sys.version.split()[0])"
Write-Host ("Python {0}" -f $pyVersion)

$node = Get-Command node -ErrorAction SilentlyContinue
$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $node -or -not $npm) { Fail-Setup "Node.js was not found. Install the current LTS from https://nodejs.org/ and run this script again." }
Write-Host ("Node {0}" -f (& node --version))
Write-Host ("npm {0}" -f (& npm --version))

if (-not (Test-LocalPostgres)) {
    Fail-Setup "PostgreSQL is not running on port 5432. Install PostgreSQL 16, create database cnip for user cnip, remember the password, then run this script again."
}
Write-Host "PostgreSQL port 5432 is open."

$envFile = Join-Path $Root ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $Root ".env.example") $envFile
    Fail-Setup "A new .env file was created. Open it, set the PostgreSQL password for user cnip, save it, and run this script again."
}

$apiVenv = Join-Path $Root "services\api\.venv\Scripts\python.exe"
if (-not (Test-Path $apiVenv)) {
    Write-Host "Creating the API Python environment..."
    & $python -m venv (Join-Path $Root "services\api\.venv")
    if ($LASTEXITCODE -ne 0) { Fail-Setup "Could not create the API Python environment." }
}
Write-Host "Installing API packages..."
& $apiVenv -m pip install --upgrade pip
& $apiVenv -m pip install -r (Join-Path $Root "services\api\requirements.txt")
if ($LASTEXITCODE -ne 0) { Fail-Setup "API package installation failed." }

$inferenceVenv = Join-Path $Root "services\inference\.venv\Scripts\python.exe"
if (-not (Test-Path $inferenceVenv)) {
    Write-Host "Creating the prediction Python environment..."
    & $python -m venv (Join-Path $Root "services\inference\.venv")
    if ($LASTEXITCODE -ne 0) { Fail-Setup "Could not create the prediction Python environment." }
}
Write-Host "Installing prediction packages. This can take several minutes the first time."
& $inferenceVenv -m pip install --upgrade pip
& $inferenceVenv -m pip install -r (Join-Path $Root "services\inference\requirements.txt")
if ($LASTEXITCODE -ne 0) { Fail-Setup "Prediction package installation failed." }

if (-not (Test-Path (Join-Path $Root "apps\web\node_modules"))) {
    Write-Host "Installing website packages..."
    Push-Location (Join-Path $Root "apps\web")
    & npm install
    $npmCode = $LASTEXITCODE
    Pop-Location
    if ($npmCode -ne 0) { Fail-Setup "Website package installation failed." }
} else {
    Write-Host "Website packages are already installed."
}

$missing = Get-MissingV4Files -Root $Root
if ($missing.Count -gt 0) { Fail-Setup ("Trained model files are missing: " + ($missing -join ", ")) }
Write-Host "GA-RGCA v4 model files are present."

Write-Host "Updating the database schema without deleting data..."
Push-Location (Join-Path $Root "services\api")
& $apiVenv -m alembic upgrade head
$alembicCode = $LASTEXITCODE
if ($alembicCode -ne 0) {
    Pop-Location
    Fail-Setup "Database update failed. Check that database cnip and user cnip in .env can connect."
}

$userCountText = & $apiVenv -c "from sqlalchemy import create_engine, text; from app.core.config import get_settings; e=create_engine(get_settings().database_url); c=e.connect(); print(c.execute(text('select count(*) from users')).scalar())"
$userCode = $LASTEXITCODE
if ($userCode -ne 0) {
    Pop-Location
    Fail-Setup "Could not read the users table."
}
$userCount = [int](($userCountText | Select-Object -Last 1).ToString().Trim())
if ($userCount -eq 0) {
    Write-Host "No users found. Creating the one-time demonstration accounts..."
    & $apiVenv -m app.seed
    $seedCode = $LASTEXITCODE
    Pop-Location
    if ($seedCode -ne 0) { Fail-Setup "One-time demonstration setup failed." }
} else {
    Pop-Location
    Write-Host "Existing users were kept. The database was not seeded again."
}

if (-not (Test-Path (Join-Path $Root "apps\web\.next\BUILD_ID"))) {
    Write-Host "Building the website for the demo. This can take a few minutes."
    Push-Location (Join-Path $Root "apps\web")
    & npm run build
    $buildCode = $LASTEXITCODE
    Pop-Location
    if ($buildCode -ne 0) { Fail-Setup "Website build failed." }
} else {
    Write-Host "A website build is already present."
}

Write-Host ""
Write-Host "SETUP SUCCEEDED"
Write-Host "Next time, run START_PROJECT.ps1"
Write-LaunchLog -Root $Root -Message "SETUP SUCCEEDED"
exit 0
