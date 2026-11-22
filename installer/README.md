# 安装与卸载

安装程序为 PowerShell 脚本，按当前用户安装，不需要管理员权限，也不会写入系统目录或 HKLM。

## 前置条件

1. Windows 10 / 11，PowerShell 5.1。
2. 先构建 exe：

```powershell
packaging\build.cmd
```

产物：`artifacts\星月-桌面整理.exe`。

## 安装

双击 `install.cmd`，或在命令行执行：

```powershell
installer\install.cmd
```

默认安装位置：

- 程序：`%LOCALAPPDATA%\Programs\XingYueDesktop\星月-桌面整理.exe`
- 开始菜单：`%APPDATA%\Microsoft\Windows\Start Menu\Programs\星月-桌面整理.lnk`
- 用户数据：`%APPDATA%\XingYueDesktop`
- 卸载项：`HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\XingYueDesktop`

安装完成后会启动程序。再次运行安装程序可覆盖升级，已有用户数据会保留。

### 可选参数

| 参数 | 说明 |
| --- | --- |
| `-SourceExe <路径>` | 指定安装源 exe |
| `-InstallDir <路径>` | 自定义安装目录 |
| `-DataDir <路径>` | 自定义用户数据目录 |
| `-DesktopShortcut` | 同时创建桌面快捷方式 |
| `-NoShortcuts` | 不创建快捷方式 |
| `-NoRegistry` | 不写入卸载注册表项 |
| `-AllowCustomInstallDir` | 允许安装到默认 Programs 目录之外（测试/便携用） |
| `-NoLaunch` | 安装后不启动程序 |
| `-Quiet` | 静默安装，不启动、不询问 |
| `-Force` | 程序正在运行时强制结束进程 |

示例：

```powershell
installer\install.cmd -DesktopShortcut
installer\install.cmd -Quiet -NoLaunch -Force
```

## 卸载

三种方式：

1. Windows 设置 → 应用 → 已安装的应用 → 星月-桌面整理 → 卸载。
2. 运行安装目录下的 `uninstall.cmd`（脚本会自动删除安装目录）。
3. 命令行：

```powershell
& "$env:LOCALAPPDATA\Programs\XingYueDesktop\uninstall.ps1"
```

默认保留 `%APPDATA%\XingYueDesktop` 中的方案与日志。若需一并删除：

```powershell
& "$env:LOCALAPPDATA\Programs\XingYueDesktop\uninstall.ps1" -PurgeData
```

静默卸载（保留数据）：`uninstall.ps1 -Quiet`。

## 隔离测试

不写注册表、不建快捷方式、不启动程序：

```powershell
installer\install.ps1 -InstallDir .\artifacts\_test-install -DataDir .\artifacts\_test-data `
  -NoShortcuts -NoRegistry -NoLaunch -Quiet -Force -AllowCustomInstallDir
.\artifacts\_test-install\uninstall.ps1 -PurgeData -Quiet -NoShortcuts -NoRegistry
```

## 说明

- 安装脚本只复制文件、创建快捷方式并写入 HKCU 卸载项，不修改系统环境变量。
- 卸载脚本在删除安装目录前会校验目录，拒绝处理磁盘根目录与系统目录。
- 所有脚本均为纯文本，可直接审阅；建议发布时对 exe 进行代码签名。
