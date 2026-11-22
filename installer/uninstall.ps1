#Requires -Version 5.1
<#
.SYNOPSIS
    星月-桌面整理 卸载程序。

.DESCRIPTION
    结束程序、删除快捷方式与卸载注册表项，并移除安装目录。
    默认保留 %APPDATA%\XingYueDesktop 中的方案和日志；使用 -PurgeData 可同时删除。

.PARAMETER InstallDir
    安装目录。默认使用脚本所在目录（由安装程序复制到安装目录）。

.PARAMETER DataDir
    用户数据目录。默认读取 install.json，否则为 %APPDATA%\XingYueDesktop。

.PARAMETER PurgeData
    同时删除用户数据（方案与日志）。

.PARAMETER Quiet
    静默卸载：不询问，默认保留用户数据。

.PARAMETER NoRegistry
    不删除卸载注册表项（测试或便携部署）。

.PARAMETER NoShortcuts
    不删除快捷方式（测试或便携部署）。
#>
[CmdletBinding()]
param(
    [string]$InstallDir = "",
    [string]$DataDir = "",
    [switch]$PurgeData,
    [switch]$Quiet,
    [switch]$NoRegistry,
    [switch]$NoShortcuts,
    [int]$WatchdogSeconds = 300
)

$ErrorActionPreference = "Stop"
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
}

$watchdog = $null
if ($WatchdogSeconds -gt 0) {
    $watchdog = Start-Job -ScriptBlock {
        param($ParentId, $Seconds)
        Start-Sleep -Seconds $Seconds
        if (Get-Process -Id $ParentId -ErrorAction SilentlyContinue) {
            Stop-Process -Id $ParentId -Force
        }
    } -ArgumentList $PID, $WatchdogSeconds
}
trap {
    $failure = $_.Exception.Message
    if ($watchdog) {
        Stop-Job $watchdog -ErrorAction SilentlyContinue
        Remove-Job $watchdog -Force -ErrorAction SilentlyContinue
    }
    throw $failure
}

$AppId = "XingYueDesktop"
$AppName = "星月-桌面整理"
$ExeName = "星月-桌面整理.exe"

if ($AppName -match '[\\/:*?"<>|]' -or [System.IO.Path]::GetFileName($ExeName) -ne $ExeName) {
    throw "安装元数据包含非法文件名。"
}

if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = $PSScriptRoot
}
$InstallDir = [System.IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($InstallDir))
if ($InstallDir -match '^[A-Za-z]:$' -or $InstallDir -eq $env:SystemRoot) {
    throw "安装目录不合法：$InstallDir"
}

$infoPath = Join-Path $InstallDir "install.json"
$shortcuts = @()
if (Test-Path -LiteralPath $infoPath) {
    try {
        $info = Get-Content -LiteralPath $infoPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($info.displayName) { $AppName = [string]$info.displayName }
        if ($info.exeName) { $ExeName = [string]$info.exeName }
        if (-not $DataDir -and $info.dataDir) { $DataDir = [string]$info.dataDir }
        if ($info.shortcuts) { $shortcuts = @($info.shortcuts) }
    } catch {
        Write-Warning "读取 install.json 失败，使用默认卸载信息。"
    }
}

if ([string]::IsNullOrWhiteSpace([string]$info.installDir)) {
    throw "install.json 缺少 installDir，拒绝删除：$InstallDir"
}
if ($AppName -match '[\\/:*?"<>|]' -or [System.IO.Path]::GetFileName($ExeName) -ne $ExeName) {
    throw "install.json 包含非法文件名，拒绝删除：$InstallDir"
}

