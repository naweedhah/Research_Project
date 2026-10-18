# Stops only the processes started by START_PROJECT.ps1.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "scripts\native-common.ps1")

$Root = Get-ProjectRoot
Initialize-LaunchFolders -Root $Root
Write-LaunchLog -Root $Root -Message "STOP requested"

foreach ($name in @("frontend", "api", "inference")) {
    $result = Stop-RecordedProcess -Root $Root -Name $name
    Write-Host ("{0}: {1}" -f $name, $result)
    Write-LaunchLog -Root $Root -Message ("{0}: {1}" -f $name, $result)
}

Write-Host ""
Write-Host "Project processes started by the launcher have been stopped."
Write-Host "PostgreSQL was left running."
exit 0
