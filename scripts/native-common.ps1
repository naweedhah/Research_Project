# Shared helpers for the native Windows launcher. Not run on its own.
$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

function Get-ProjectRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Initialize-LaunchFolders {
    param([string]$Root)
    New-Item -ItemType Directory -Force -Path (Join-Path $Root "logs") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $Root ".run") | Out-Null
}

function Write-LaunchLog {
    param([string]$Root, [string]$Message)
    $path = Join-Path $Root "logs\launcher.log"
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $path -Value $line -Encoding utf8
}

function Test-TcpPort {
    param([string]$HostName = "127.0.0.1", [int]$Port)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $wait = $client.BeginConnect($HostName, $Port, $null, $null)
        $ok = $wait.AsyncWaitHandle.WaitOne(1500, $false)
        if (-not $ok) { return $false }
        $client.EndConnect($wait) | Out-Null
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Get-ListeningPid {
    param([int]$Port)
    $matches = netstat -ano | Select-String -Pattern (":{0}\s+" -f $Port)
    foreach ($row in $matches) {
        $text = $row.ToString()
        if ($text -notmatch "LISTENING") { continue }
        $parts = @($text -split "\s+" | Where-Object { $_ -ne "" })
        if ($parts.Length -gt 0) { return [int]$parts[-1] }
    }
    return $null
}

function Get-JsonQuiet {
    param([string]$Url, [int]$TimeoutSec = 8)
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
    return $response.Content | ConvertFrom-Json
}

function Wait-HttpOk {
    param([string]$Url, [int]$Seconds)
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) { return $true }
        } catch {
            Start-Sleep -Seconds 2
            continue
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Get-V4ArtifactDir {
    param([string]$Root)
    return Join-Path $Root "ml\artifacts\ga_rgca_v4_rsl"
}

function Get-MissingV4Files {
    param([string]$Root)
    $required = @(
        "ga_rgca_v4_states.pt",
        "multimodal_preprocessor_v4.joblib",
        "binary_calibrators_v4.joblib",
        "rolling_tree_experts_v4.joblib",
        "superlearner_policy_v4.joblib",
        "metadata_v4.json"
    )
    $dir = Get-V4ArtifactDir -Root $Root
    $missing = @()
    foreach ($name in $required) {
        if (-not (Test-Path (Join-Path $dir $name))) { $missing += $name }
    }
    return $missing
}

function Test-LocalPostgres {
    $service = Get-Service -Name "postgresql-x64-16" -ErrorAction SilentlyContinue
    if ($service -and $service.Status -ne "Running") {
        try { Start-Service -Name $service.Name -ErrorAction Stop } catch { }
    }
    return (Test-TcpPort -Port 5432)
}

function Get-PythonExe {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $exe = & py -3 -c "import sys; print(sys.executable)"
        if ($LASTEXITCODE -eq 0 -and $exe) { return $exe.Trim() }
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return $python.Source }
    return $null
}

function Start-RecordedProcess {
    param(
        [string]$Root,
        [string]$Name,
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory,
        [hashtable]$Environment
    )
    $stdout = Join-Path $Root ("logs\{0}.log" -f $Name)
    $stderr = Join-Path $Root ("logs\{0}.err.log" -f $Name)
    if (Test-Path $stdout) { Remove-Item $stdout -Force -ErrorAction SilentlyContinue }
    if (Test-Path $stderr) { Remove-Item $stderr -Force -ErrorAction SilentlyContinue }
    foreach ($key in $Environment.Keys) {
        Set-Item -Path ("Env:{0}" -f $key) -Value $Environment[$key]
    }
    $proc = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -WorkingDirectory $WorkingDirectory -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
    $pidFile = Join-Path $Root (".run\{0}.pid" -f $Name)
    Set-Content -Path $pidFile -Value $proc.Id -Encoding ascii
    return $proc
}

function Stop-RecordedProcess {
    param([string]$Root, [string]$Name)
    $pidFile = Join-Path $Root (".run\{0}.pid" -f $Name)
    if (-not (Test-Path $pidFile)) {
        return "not running"
    }
    $raw = (Get-Content -Path $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    if (-not $raw -or $raw -notmatch "^\d+$") { return "stale pid removed" }
    $procId = [int]$raw
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if (-not $proc) { return "already stopped" }
    $cim = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f $procId) -ErrorAction SilentlyContinue
    $command = ""
    if ($cim) { $command = [string]$cim.CommandLine }
    $rootMatch = $Root.TrimEnd("\")
    if ($command -and ($command -notlike ("*{0}*" -f $rootMatch))) {
        return "left alone (pid did not belong to this project)"
    }
    & taskkill.exe /PID $procId /T /F | Out-Null
    return "stopped"
}