$installItem = Get-Item -LiteralPath $InstallDir -Force
if ($installItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
    throw "安装目录是符号链接或联接点，拒绝删除：$InstallDir"
}
$installMarker = Join-Path $InstallDir ".xingyue-install"
if (-not (Test-Path -LiteralPath $infoPath)) {
    throw "未找到 install.json，拒绝删除：$InstallDir"
}
if (-not (Test-Path -LiteralPath $installMarker)) {
    throw "未找到安装标记 .xingyue-install，拒绝删除：$InstallDir"
}
if ((Get-Content -LiteralPath $installMarker -Raw -ErrorAction SilentlyContinue).Trim() -ne $AppId) {
    throw "安装标记不匹配，拒绝删除：$InstallDir"
}
$recordedInstall = [System.IO.Path]::GetFullPath(
    [Environment]::ExpandEnvironmentVariables([string]$info.installDir)
).TrimEnd('\')
if ($recordedInstall -ne $InstallDir.TrimEnd('\')) {
    throw "install.json 记录的安装目录不一致，拒绝删除：$InstallDir"
}
$blockedPaths = @(
    $env:SystemRoot,
    $env:ProgramFiles,
    ${env:ProgramFiles(x86)},
    $env:USERPROFILE,
    (Split-Path -Parent $env:USERPROFILE),
    $env:LOCALAPPDATA,
    $env:APPDATA,
    $env:TEMP
)
if ($blockedPaths -contains $InstallDir.TrimEnd('\')) {
    throw "拒绝删除系统目录或用户根目录：$InstallDir"
}

if ([string]::IsNullOrWhiteSpace($DataDir)) {
    $DataDir = Join-Path $env:APPDATA "XingYueDesktop"
}
$DataDir = [System.IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($DataDir))

if (-not $PurgeData -and -not $Quiet) {
    Write-Host "用户数据目录：$DataDir"
    $answer = Read-Host "是否同时删除用户数据（方案、日志）？[y/N]"
    if ($answer -match '^[Yy]') {
        $PurgeData = $true
    }
}

function Test-AllowedShortcut {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }
    if (-not $Path.EndsWith(".lnk", [System.StringComparison]::OrdinalIgnoreCase)) {
        return $false
    }
    $full = [System.IO.Path]::GetFullPath($Path)
    $startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    $desktop = [Environment]::GetFolderPath("Desktop")
    foreach ($dir in @($startMenu, $desktop)) {
        if ($dir -and $full.StartsWith($dir.TrimEnd('\') + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

$processName = [System.IO.Path]::GetFileNameWithoutExtension($ExeName)
Get-Process -Name $processName -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 600

if (-not $NoShortcuts) {
    $paths = @()
    if ($shortcuts.Count -gt 0) { $paths += $shortcuts }
    $paths += Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$AppName.lnk"
    $desktopDir = [Environment]::GetFolderPath("Desktop")
    if ($desktopDir) {
        $paths += Join-Path $desktopDir "$AppName.lnk"
    }
    $paths | Select-Object -Unique | Where-Object { Test-AllowedShortcut $_ } | ForEach-Object {
        Remove-Item -LiteralPath $_ -Force -ErrorAction SilentlyContinue
    }
}

if (-not $NoRegistry) {
    $regKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppId"
    if (Test-Path -Path $regKey) {
        Remove-Item -Path $regKey -Recurse -Force
    }
}

if ($PurgeData) {
    if ($DataDir -match '^[A-Za-z]:$' -or $DataDir -eq $env:SystemRoot) {
        throw "数据目录不合法，已停止删除：$DataDir"
    }
    if (Test-Path -LiteralPath $DataDir) {
        $dataItem = Get-Item -LiteralPath $DataDir -Force
        if ($dataItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw "数据目录是符号链接或联接点，已停止删除：$DataDir"
        }
        $defaultData = Join-Path $env:APPDATA "XingYueDesktop"
        $marker = Join-Path $DataDir ".xingyue-desktop"
        $marked = (Test-Path -LiteralPath $marker) -and
            ((Get-Content -LiteralPath $marker -Raw -ErrorAction SilentlyContinue).Trim() -eq $AppId)
        if (-not ($DataDir.TrimEnd('\') -eq $defaultData.TrimEnd('\') -or $marked)) {
            throw "拒绝删除未标记的数据目录：$DataDir。请手动确认后删除。"
        }
        Remove-Item -LiteralPath $DataDir -Recurse -Force
        Write-Host "已删除用户数据：$DataDir" -ForegroundColor Yellow
    }
} else {
    Write-Host "已保留用户数据：$DataDir"
}

$allowedNames = @($ExeName, "uninstall.ps1", "uninstall.cmd", "install.json", ".xingyue-install")
$entries = @(Get-ChildItem -LiteralPath $InstallDir -Force)
$unexpected = @($entries | Where-Object { $_.PSIsContainer -or $allowedNames -notcontains $_.Name })
if ($unexpected.Count -gt 0) {
    $names = ($unexpected | Select-Object -ExpandProperty Name) -join ", "
    throw "安装目录包含未登记条目，已停止删除：$names"
}
if ($watchdog) {
    Stop-Job $watchdog -ErrorAction SilentlyContinue
    Remove-Job $watchdog -Force -ErrorAction SilentlyContinue
    $watchdog = $null
}
foreach ($name in $allowedNames) {
    $candidate = Join-Path $InstallDir $name
    if (Test-Path -LiteralPath $candidate) {
        Remove-Item -LiteralPath $candidate -Force -ErrorAction Stop
    }
}
Set-Location $env:TEMP
Remove-Item -LiteralPath $InstallDir -Force -ErrorAction Stop
Write-Host ""
Write-Host "卸载完成" -ForegroundColor Green
Write-Host "  安装目录已删除：$InstallDir"
