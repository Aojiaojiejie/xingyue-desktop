"""对话框样式检查（开发用）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from xingyue_desktop.cli import set_dpi_awareness  # noqa: E402

set_dpi_awareness()

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xingyue_desktop.ui.dialogs import ConfirmDialog, NameDialog  # noqa: E402
from xingyue_desktop.ui.theme import apply_theme  # noqa: E402

app = QApplication(sys.argv[:1])
out = ROOT / "artifacts" / "ui-shots"
out.mkdir(parents=True, exist_ok=True)

details = "\n".join([
    "季度报告.docx  →  文档/",
    "预算表.xlsx  →  表格/",
    "封面图.png  →  图片/",
    "素材包.zip  →  压缩包/",
    "… 其余 8 个文件",
])
for theme in ("light", "dark"):
    apply_theme(app, theme)
    dialog = ConfirmDialog(
        "确认整理 12 个文件？",
        "将把 12 个文件移动到桌面上的 5 个分类文件夹（文档, 表格, 图片, 压缩包, 其他），共 24.6 MB。\n"
        "文件只会被归类，不会被删除；整理后可通过「撤销」还原。",
        details,
        "开始整理",
        False,
        "整理前记录桌面快照",
        True,
    )
    dialog.show()
    QTest.qWait(250)
    dialog.grab().save(str(out / f"dialog-tidy-{theme}.png"))
    dialog.close()

    danger = ConfirmDialog(
        "删除这套方案？",
        "「工作布局」记录了 29 个图标的坐标，删除后无法恢复。\n桌面上的图标本身不会受到影响。",
        confirm_text="删除方案",
        danger=True,
    )
    danger.show()
    QTest.qWait(200)
    danger.grab().save(str(out / f"dialog-delete-{theme}.png"))
    danger.close()

    name = NameDialog("快照当前桌面", "", "方案 3", "保存快照")
    name.show()
    QTest.qWait(200)
    name.grab().save(str(out / f"dialog-name-{theme}.png"))
    name.close()

print("dialogs saved")
