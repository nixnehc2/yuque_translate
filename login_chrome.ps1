param([switch]$Connect)
# 手动登录辅助；-Connect 同时启用仅限本机的调试连接。
$ErrorActionPreference = 'Stop'
$chromePath = Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'
if (-not (Test-Path -LiteralPath $chromePath)) { throw '未找到 Google Chrome，请先安装 Chrome。' }
$profilePath = Join-Path $PSScriptRoot '.browser-profile'
Write-Host '请先停止下载器。在项目专属 Chrome 窗口中手动登录语雀。'
$browserArgs = @("--user-data-dir=`"$profilePath`"", '--no-first-run')
if ($Connect) {
    $browserArgs += '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=9223'
    Write-Host '兼容模式：保持此窗口打开，运行 main.py 时加 --connect http://127.0.0.1:9223'
} else {
    Write-Host '默认模式：登录成功后关闭此专属窗口，再运行 main.py。'
}
$browserArgs += 'https://foundationml.yuque.com/foundationml/seminar'
Start-Process -FilePath $chromePath -ArgumentList $browserArgs
