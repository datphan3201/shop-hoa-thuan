[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ServerExe,
    [Parameter(Mandatory = $true)]
    [string]$DataDirectory,
    [int]$Port = 2515
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ServerExe -PathType Leaf)) {
    throw "Không tìm thấy ShopHoaThuanServer.exe: $ServerExe"
}
if (-not (Test-Path -LiteralPath (Join-Path $DataDirectory "data\\db.sqlite3") -PathType Leaf)) {
    throw "Database test chưa được migration: $DataDirectory"
}

$oldEnvironment = @{}
foreach ($name in @(
    "SHOP_DATA_DIR",
    "DJANGO_DEBUG",
    "DJANGO_SECRET_KEY",
    "DJANGO_ALLOWED_HOSTS",
    "SHOP_SERVER_HOST",
    "SHOP_SERVER_PORT"
)) {
    $oldEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
}

$process = $null
try {
    $env:SHOP_DATA_DIR = $DataDirectory
    $env:DJANGO_DEBUG = "false"
    $secretBytes = [byte[]]::new(64)
    $random = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $random.GetBytes($secretBytes)
    }
    finally {
        $random.Dispose()
    }
    $env:DJANGO_SECRET_KEY = [Convert]::ToBase64String($secretBytes)
    $env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost"
    $env:SHOP_SERVER_HOST = "127.0.0.1"
    $env:SHOP_SERVER_PORT = "$Port"

    $process = Start-Process -FilePath $ServerExe -PassThru
    $healthy = $false
    for ($attempt = 0; $attempt -lt 15; $attempt++) {
        Start-Sleep -Seconds 1
        try {
            $response = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/health/" -TimeoutSec 2
            $body = $response.Content | ConvertFrom-Json
            if ($response.StatusCode -eq 200 -and $body.status -eq "ok") {
                $healthy = $true
                break
            }
        }
        catch {
            if ($process.HasExited) {
                break
            }
        }
    }

    if (-not $healthy) {
        throw "Native server không đạt health check tại port $Port."
    }
    Write-Output "PASS: Native ShopHoaThuanServer.exe trả /health/ thành công."
}
finally {
    if ($null -ne $process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
        $process.WaitForExit()
    }
    foreach ($name in $oldEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $oldEnvironment[$name], "Process")
    }
}
