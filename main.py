"""源码启动入口：python main.py。

真正的命令行逻辑位于 src/xingyue_desktop/cli.py，保持薄启动器可减少
PyInstaller 与 IDE 的路径差异。
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from xingyue_desktop.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
