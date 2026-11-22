#Requires -Version 5.1
<#
.SYNOPSIS
    构建星月-桌面整理单文件 exe。

.DESCRIPTION
    运行测试（可通过 -SkipTests 跳过）、校验版本号、调用 PyInstaller 打包，
    并把产物复制到 artifacts\星月-桌面整理.exe。

.PARAMETER SkipTests
    跳过 pytest，仅执行打包。
#>
[CmdletBinding()]
param(
    [switch]$SkipTests,
    [string]$PythonExe = "",
    [int]$WatchdogSeconds = 1800
)

$ErrorActionPreference = "Stop"
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
}

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

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

$ManifestPath = Join-Path (Join-Path $Root "config") "app_manifest.json"
if (-not (Test-Path -LiteralPath $ManifestPath)) {
    throw "缺少配置文件：$ManifestPath"
}
$Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$ExeName = [string]$Manifest.exe_name
$Version = [string]$Manifest.version

function Resolve-Python {
    param([string]$Explicit)

    if (-not [string]::IsNullOrWhiteSpace($Explicit)) {
        if (-not (Test-Path -LiteralPath $Explicit -PathType Leaf)) {
            throw "指定的 Python 不存在：$Explicit"
        }
        return [System.IO.Path]::GetFullPath($Explicit)
    }

    if ($env:XINGYUE_PYTHON -and (Test-Path -LiteralPath $env:XINGYUE_PYTHON -PathType Leaf)) {
        return [System.IO.Path]::GetFullPath($env:XINGYUE_PYTHON)
    }

    $candidates = New-Object System.Collections.Generic.List[string]
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -and $cmd.Source -notmatch 'WindowsApps') {
        [void]$candidates.Add($cmd.Source)
    }
    foreach ($pattern in @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python*\python.exe"),
        "C:/Python*/python.exe",
        (Join-Path $env:ProgramFiles "Python*\python.exe")
    )) {
        Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue |
            ForEach-Object { [void]$candidates.Add($_.FullName) }
    }

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        try {
            $versionText = & $candidate --version 2>&1
            if ($LASTEXITCODE -eq 0 -and "$versionText" -match '^Python 3\.') {
                return $candidate
            }
        } catch {
        }
    }
    throw "未找到可用的 Python 3。请安装 Python 3.10+，或使用 -PythonExe 指定解释器路径。"
}

function Invoke-WithTimeout {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [int]$TimeoutSeconds,
        [string]$Label
    )
    $quoted = $Arguments | ForEach-Object { '"' + ($_ -replace '"', '\"') + '"' }
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = ($quoted -join " ")
    $startInfo.WorkingDirectory = $Root
    $startInfo.UseShellExecute = $false
    $process = [System.Diagnostics.Process]::Start($startInfo)
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        & taskkill.exe /PID $process.Id /T /F 2>$null | Out-Null
        throw "$Label 超时（$TimeoutSeconds 秒），已终止。"
    }
    if ($process.ExitCode -ne 0) {
        throw "$Label 失败，退出码 $($process.ExitCode)。"
    }
}

$python = Resolve-Python -Explicit $PythonExe

$pyVersion = & $python -c "import sys; sys.path.insert(0, 'src'); from xingyue_desktop.core import models; print(models.APP_VERSION)"
if ($LASTEXITCODE -ne 0) {
    throw "无法读取应用版本号，请检查 src\xingyue_desktop\models.py。"
}
$pyVersion = ($pyVersion | Out-String).Trim()
if ($pyVersion -ne $Version) {
    throw "版本不一致：config\app_manifest.json=$Version，models.py=$pyVersion"
}

if (-not $SkipTests) {
    Write-Host "运行测试..." -ForegroundColor Cyan
    Invoke-WithTimeout -FilePath $python -Arguments @("-m", "pytest", "-q") `
        -TimeoutSeconds 600 -Label "pytest"
}

$Artifacts = Join-Path $Root "artifacts"
$DistDir = Join-Path $Artifacts "_build"
$WorkDir = Join-Path $Root "build"
New-Item -ItemType Directory -Force -Path $Artifacts | Out-Null
if (Test-Path -LiteralPath $DistDir) {
    Remove-Item -LiteralPath $DistDir -Recurse -Force
}

Write-Host "开始打包..." -ForegroundColor Cyan
$specPath = Join-Path $PSScriptRoot "xingyue-desktop.spec"
$pyiArgs = @(
    "-m", "PyInstaller", $specPath,
    "--noconfirm", "--clean",
    "--distpath", $DistDir,
    "--workpath", $WorkDir
)
Invoke-WithTimeout -FilePath $python -Arguments $pyiArgs `
    -TimeoutSeconds 1800 -Label "PyInstaller"

$builtExe = Join-Path $DistDir "XingYueDesktop.exe"
if (-not (Test-Path -LiteralPath $builtExe)) {
    throw "未找到 PyInstaller 产物：$builtExe"
}
$targetExe = Join-Path $Artifacts $ExeName
Copy-Item -LiteralPath $builtExe -Destination $targetExe -Force
Remove-Item -LiteralPath $DistDir -Recurse -Force -ErrorAction SilentlyContinue

$sizeMb = [Math]::Round((Get-Item -LiteralPath $targetExe).Length / 1MB, 1)
Write-Host ""
Write-Host "构建完成" -ForegroundColor Green
Write-Host "  版本：$Version"
Write-Host "  产物：$targetExe"
Write-Host "  大小：$sizeMb MB"
Write-Host "  安装：installer\install.cmd"
if ($watchdog) {
    Stop-Job $watchdog -ErrorAction SilentlyContinue
    Remove-Job $watchdog -Force -ErrorAction SilentlyContinue
}
