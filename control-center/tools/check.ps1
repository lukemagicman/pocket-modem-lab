param(
    [string]$DeviceUrl = "",
    [switch]$ExpectCurrentVersion
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Version = (Get-Content -Raw -LiteralPath (Join-Path $ProjectRoot "VERSION")).Trim()

function Invoke-Python {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & py -3.14 @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python 检查失败：$($Arguments -join ' ')"
    }
}

Push-Location $ProjectRoot
try {
    Write-Host "[1/4] Python 语法"
    Invoke-Python -m py_compile backend/openstick-sms-web.py services/openstick-uplink-manager.py

    Write-Host "[2/4] 单元测试"
    Invoke-Python -m unittest discover -s tests -v

    Write-Host "[3/4] 前端结构与 JavaScript"
    Invoke-Python tools/check_frontend.py

    Write-Host "[4/4] 设备只读状态"
    if ($DeviceUrl) {
        $arguments = @("tools/check_live.py", $DeviceUrl)
        if ($ExpectCurrentVersion) {
            $arguments += @("--expected-version", $Version)
        }
        Invoke-Python @arguments
    } else {
        Write-Host "跳过：未提供 -DeviceUrl"
    }

    Write-Host "全部检查通过。"
} finally {
    Pop-Location
}
