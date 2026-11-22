"""星月-桌面整理：程序入口。

用法：
    python main.py               启动图形界面
    python main.py --demo        演示模式（不读写真实桌面）
    python main.py --screenshot out.png --demo
"""

from __future__ import annotations

import argparse
import ctypes
import os
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path


def set_dpi_awareness() -> None:
    """必须在 QApplication 之前调用，保证坐标与资源管理器一致（物理像素）。"""
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)  # PER_MONITOR_AWARE_V2
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("XingYue.DesktopOrganizer")
    except Exception:
        pass


def seed_demo(service) -> None:
    if service.snapshots:
        return
    state = service.refresh_state()
    original = [(item.index, item.x, item.y) for item in state.items]
    first = service.create_snapshot("工作布局")
    if not first:
        return

    moves = []
    index = 0
    for item in state.items:
        if item.system:
            continue
        col, row = index // 6, index % 6
        moves.append((item.index, 30 + col * 108, 16 + row * 116))
        index += 1
        if index >= 26:
            break
    service.backend.set_positions(moves)
    service.create_snapshot("专注模式")
    service.backend.set_positions(original)

    # 让「工作布局」缺少两个图标，用于展示待整理提示
    snapshot = service.store.get_snapshot(first.id)
    if snapshot:
        drop_names = {"图标设计.ico", "字体合集.ttf"}
        dropped = [item for item in snapshot.items if item.name in drop_names]
        snapshot.items = [item for item in snapshot.items if item.name not in drop_names]
        service.store.save_snapshot(snapshot, make_active=True)
        zone_left = state.canvas_w - service.settings.tidy_zone_width
        for offset, item in enumerate(dropped):
            target = next((i for i in state.items if i.name == item.name), None)
            if target:
                service.backend.set_positions([(target.index, zone_left - 80, 520 + offset * 112)])

    if service.store.get_snapshot(first.id):
        service.store.duplicate_snapshot(first.id, "极简桌面")
    service.store.set_active(first.id)
    service.log("info", "演示数据已准备：3 套方案、2 个待整理图标")


def _crash(exc: BaseException) -> None:
    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    try:
        base = Path(os.environ.get("APPDATA") or Path.home()) / "XingYueDesktop"
        base.mkdir(parents=True, exist_ok=True)
        with open(base / "crash.log", "a", encoding="utf-8") as handle:
            handle.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}]\n{detail}\n")
    except OSError:
        pass
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication([])
        app.processEvents()
        QMessageBox.critical(
            None,
            "星月-桌面整理",
            f"程序遇到问题：{exc}\n\n详细信息已写入：\n{base / 'crash.log'}",
        )
    except Exception:
        pass


def _exception_hook(exc_type, exc, tb) -> None:
    _crash(exc)


def _start(args: argparse.Namespace) -> int:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import QApplication

    from .core.service import AppService
    from .core.storage import Store
    from .ui.main_window import MainWindow

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("星月-桌面整理")
    app.setOrganizationName("XingYue")
    sys.excepthook = _exception_hook

    if args.data_dir:
        data_dir = Path(args.data_dir)
    elif args.demo:
        data_dir = Path(tempfile.gettempdir()) / "xingyue-demo" if args.screenshot else Path.cwd() / ".demo-data"
    else:
        data_dir = None
    store = Store(data_dir)
    if args.theme:
        settings = store.load_settings()
        settings.theme = args.theme
        store.save_settings(settings)

    service = AppService(store=store, demo=args.demo)
    if args.demo:
        seed_demo(service)

    window = MainWindow(service)
    if args.size and "x" in args.size:
        try:
            width, height = args.size.lower().split("x", 1)
            window.resize(int(width), int(height))
        except ValueError:
            pass
    window.show()

    if args.screenshot:
        target = Path(args.screenshot)

        def capture() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            pixmap = window.grab()
            pixmap.save(str(target), "PNG")
            print(f"screenshot saved: {target} ({pixmap.width()}x{pixmap.height()})")
            app.quit()

        QTimer.singleShot(1400, capture)

    return app.exec()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="星月-桌面整理")
    parser.add_argument("--demo", action="store_true", help="演示模式，不读写真实桌面")
    parser.add_argument("--data-dir", type=str, default="", help="自定义数据目录")
    parser.add_argument("--screenshot", type=str, default="", help="渲染界面并保存 PNG 后退出")
    parser.add_argument("--size", type=str, default="", help="窗口尺寸，例如 1360x880")
    parser.add_argument("--theme", type=str, choices=["light", "dark"], default="")
    args = parser.parse_args(argv)

    set_dpi_awareness()
    try:
        return _start(args)
    except Exception as exc:  # 打包为无控制台程序时的兜底
        _crash(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
