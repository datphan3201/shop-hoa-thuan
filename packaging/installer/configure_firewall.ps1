[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Install", "Remove")]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [string]$ProgramPath,

    [int]$Port = 2505,

    [string]$RuleName = "Shop Hoa Thuan LAN 2505"
)

$ErrorActionPreference = "Stop"

if ($Action -eq "Install") {
    if (-not (Test-Path -LiteralPath $ProgramPath -PathType Leaf)) {
        throw "Không tìm thấy server executable: $ProgramPath"
    }

    Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule -ErrorAction SilentlyContinue

    New-NetFirewallRule `
        -DisplayName $RuleName `
        -Description "Shop Hoa Thuan - Private LAN only." `
        -Direction Inbound `
        -Action Allow `
        -Enabled True `
        -Profile Private `
        -Protocol TCP `
        -LocalPort $Port `
        -Program $ProgramPath |
        Out-Null
    exit 0
}

Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule -ErrorAction SilentlyContinue
exit 0
