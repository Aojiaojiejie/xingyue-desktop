#Requires -Version 5.1
<#
.SYNOPSIS
    星月-桌面整理 安装程序（当前用户，无需管理员权限）。

.DESCRIPTION
    将构建产物安装到 %LOCALAPPDATA%\Programs\XingYueDesktop，创建开始菜单快捷方式，
    写入“应用和功能”卸载项，并把卸载程序复制到安装目录。

.PARAMETER SourceExe
    安装源 exe。默认 artifacts\星月-桌面整理.exe。

.PARAMETER InstallDir
    安装目录。默认 %LOCALAPPDATA%\Programs\XingYueDesktop。

.PARAMETER DataDir
    用户数据目录。默认 %APPDATA%\XingYueDesktop。

.PARAMETER DesktopShortcut
    同时创建桌面快捷方式。

.PARAMETER NoShortcuts
    不创建快捷方式（用于测试或便携部署）。

.PARAMETER NoRegistry
    不写入卸载注册表项（用于测试或便携部署）。

.PARAMETER NoLaunch
    安装完成后不启动程序。

.PARAMETER Quiet
    静默模式：不启动程序、不询问；程序正在运行时失败。

.PARAMETER Force
    程序正在运行时强制结束进程。
#>
[CmdletBinding()]
param(
    [string]$SourceExe = "",
    [string]$InstallDir = "",
    [string]$DataDir = "",
    [switch]$DesktopShortcut,
    [switch]$NoShortcuts,
    [switch]$NoRegistry,
    [switch]$NoLaunch,
    [switch]$Quiet,
    [switch]$Force,
    [switch]$AllowCustomInstallDir,
    [int]$WatchdogSeconds = 600
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

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ManifestPath = Join-Path (Join-Path $RepoRoot "config") "app_manifest.json"

$AppId = "XingYueDesktop"
$AppName = "星月-桌面整理"
$Version = "1.0.0"
$Publisher = "XingYue"
$ExeName = "星月-桌面整理.exe"

if (Test-Path -LiteralPath $ManifestPath) {
    try {
        $manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($manifest.app_id) { $AppId = [string]$manifest.app_id }
        if ($manifest.display_name) { $AppName = [string]$manifest.display_name }
        if ($manifest.version) { $Version = [string]$manifest.version }
        if ($manifest.publisher) { $Publisher = [string]$manifest.publisher }
        if ($manifest.exe_name) { $ExeName = [string]$manifest.exe_name }
    } catch {
        Write-Warning "读取 config\app_manifest.json 失败，使用内置元数据。"
    }
}

if ($AppName -match '[\\/:*?"<>|]' -or [System.IO.Path]::GetFileName($ExeName) -ne $ExeName) {
    throw "安装元数据包含非法文件名。"
}

if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Join-Path $env:LOCALAPPDATA "Programs\XingYueDesktop"
}
if ([string]::IsNullOrWhiteSpace($DataDir)) {
    $DataDir = Join-Path $env:APPDATA "XingYueDesktop"
}
$InstallDir = [System.IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($InstallDir))
$DataDir = [System.IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($DataDir))
if ($InstallDir -match '^[A-Za-z]:$' -or $InstallDir -eq $env:SystemRoot) {
    throw "安装目录不合法：$InstallDir"
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
    throw "拒绝安装到系统目录或用户根目录：$InstallDir"
}
if ($AllowCustomInstallDir) {
    $segments = ($InstallDir.TrimEnd('\') -split '\\').Count
    if ($segments -lt 3) {
        throw "自定义安装目录层级过浅，已拒绝：$InstallDir"
    }
}
if (-not $AllowCustomInstallDir) {
    $programsRoot = Join-Path $env:LOCALAPPDATA "Programs"
    $prefix = $programsRoot.TrimEnd('\') + '\'
    if (-not $InstallDir.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "默认只允许安装到 $programsRoot 下；自定义目录请追加 -AllowCustomInstallDir。"
    }
}

if ([string]::IsNullOrWhiteSpace($SourceExe)) {
    $SourceExe = Join-Path (Join-Path $RepoRoot "artifacts") $ExeName
}
if (-not (Test-Path -LiteralPath $SourceExe -PathType Leaf)) {
    $fallback = Join-Path (Join-Path $RepoRoot "artifacts") "XingYueDesktop.exe"
    if (Test-Path -LiteralPath $fallback -PathType Leaf) {
        $SourceExe = $fallback
    } else {
        throw "未找到安装源：$SourceExe`n请先运行 packaging\build.ps1 生成构建产物。"
    }
}
$SourceExe = [System.IO.Path]::GetFullPath($SourceExe)

$processName = [System.IO.Path]::GetFileNameWithoutExtension($ExeName)
$running = @(Get-Process -Name $processName -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) {
    if ($Force) {
        $running | Stop-Process -Force
        Start-Sleep -Milliseconds 600
    } elseif ($Quiet) {
        throw "$AppName 正在运行，无法静默安装。请退出程序或使用 -Force。"
    } else {
        $answer = Read-Host "检测到 $AppName 正在运行，是否结束进程并继续？[y/N]"
        if ($answer -match '^[Yy]') {
            $running | Stop-Process -Force
            Start-Sleep -Milliseconds 600
        } else {
            throw "安装已取消。"
        }
    }
}

if (Test-Path -LiteralPath $InstallDir) {
    $installItem = Get-Item -LiteralPath $InstallDir -Force
    if ($installItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw "安装目录不能是符号链接或联接点：$InstallDir"
    }
    $existing = @(Get-ChildItem -LiteralPath $InstallDir -Force)
    if ($existing.Count -gt 0 -and
        -not (Test-Path -LiteralPath (Join-Path $InstallDir ".xingyue-install"))) {
        throw "安装目录非空且不是本程序的安装目录：$InstallDir"
    }
}
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Set-Content -LiteralPath (Join-Path $InstallDir ".xingyue-install") -Value $AppId -Encoding ASCII
if (Test-Path -LiteralPath $DataDir) {
    $dataItem = Get-Item -LiteralPath $DataDir -Force
    if ($dataItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw "数据目录不能是符号链接或联接点：$DataDir"
    }
}
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
$dataMarker = Join-Path $DataDir ".xingyue-desktop"
if (-not (Test-Path -LiteralPath $dataMarker)) {
    Set-Content -LiteralPath $dataMarker -Value $AppId -Encoding ASCII
}
$targetExe = Join-Path $InstallDir $ExeName
Copy-Item -LiteralPath $SourceExe -Destination $targetExe -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "uninstall.ps1") -Destination (Join-Path $InstallDir "uninstall.ps1") -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "uninstall.cmd") -Destination (Join-Path $InstallDir "uninstall.cmd") -Force

$shortcuts = New-Object System.Collections.Generic.List[string]
if (-not $NoShortcuts) {
    $shell = New-Object -ComObject WScript.Shell
    $startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    New-Item -ItemType Directory -Force -Path $startMenuDir | Out-Null
    $startMenuLnk = Join-Path $startMenuDir "$AppName.lnk"
    $shortcut = $shell.CreateShortcut($startMenuLnk)
    $shortcut.TargetPath = $targetExe
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.IconLocation = "$targetExe,0"
    $shortcut.Description = $AppName
    $shortcut.Save()
    [void]$shortcuts.Add($startMenuLnk)

    if ($DesktopShortcut) {
        $desktopDir = [Environment]::GetFolderPath("Desktop")
        if ($desktopDir) {
            $desktopLnk = Join-Path $desktopDir "$AppName.lnk"
            $shortcut = $shell.CreateShortcut($desktopLnk)
            $shortcut.TargetPath = $targetExe
            $shortcut.WorkingDirectory = $InstallDir
            $shortcut.IconLocation = "$targetExe,0"
            $shortcut.Description = $AppName
            $shortcut.Save()
            [void]$shortcuts.Add($desktopLnk)
        }
    }
}

if (-not $NoRegistry) {
    $uninstallScript = Join-Path $InstallDir "uninstall.ps1"
    $uninstallString = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $uninstallScript
    $regKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppId"
    if (-not (Test-Path -Path $regKey)) {
        New-Item -Path $regKey -Force | Out-Null
    }
    New-ItemProperty -Path $regKey -Name "DisplayName" -Value $AppName -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regKey -Name "DisplayVersion" -Value $Version -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regKey -Name "Publisher" -Value $Publisher -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regKey -Name "InstallLocation" -Value $InstallDir -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regKey -Name "DisplayIcon" -Value $targetExe -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regKey -Name "UninstallString" -Value $uninstallString -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regKey -Name "QuietUninstallString" -Value ($uninstallString + " -Quiet") -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regKey -Name "InstallDate" -Value (Get-Date -Format "yyyyMMdd") -PropertyType String -Force | Out-Null
    $sizeKb = [int][Math]::Ceiling((Get-Item -LiteralPath $targetExe).Length / 1KB)
    New-ItemProperty -Path $regKey -Name "EstimatedSize" -Value $sizeKb -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $regKey -Name "NoModify" -Value 1 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $regKey -Name "NoRepair" -Value 1 -PropertyType DWord -Force | Out-Null
}

$installInfo = [ordered]@{
    appId = $AppId
    displayName = $AppName
    version = $Version
    publisher = $Publisher
    installDir = $InstallDir
    exeName = $ExeName
    dataDir = $DataDir
    shortcuts = $shortcuts.ToArray()
    installedAt = (Get-Date).ToString("s")
}
$installInfo | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $InstallDir "install.json") -Encoding UTF8

Write-Host ""
Write-Host "安装完成" -ForegroundColor Green
Write-Host "  程序：$targetExe"
Write-Host "  数据：$DataDir"
if (-not $NoRegistry) {
    Write-Host "  卸载：Windows 设置 → 应用 → 已安装的应用，或运行：$InstallDir\uninstall.cmd"
}
if ($watchdog) {
    Stop-Job $watchdog -ErrorAction SilentlyContinue
    Remove-Job $watchdog -Force -ErrorAction SilentlyContinue
}
if (-not $NoLaunch -and -not $Quiet) {
    Start-Process -FilePath $targetExe
}
