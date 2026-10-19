# Non-destructive readiness check for the professor demonstration.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "scripts\native-common.ps1")

$Root = Get-ProjectRoot
$postgres = if (Test-TcpPort -Port 5432) { "READY" } else { "NOT READY" }
$inference = "NOT READY"
$model = "NOT READY"
$loaded = $false
$horizon = $null
$api = "NOT READY"
$frontend = "NOT READY"

$missing = Get-MissingV4Files -Root $Root
$artifacts = if ($missing.Count -eq 0) { "READY" } else { "MISSING: " + ($missing -join ", ") }

if (Test-TcpPort -Port 8001) {
    try {
        $info = Get-JsonQuiet -Url "http://127.0.0.1:8001/model-info"
        $inference = "READY"
        $model = [string]$info.model_version
        $loaded = [bool]$info.model_loaded -and $model -eq "GA-RGCA-v4-Rolling-RSL"
        $horizon = $info.prediction_horizon_months
        if (-not $loaded) { $inference = "NOT READY" }
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
        Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 8 | Out-Null
        $frontend = "READY"
    } catch {
        try {
            Invoke-WebRequest -Uri "http://127.0.0.1:3000" -UseBasicParsing -TimeoutSec 8 | Out-Null
            $frontend = "READY"
        } catch {
            $frontend = "PORT OPEN BUT NOT RESPONDING"
        }
    }
}

Write-Host ""
Write-Host "==============================================="
Write-Host " PROFESSOR DEMO READINESS"
Write-Host "==============================================="
Write-Host ""
Write-Host ("PostgreSQL ................ {0}" -f $postgres)
Write-Host ("GA-RGCA v4 ................ {0}" -f $(if ($loaded) { "READY" } else { $inference }))
Write-Host ("Clinical API .............. {0}" -f $api)
Write-Host ("Frontend .................. {0}" -f $frontend)
Write-Host ("Model files ............... {0}" -f $artifacts)
Write-Host ""
Write-Host "Model:"
Write-Host $(if ($model) { $model } else { "NOT LOADED" })
Write-Host ""
Write-Host "Horizon:"
if ($horizon) { Write-Host "$horizon months" } else { Write-Host "unknown" }
Write-Host ""
if ($postgres -eq "READY" -and $loaded -and $api -eq "READY" -and $frontend -eq "READY" -and $missing.Count -eq 0) {
    Write-Host "SYSTEM READY FOR DEMONSTRATION"
    Write-Host "==============================================="
    exit 0
}
Write-Host "NOT READY FOR DEMONSTRATION"
Write-Host "Run START_PROJECT.bat or START_PROJECT.ps1, then check the logs folder."
Write-Host "==============================================="
exit 1
