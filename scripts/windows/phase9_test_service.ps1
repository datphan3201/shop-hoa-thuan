[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$AppRoot,
    [Parameter(Mandatory = $true)]
    [string]$WinSwPath,
    [string]$DataRoot = "C:\ProgramData\Shop Hoa Thuan Test",
    [switch]$Cleanup
)

$ErrorActionPreference = "Stop"
$ServiceId = "ShopHoaThuanTestServer"
$RuleName = "Shop Hoa Thuan Test LAN 2505"
$Wrapper = Join-Path $AppRoot "$ServiceId.exe"
$Config = Join-Path $AppRoot "$ServiceId.xml"

if (-not $ServiceId.StartsWith("ShopHoaThuanTest")) {
    throw "Script chỉ được phép thao tác service test ShopHoaThuanTest*."
}

if ($Cleanup) {
    & sc.exe stop $ServiceId 2>$null
    Start-Sleep -Seconds 1
    if (Test-Path $Wrapper) { & $Wrapper uninstall 2>$null }
    Remove-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $Wrapper, $Config -Force -ErrorAction SilentlyContinue
    Write-Host "Đã dọn service/rule test. DataRoot được giữ lại: $DataRoot"
    exit 0
}

$Server = Join-Path $AppRoot "ShopHoaThuanServer.exe"
if (-not (Test-Path $Server)) { throw "Thiếu server build: $Server" }
if (-not (Test-Path $WinSwPath)) { throw "Thiếu WinSW đã xác minh: $WinSwPath" }

New-Item -ItemType Directory -Force -Path $DataRoot, (Join-Path $DataRoot "logs") | Out-Null
Copy-Item -LiteralPath $WinSwPath -Destination $Wrapper -Force

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

& $Wrapper install
New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 2505 -Profile Private | Out-Null
& $Wrapper start
Write-Host "Đã cài service test. Xác minh health: http://127.0.0.1:2505/health/"
