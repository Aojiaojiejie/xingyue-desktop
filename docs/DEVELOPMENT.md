# 开发与发布

## 环境

- Windows 10 / 11 64 位
- Python 3.10+（开发使用 3.13）
- PowerShell 5.1

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pip install -e .
```

如果 `python` 指向 Microsoft Store 占位程序或存在多个解释器，构建脚本支持显式指定：

```powershell
packaging\build.cmd -PythonExe "C:\Path\To\Python\python.exe"
```

## 运行

```powershell
python main.py
python main.py --demo
python -m xingyue_desktop
xingyue-desktop
```

`--demo` 使用内存中的演示后端，不读取或写入真实桌面，适合开发界面。

## 测试

```powershell
pytest
```

测试从 `tests/conftest.py` 注入 `src/`，无需先安装包。覆盖：

- 扩展名分类、跳过规则、重名目标
- 待整理区边界与槽位避让
- 应用图标/全部图标排序、系统图标锁定
- 跨分辨率坐标缩放
- 快照存储、重命名、复制、导入导出、活动方案回退
- 服务层快照往返、文件整理与撤销

## 构建

```powershell
packaging\build.cmd
```

脚本会：

1. 校验 `config\app_manifest.json` 的版本与 `models.APP_VERSION` 一致；
2. 运行 pytest；
3. 使用 `packaging\xingyue-desktop.spec` 调用 PyInstaller；
4. 将产物复制为 `artifacts\星月-桌面整理.exe`。

单文件约 45 MB。构建目录 `build/`、`artifacts/` 均被 git 忽略。

### 图标

```powershell
python tools\make_icon.py
```

输出：

- `resources\icons\icon.png`、`icon.ico`、`icon-256.png`
- `docs\screenshots\06-app-icon.png`

### 手动打包

```powershell
python -m PyInstaller packaging\xingyue-desktop.spec --noconfirm --clean `
  --distpath artifacts\_build --workpath build
```

`XingYueDesktop.exe` 生成后重命名为 `星月-桌面整理.exe` 即可。

## 安装程序

构建后：

```powershell
installer\install.cmd
```

安装到 `%LOCALAPPDATA%\Programs\XingYueDesktop`，创建开始菜单快捷方式与 HKCU 卸载项。完整参数见 `installer/README.md`。

隔离测试（不写注册表、不建快捷方式）：

```powershell
installer\install.ps1 -InstallDir .\artifacts\_test-install -DataDir .\artifacts\_test-data `
  -NoShortcuts -NoRegistry -NoLaunch -Quiet -Force -AllowCustomInstallDir
.\artifacts\_test-install\uninstall.ps1 -PurgeData -Quiet -NoShortcuts -NoRegistry
```

执行 PowerShell 脚本时如遇执行策略限制，可在当前进程临时绕过：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## 版本发布

版本号出现在以下位置，必须同步：

1. `config\app_manifest.json` → `version`
2. `config\version_info.txt` → `filevers` / `prodvers` / `FileVersion` / `ProductVersion`
3. `pyproject.toml` → `project.version`
4. `src\xingyue_desktop\core\models.py` → `APP_VERSION`

构建脚本会检查 1 和 4 是否一致。

发布前检查：

- [ ] `pytest` 全部通过
- [ ] `packaging\build.cmd` 成功，exe 可启动
- [ ] 隔离安装/卸载测试通过
- [ ] 完整安装测试通过（可选，需临时写入开始菜单与 HKCU）
- [ ] 更新 `CHANGELOG.md`
- [ ] 确认许可证已添加
- [ ] 不提交 `artifacts/`、`build/`、`__pycache__`、本地日志

## 持续集成

`.github/workflows/ci.yml` 在 GitHub Actions 的 Windows runner 上安装依赖并运行 `pytest`。构建与安装脚本不放入 CI，避免在云端写入注册表或快捷方式。

## 代码约定

- 4 空格缩进，行宽 120。
- 业务逻辑放 `core/`，Qt 相关放 `ui/`；算法保持纯函数以便测试。
- 不在界面中新增解释性小字；说明写入源码注释或文档。
- 不引入明文密钥、令牌或账号密码；本地配置通过环境变量或用户数据目录读取。
