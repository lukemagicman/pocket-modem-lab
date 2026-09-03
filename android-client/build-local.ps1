$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$wrapper = Join-Path $projectRoot 'gradlew.bat'

if (-not (Test-Path -LiteralPath $wrapper)) {
    throw '缺少 Gradle Wrapper。请重新克隆仓库或检查 android-client/gradlew.bat。'
}

& $wrapper '--no-daemon' 'assembleDebug'

if ($LASTEXITCODE -ne 0) {
    throw "Gradle 构建失败，退出码 $LASTEXITCODE"
}

$apk = Join-Path $projectRoot 'app\build\outputs\apk\debug\app-debug.apk'
Get-FileHash -LiteralPath $apk -Algorithm SHA256
