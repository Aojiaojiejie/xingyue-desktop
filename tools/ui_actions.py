"""交互烟雾测试：演示模式下执行应用/收纳/排序，并截图（开发用）。"""

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

data_dir = ROOT / "artifacts" / ".actions-data"
shutil.rmtree(data_dir, ignore_errors=True)
out = ROOT / "artifacts" / "ui-shots"
out.mkdir(parents=True, exist_ok=True)

app = QApplication(sys.argv[:1])
service = AppService(store=Store(data_dir), demo=True)
seed_demo(service)
window = MainWindow(service)
window.resize(1360, 880)
window.show()
QTest.qWait(500)

print("initial items:", len(window.state.items), "pending:", len(window._pending_items()))

window.act_apply.click()
QTest.qWait(600)
print("after apply pending:", len(window._pending_items()), "active:", service.store.active_id)
window.grab().save(str(out / "action-apply.png"))

window._move_new_to_zone()
QTest.qWait(500)
print("after zone pending:", len(window._pending_items()))
window.grab().save(str(out / "action-zone.png"))

window._order_icons()
QTest.qWait(500)
print("after order items:", len(window.state.items))
window.grab().save(str(out / "action-order.png"))

window.resize(1000, 700)
QTest.qWait(400)
window.btn_left.click()
QTest.qWait(500)
print("compact panel:", window._compact, "left visible:", window.left_panel.isVisible(),
      "right visible:", window.right_panel.isVisible(), "body:", window.body.sizes())
window.grab().save(str(out / "compact-open-left.png"))

window.btn_right.click()
QTest.qWait(500)
print("after right click left:", window.left_panel.isVisible(), "right:", window.right_panel.isVisible())
window.grab().save(str(out / "compact-open-right.png"))

print("done")
