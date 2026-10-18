# Reports status without starting anything.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "scripts\native-common.ps1")

$Root = Get-ProjectRoot
$postgres = if (Test-TcpPort -Port 5432) { "READY" } else { "NOT READY" }
$inference = "NOT READY"
$model = "NOT READY"
$api = "NOT READY"
$frontend = "NOT READY"

if (Test-TcpPort -Port 8001) {
    try {
        $info = Get-JsonQuiet -Url "http://127.0.0.1:8001/model-info"
        $inference = "READY"
        if ($info.active_model) { $model = [string]$info.active_model } else { $model = "NOT LOADED" }
    } catch {
        $inference = "PORT OPEN BUT NOT RESPONDING"
    }
}

if (Test-TcpPort -Port 8000) {
    try {
        $health = Get-JsonQuiet -Url "http://127.0.0.1:8000/health"
        if ($health.status -eq "ok") { $api = "READY" } else { $api = "NOT READY" }
    } catch {
        $api = "PORT OPEN BUT NOT RESPONDING"
    }
}

if (Test-TcpPort -Port 3000) {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:3000" -UseBasicParsing -TimeoutSec 8 | Out-Null
        $frontend = "READY"
    } catch {
        $frontend = "PORT OPEN BUT NOT RESPONDING"
    }
}

$missing = Get-MissingV4Files -Root $Root
$artifacts = if ($missing.Count -eq 0) { "present" } else { "MISSING" }

Write-Host ""
Write-Host "PostgreSQL ............... $postgres"
Write-Host "Inference ................ $inference"
Write-Host "Active model ............. $model"
Write-Host "Clinical API ............. $api"
Write-Host "Frontend ................. $frontend"
Write-Host "Model files .............. $artifacts"
Write-Host ""
Write-Host "Redis and the background worker are optional. The clinic demo does not need them."
Write-Host ""
if ($postgres -eq "READY" -and $inference -eq "READY" -and $model -eq "GA-RGCA-v4-Rolling-RSL" -and $api -eq "READY" -and $frontend -eq "READY") {
    Write-Host "SYSTEM READY"
    exit 0
}
Write-Host "NOT FULLY READY"
exit 1
