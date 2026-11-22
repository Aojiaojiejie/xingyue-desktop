# 贡献指南

## 开发环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pip install -e .
pytest
```

## 提交前

- 运行 `pytest`，确保全部通过。
- 修改界面后运行一次 `python main.py --demo`，确认布局在 1360×880 与 1000×700 下正常。
- 修改打包或安装脚本后，按 `docs/DEVELOPMENT.md` 做隔离安装测试。
- 不要提交 `artifacts/`、`build/`、`__pycache__`、`.pytest_cache/`、日志或本地数据。

## 代码风格

- Python 4 空格缩进，行宽 120。
- `core/` 不依赖 Qt；`ui/` 不直接操作文件系统或 Win32。
- 新增整理规则时优先写成纯函数并补充单元测试。
- 界面文案保持简洁：只保留控件名称、状态数据与错误信息；功能解释放入文档或注释。

## 安全

- 禁止提交密钥、令牌、账号密码、证书私钥或包含个人路径的配置。
- 文件操作必须可撤销；新增删除类操作需要明确确认。
- 安装/卸载脚本修改系统状态前必须校验目标路径，拒绝磁盘根目录与系统目录。

## 许可证

仓库尚未确定开源许可证。在许可证明确前，请勿假定可以再分发或用于商业项目。
