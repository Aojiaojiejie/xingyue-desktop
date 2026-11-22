# 第三方组件声明

本项目源码以 [MIT 许可证](LICENSE) 发布。构建出的发行版本（`artifacts/` 中的 exe）内含下列第三方组件，其许可证条款对相应组件同时适用。

## PySide6 / Qt for Python

| 项 | 内容 |
| --- | --- |
| 组件 | PySide6、Shiboken6、Qt 6 运行库 |
| 许可证 | LGPL-3.0（部分模块为 GPL-3.0 或商业许可） |
| 版权 | The Qt Company Ltd. |
| 来源 | <https://www.qt.io/qt-for-python> |

本项目以动态链接方式使用 Qt 库，未修改 Qt 源码。依据 LGPL-3.0 第 4 条，使用者有权替换发行版中的 Qt 库，可通过以下任一方式实现：

- 用 `packaging\build.cmd` 配合 PyInstaller 的 `--onedir` 模式重新构建，替换 `_internal` 目录下的 Qt DLL；
- 安装同版本 PySide6 后直接以源码方式运行本项目；
- 修改本项目源码并重新打包——完整源码即在本仓库中。

## Python 运行时

| 项 | 内容 |
| --- | --- |
| 组件 | CPython 解释器与标准库 |
| 许可证 | PSF License Agreement |
| 版权 | Python Software Foundation |
| 来源 | <https://www.python.org> |

## 构建期依赖（不进入发行版）

| 组件 | 许可证 | 用途 |
| --- | --- | --- |
| Pillow | MIT-CMU | 生成图标资源 |
| PyInstaller | GPL-2.0 with exception | 打包为单文件 exe；其例外条款允许打包后的产物按原许可证分发 |
| pytest | MIT | 单元测试 |

## 图标

`resources/icons/` 下的图标由 `tools/make_icon.py` 以程序方式生成，不含第三方素材。
