"""星月-桌面整理：应用包。

源码运行时资源位于仓库根目录的 resources/；PyInstaller 单文件运行时
由 --add-data 解包到 _MEIPASS/resources。
"""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    """返回 resources/ 下资源的绝对路径，兼容源码与打包运行。"""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base.joinpath(*parts)


__all__ = ["resource_path"]
