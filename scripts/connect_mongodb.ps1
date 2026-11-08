$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not $env:MONGODB_URI) {
    throw "Set MONGODB_URI in your environment before running this script. Do not put database credentials in source files."
}
$pingOutput = & python (Join-Path $PSScriptRoot "check_mongodb.py")
$pingExitCode = $LASTEXITCODE
Write-Output $pingOutput
if ($pingExitCode -ne 0) {
    Write-Error "Atlas connection failed. Use the reported cause to check the database-user password, cluster hostname, or Atlas Network Access IP allowlist."
    exit 1
}

$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $serverProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)"
    if ($serverProcess.Name -ne "python.exe" -or $serverProcess.CommandLine -notmatch "app\.py") {
        throw "Port 8000 is occupied by a process other than this app; leaving it untouched."
    }
    Stop-Process -Id $listener.OwningProcess
    Wait-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
}

python app.py
