[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$AppRoot,
    [Parameter(Mandatory = $true)]
    [string]$WinSwPath,
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,
    [Parameter(Mandatory = $true)]
    [string]$PythonExe,
    [string]$DataRoot = "C:\ProgramData\Shop Hoa Thuan Test",
    [switch]$Cleanup
)

$ErrorActionPreference = "Stop"
$ServiceId = "ShopHoaThuanTestServer"
$RuleName = "Shop Hoa Thuan Test LAN 2505"
$Wrapper = Join-Path $AppRoot "$ServiceId.exe"
$Config = Join-Path $AppRoot "$ServiceId.xml"
$Server = Join-Path $AppRoot "ShopHoaThuanServer.exe"

if (-not $ServiceId.StartsWith("ShopHoaThuanTest")) {
    throw "Script chỉ được phép thao tác service test ShopHoaThuanTest*."
}
if (-not (Test-Path -LiteralPath $Server -PathType Leaf)) {
    throw "Thiếu server build: $Server"
}
if (-not (Test-Path -LiteralPath $WinSwPath -PathType Leaf)) {
    throw "Thiếu WinSW đã xác minh: $WinSwPath"
}
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "Thiếu Python Windows test: $PythonExe"
}
if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "manage.py") -PathType Leaf)) {
    throw "ProjectRoot không hợp lệ: $ProjectRoot"
}

function Remove-TestResources {
    & sc.exe stop $ServiceId 2>$null
    Start-Sleep -Seconds 1
    if (Test-Path -LiteralPath $Wrapper) {
        & $Wrapper uninstall 2>$null
    }
    Remove-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $Wrapper, $Config -Force -ErrorAction SilentlyContinue
}

function Wait-Health {
    param([int]$TimeoutSeconds = 30)

    for ($attempt = 0; $attempt -lt $TimeoutSeconds; $attempt++) {
        Start-Sleep -Seconds 1
        try {
            $response = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:2505/health/" -TimeoutSec 2
            $body = $response.Content | ConvertFrom-Json
            if ($response.StatusCode -eq 200 -and $body.status -eq "ok") {
                return
            }
        }
        catch {
            # Service can be restarting; let the bounded poll continue.
        }
    }
    throw "Service test không đạt health check trong $TimeoutSeconds giây."
}

if ($Cleanup) {
    Remove-TestResources
    Write-Output "Đã dọn service/rule test. DataRoot được giữ lại: $DataRoot"
    exit 0
}

Remove-TestResources
New-Item -ItemType Directory -Force -Path $DataRoot, (Join-Path $DataRoot "logs") | Out-Null
Copy-Item -LiteralPath $WinSwPath -Destination $Wrapper -Force

$oldEnvironment = @{}
foreach ($name in @("SHOP_DATA_DIR", "DJANGO_DEBUG", "DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS")) {
    $oldEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
}

try {
    $env:SHOP_DATA_DIR = $DataRoot
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

    # This is explicit test setup, not service startup.  It proves the service
    # can only run against a schema prepared by a separate runner.
    & $PythonExe (Join-Path $ProjectRoot "manage.py") migrate --noinput
    if ($LASTEXITCODE -ne 0) {
        throw "Không thể chuẩn bị schema test bằng migration runner."
    }
}
finally {
    foreach ($name in $oldEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $oldEnvironment[$name], "Process")
    }
}

@"
<service>
  <id>$ServiceId</id>
  <name>Shop Hoà Thuận Test Server</name>
  <description>Service integration test; only test data is used.</description>
  <executable>%BASE%\ShopHoaThuanServer.exe</executable>
  <workingdirectory>%BASE%</workingdirectory>
  <env name="SHOP_DATA_DIR" value="$DataRoot" />
  <env name="DJANGO_DEBUG" value="false" />
  <env name="SHOP_SERVER_HOST" value="0.0.0.0" />
  <env name="SHOP_SERVER_PORT" value="2505" />
  <stoptimeout>30 sec</stoptimeout>
  <onfailure action="restart" delay="10 sec" />
  <onfailure action="restart" delay="30 sec" />
  <onfailure action="none" />
  <resetfailure>1 hour</resetfailure>
  <logpath>$DataRoot\logs\service</logpath>
  <log mode="roll-by-size"><sizeThreshold>5120</sizeThreshold><keepFiles>3</keepFiles></log>
</service>
"@ | Set-Content -LiteralPath $Config -Encoding UTF8

try {
    & $Wrapper install
    New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 2505 -Profile @("Private", "Public") -RemoteAddress LocalSubnet | Out-Null
    & $Wrapper start
    Wait-Health

    $service = Get-CimInstance Win32_Service -Filter "Name='$ServiceId'"
    if ($service.ProcessId -le 0) {
        throw "Không lấy được PID service test để kiểm thử recovery."
    }
    Stop-Process -Id $service.ProcessId -Force
    Wait-Health -TimeoutSeconds 45

    & $Wrapper stop
    Start-Sleep -Seconds 2
    & $Wrapper start
    Wait-Health
    Write-Output "PASS: service, health, controlled recovery và firewall LAN trên Private/Public đã được xác minh."
}
finally {
    Remove-TestResources
    Write-Output "Đã dọn service/rule test. DataRoot được giữ lại: $DataRoot"
}
