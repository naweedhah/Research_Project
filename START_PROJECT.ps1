# Starts the clinic demo on this Windows computer. No Docker.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "scripts\native-common.ps1")

$Root = Get-ProjectRoot
Initialize-LaunchFolders -Root $Root
Write-LaunchLog -Root $Root -Message "START requested"

function Show-Banner {
    param([hashtable]$Ready, [string]$Model, [string]$FrontendMode, [string]$Failure)
    Write-Host ""
    Write-Host "========================================================"
    Write-Host " CHILD NUTRITION INTELLIGENCE PLATFORM"
    Write-Host "========================================================"
    Write-Host ""
    Write-Host ("PostgreSQL ............... {0}" -f $Ready.Postgres)
    Write-Host ("GA-RGCA v4 ............... {0}" -f $Ready.Model)
    Write-Host ("Clinical API ............. {0}" -f $Ready.Api)
    Write-Host ("Frontend ................. {0}" -f $Ready.Frontend)
    Write-Host ""
    if ($Failure) {
        Write-Host "FAILED"
        Write-Host $Failure
        Write-Host ""
        Write-Host "Details are in the logs folder:"
        Write-Host (Join-Path $Root "logs")
        Write-Host "========================================================"
        return
    }
    Write-Host "Model:"
    Write-Host $Model
    Write-Host ""
    Write-Host "Prediction:"
    Write-Host "Rolling 12-month nutritional risk"
    Write-Host ""
    Write-Host "Frontend mode:"
    Write-Host $FrontendMode
    Write-Host ""
    Write-Host "Frontend:"
    Write-Host "http://localhost:3000"
    Write-Host ""
    Write-Host "API:"
    Write-Host "http://127.0.0.1:8000"
    Write-Host ""
    Write-Host "Inference:"
    Write-Host "http://127.0.0.1:8001"
    Write-Host ""
    Write-Host "SYSTEM READY"
    Write-Host "========================================================"
}

$ready = @{ Postgres = "FAILED"; Model = "FAILED"; Api = "FAILED"; Frontend = "FAILED" }

if (-not (Test-LocalPostgres)) {
    $msg = "PostgreSQL is not accepting connections on 127.0.0.1 port 5432. Open Services, start postgresql-x64-16, then run this launcher again."
    Write-LaunchLog -Root $Root -Message $msg
    Show-Banner -Ready $ready -Model "GA-RGCA-v4-Rolling-RSL" -FrontendMode "" -Failure $msg
    exit 1
}
$ready.Postgres = "READY"

$missing = Get-MissingV4Files -Root $Root
if ($missing.Count -gt 0) {
    $msg = "The trained model files are missing: " + ($missing -join ", ")
    Write-LaunchLog -Root $Root -Message $msg
    Show-Banner -Ready $ready -Model "GA-RGCA-v4-Rolling-RSL" -FrontendMode "" -Failure $msg
    exit 1
}

$inferencePython = Join-Path $Root "services\inference\.venv\Scripts\python.exe"
$apiPython = Join-Path $Root "services\api\.venv\Scripts\python.exe"
if (-not (Test-Path $inferencePython) -or -not (Test-Path $apiPython)) {
    $msg = "Python environments are not ready. Run SETUP_PROJECT.ps1 once, then start again."
    Write-LaunchLog -Root $Root -Message $msg
    Show-Banner -Ready $ready -Model "GA-RGCA-v4-Rolling-RSL" -FrontendMode "" -Failure $msg
    exit 1
}

$env:C1_MODEL_VERSION = "ga_rgca_v4_rsl"
if (Test-Path Env:GA_RGCA_V4_DIR) { Remove-Item Env:GA_RGCA_V4_DIR }
$env:PYTHONUNBUFFERED = "1"

if (-not (Test-TcpPort -Port 8001)) {
    Write-LaunchLog -Root $Root -Message "Starting inference"
    Start-RecordedProcess -Root $Root -Name "inference" -FilePath $inferencePython -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001") -WorkingDirectory (Join-Path $Root "services\inference") -Environment @{ C1_MODEL_VERSION = "ga_rgca_v4_rsl"; PYTHONUNBUFFERED = "1" } | Out-Null
} else {
    Write-LaunchLog -Root $Root -Message "Inference port already open"
}

