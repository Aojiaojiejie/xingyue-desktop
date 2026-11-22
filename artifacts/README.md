# 构建产物

此目录用于存放本地构建输出，已被 `.gitignore` 忽略（仅保留本说明）。

- `星月-桌面整理.exe`：由 `packaging\build.cmd` 生成的单文件程序。
- `ui-shots/`、`_install-test/`：开发或安装测试产生的临时目录，不应提交。

发布时请通过 `packaging\build.cmd` 重新构建，不要把本地 exe 直接提交到仓库。
