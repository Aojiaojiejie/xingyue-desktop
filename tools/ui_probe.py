"""UI 几何与主题快照检查（开发用）。"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from xingyue_desktop.cli import seed_demo, set_dpi_awareness  # noqa: E402

set_dpi_awareness()

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xingyue_desktop.core.service import AppService  # noqa: E402
from xingyue_desktop.core.storage import Store  # noqa: E402
from xingyue_desktop.ui.main_window import MainWindow  # noqa: E402

data_dir = ROOT / "artifacts" / ".probe-data"
shutil.rmtree(data_dir, ignore_errors=True)
out_dir = ROOT / "artifacts" / "ui-shots"
out_dir.mkdir(parents=True, exist_ok=True)

app = QApplication(sys.argv[:1])
store = Store(data_dir)
service = AppService(store=store, demo=True)
seed_demo(service)

window = MainWindow(service)
window.resize(1360, 880)
window.show()
QTest.qWait(600)


def dump(tag: str) -> None:
    preview = window.preview
    bar = window.right_scroll.verticalScrollBar()
    print(f"--- {tag} ---")
    print("window:", window.width(), window.height(), "compact:", window._compact)
    print("body sizes:", window.body.sizes())
    print("left visible:", window.left_panel.isVisible(), "right visible:", window.right_panel.isVisible())
    print("preview widget:", preview.width(), preview.height(), "stage scale:", round(preview._scale, 3))
    print("right scroll: max=", bar.maximum(), "visible=", bar.isVisible(), "width=", bar.width())
    print("scheme card count:", len(window.scheme_list._cards))
    print("log lines:", len(window.log.entries), "log height:", window.log.height())
    print("snapshot count:", len(window.snapshots), "active:", store.active_id)


dump("light 1360x880")
window.grab().save(str(out_dir / "ui-light.png"))

window._theme = "dark"
window.theme = "dark"
window.settings.theme = "dark"
window._apply_theme()
QTest.qWait(300)
dump("dark 1360x880")
window.grab().save(str(out_dir / "ui-dark.png"))

window.resize(1000, 700)
QTest.qWait(500)
dump("compact 1000x700")
window.grab().save(str(out_dir / "ui-compact.png"))

window.resize(880, 620)
QTest.qWait(400)
dump("minimum 880x620")
window.grab().save(str(out_dir / "ui-min.png"))

print("saved to", out_dir)