if (-not (Wait-HttpOk -Url "http://127.0.0.1:8001/health" -Seconds 180)) {
    $msg = "The prediction service did not become ready. See logs\inference.err.log."
    Write-LaunchLog -Root $Root -Message $msg
    Show-Banner -Ready $ready -Model "GA-RGCA-v4-Rolling-RSL" -FrontendMode "" -Failure $msg
    exit 1
}

try {
    $info = Get-JsonQuiet -Url "http://127.0.0.1:8001/model-info"
} catch {
    $msg = "The prediction service is up but model information could not be read."
    Write-LaunchLog -Root $Root -Message $msg
    Show-Banner -Ready $ready -Model "GA-RGCA-v4-Rolling-RSL" -FrontendMode "" -Failure $msg
    exit 1
}

if ($info.active_model -ne "GA-RGCA-v4-Rolling-RSL" -or $info.model_loaded -ne $true) {
    $msg = "The prediction service is not running GA-RGCA-v4-Rolling-RSL. See logs\inference.err.log."
    Write-LaunchLog -Root $Root -Message $msg
    Show-Banner -Ready $ready -Model "GA-RGCA-v4-Rolling-RSL" -FrontendMode "" -Failure $msg
    exit 1
}
$ready.Model = "READY"

if (-not (Test-TcpPort -Port 8000)) {
    Write-LaunchLog -Root $Root -Message "Starting API"
    Start-RecordedProcess -Root $Root -Name "api" -FilePath $apiPython -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") -WorkingDirectory (Join-Path $Root "services\api") -Environment @{ PYTHONUNBUFFERED = "1" } | Out-Null
} else {
    Write-LaunchLog -Root $Root -Message "API port already open"
}

if (-not (Wait-HttpOk -Url "http://127.0.0.1:8000/health" -Seconds 60)) {
    $msg = "The clinical API did not become ready. See logs\api.err.log."
    Write-LaunchLog -Root $Root -Message $msg
    Show-Banner -Ready $ready -Model "GA-RGCA-v4-Rolling-RSL" -FrontendMode "" -Failure $msg
    exit 1
}
$ready.Api = "READY"

$node = Get-Command node -ErrorAction SilentlyContinue
$nextCli = Join-Path $Root "apps\web\node_modules\next\dist\bin\next"
if (-not $node -or -not (Test-Path $nextCli)) {
    $msg = "The website tools are not installed. Run SETUP_PROJECT.ps1 once, then start again."
    Write-LaunchLog -Root $Root -Message $msg
    Show-Banner -Ready $ready -Model "GA-RGCA-v4-Rolling-RSL" -FrontendMode "" -Failure $msg
    exit 1
}

$frontendMode = "production"
$nextArgs = @($nextCli, "start", "--port", "3000")
if (-not (Test-Path (Join-Path $Root "apps\web\.next\BUILD_ID"))) {
    $frontendMode = "development (production build was not found)"
    $nextArgs = @($nextCli, "dev", "--port", "3000")
}

if (-not (Test-TcpPort -Port 3000)) {
    Write-LaunchLog -Root $Root -Message ("Starting frontend " + $frontendMode)
    Start-RecordedProcess -Root $Root -Name "frontend" -FilePath $node.Source -ArgumentList $nextArgs -WorkingDirectory (Join-Path $Root "apps\web") -Environment @{ NEXT_PUBLIC_API_URL = "http://localhost:8000" } | Out-Null
} else {
    Write-LaunchLog -Root $Root -Message "Frontend port already open"
    if (-not (Test-Path (Join-Path $Root ".run\frontend.pid"))) {
        $frontendMode = "already running"
    }
}

if (-not (Wait-HttpOk -Url "http://127.0.0.1:3000" -Seconds 120)) {
    $msg = "The website did not become ready. See logs\frontend.err.log."
    Write-LaunchLog -Root $Root -Message $msg
    Show-Banner -Ready $ready -Model "GA-RGCA-v4-Rolling-RSL" -FrontendMode $frontendMode -Failure $msg
    exit 1
}
$ready.Frontend = "READY"

try { Start-Process "http://localhost:3000" | Out-Null } catch { }
Write-LaunchLog -Root $Root -Message "SYSTEM READY"
Show-Banner -Ready $ready -Model "GA-RGCA-v4-Rolling-RSL" -FrontendMode $frontendMode -Failure ""
exit 0
