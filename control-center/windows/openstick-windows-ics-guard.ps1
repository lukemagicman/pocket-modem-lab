param(
    [Parameter(Mandatory = $true)]
    [string]$SessionDirectory
)

$ErrorActionPreference = 'Stop'
$publicName = 'Meta'
$privateDescriptionPattern = 'Remote NDIS based Internet Sharing Device'
$startFlag = Join-Path $SessionDirectory 'start.flag'
$keepFlag = Join-Path $SessionDirectory 'keep.flag'
$readyFile = Join-Path $SessionDirectory 'ready.json'
$statusFile = Join-Path $SessionDirectory 'status.json'

New-Item -ItemType Directory -Path $SessionDirectory -Force | Out-Null

trap {
    $message = $_.Exception.Message
    try {
        @{ status = 'fatal_error'; updated_at = (Get-Date).ToString('o'); error = $message } |
            ConvertTo-Json -Depth 5 |
            Set-Content -LiteralPath $statusFile -Encoding UTF8
        $_ | Out-String | Set-Content -LiteralPath (Join-Path $SessionDirectory 'error.log') -Encoding UTF8
    } catch {}
    exit 99
}

function Write-Status {
    param([string]$Status, [hashtable]$Details = @{})
    $payload = @{ status = $Status; updated_at = (Get-Date).ToString('o') }
    foreach ($item in $Details.GetEnumerator()) { $payload[$item.Key] = $item.Value }
    $payload | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statusFile -Encoding UTF8
}

function Get-SharingConnections {
    param($Manager)
    $items = @()
    foreach ($connection in $Manager.EnumEveryConnection()) {
        $properties = $Manager.NetConnectionProps($connection)
        $configuration = $Manager.INetSharingConfigurationForINetConnection($connection)
        $items += [pscustomobject]@{
            Connection = $connection
            Name = $properties.Name
            Device = $properties.DeviceName
            Enabled = [bool]$configuration.SharingEnabled
            Type = if ($configuration.SharingEnabled) { [int]$configuration.SharingConnectionType } else { -1 }
            Configuration = $configuration
        }
    }
    return $items
}

function Restore-RndisDhcp {
    param([string]$Name)
    & netsh interface ip set address name="$Name" source=dhcp | Out-Null
    & netsh interface ip set dns name="$Name" source=dhcp | Out-Null
}

$manager = New-Object -ComObject HNetCfg.HNetShare
$connections = Get-SharingConnections -Manager $manager
$public = $connections | Where-Object { $_.Name -eq $publicName } | Select-Object -First 1
$private = $connections | Where-Object { $_.Device -like "*$privateDescriptionPattern*" } | Select-Object -First 1

if (-not $public) { Write-Status 'error' @{ error = 'Shared uplink was not found' }; exit 2 }
if (-not $private) { Write-Status 'error' @{ error = 'OpenStick RNDIS adapter was not found' }; exit 3 }

$sharingBefore = @($connections | Where-Object Enabled | ForEach-Object {
    @{ name = $_.Name; device = $_.Device; type = $_.Type }
})
$foreignSharing = @($connections | Where-Object {
    $_.Enabled -and $_.Name -notin @($public.Name, $private.Name)
})
if ($foreignSharing.Count) {
    Write-Status 'blocked' @{ error = 'Another Internet Connection Sharing configuration is active'; sharing = $sharingBefore }
    exit 4
}

@{
    status = 'ready'
    public = $public.Name
    private = $private.Name
    previous_sharing = $sharingBefore
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $readyFile -Encoding UTF8

$triggered = $false
for ($index = 0; $index -lt 60; $index++) {
    if (Test-Path -LiteralPath $startFlag) { $triggered = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $triggered) { Write-Status 'cancelled' @{ reason = 'Start signal was not received' }; exit 0 }

try {
    if ($public.Configuration.SharingEnabled) { $public.Configuration.DisableSharing() }
    if ($private.Configuration.SharingEnabled) { $private.Configuration.DisableSharing() }
    $public.Configuration.EnableSharing(0)
    $private.Configuration.EnableSharing(1)
    Write-Status 'enabled' @{ public = $public.Name; private = $private.Name; rollback_seconds = 180 }
} catch {
    try {
        if ($public.Configuration.SharingEnabled) { $public.Configuration.DisableSharing() }
        if ($private.Configuration.SharingEnabled) { $private.Configuration.DisableSharing() }
        Restore-RndisDhcp -Name $private.Name
    } catch {}
    Write-Status 'error' @{ error = $_.Exception.Message }
    exit 5
}

for ($index = 0; $index -lt 90; $index++) {
    if (Test-Path -LiteralPath $keepFlag) {
        Write-Status 'kept' @{ public = $public.Name; private = $private.Name }
        exit 0
    }
    Start-Sleep -Seconds 2
}

try {
    if ($public.Configuration.SharingEnabled) { $public.Configuration.DisableSharing() }
    if ($private.Configuration.SharingEnabled) { $private.Configuration.DisableSharing() }
    Restore-RndisDhcp -Name $private.Name
    Write-Status 'rolled_back' @{ reason = 'Success was not confirmed within 180 seconds' }
} catch {
    Write-Status 'rollback_error' @{ error = $_.Exception.Message }
    exit 6
}
