"""对话框：命名、危险操作确认、关于。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .icons import ICON_ERR, ICON_PRIMARY, icon_pixmap
from .widgets import ToggleSwitch


def _button(text: str, variant: str = "primary", parent: QWidget | None = None) -> QPushButton:
    button = QPushButton(text, parent)
    button.setProperty("variant", variant)
    button.setCursor(Qt.PointingHandCursor)
    button.setMinimumWidth(86)
    return button


class NameDialog(QDialog):
    def __init__(self, title: str, label: str, value: str = "",
                 ok_text: str = "保存", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedWidth(420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(10)

        heading = QLabel(title)
        heading.setObjectName("H2")
        heading.setStyleSheet("font-size:14px; font-weight:600;")
        layout.addWidget(heading)

        if label:
            hint = QLabel(label)
            hint.setObjectName("Muted")
            hint.setWordWrap(True)
            layout.addWidget(hint)

        self.edit = QLineEdit(value)
        self.edit.setMaxLength(40)
        self.edit.selectAll()
        self.edit.returnPressed.connect(self.accept)
        layout.addWidget(self.edit)

        row = QHBoxLayout()
        row.addStretch(1)
        cancel = _button("取消", "default")
        cancel.clicked.connect(self.reject)
        confirm = _button(ok_text)
        confirm.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(confirm)
        layout.addLayout(row)
        self.edit.setFocus()

    def value(self) -> str:
        return self.edit.text().strip()

    @classmethod
    def ask(cls, parent: QWidget | None, title: str, label: str, value: str = "",
            ok_text: str = "保存") -> str | None:
        dialog = cls(title, label, value, ok_text, parent)
        if dialog.exec() == QDialog.Accepted:
            return dialog.value()
        return None


class ConfirmDialog(QDialog):
    def __init__(
        self,
        title: str,
        message: str,
        details: str = "",
        confirm_text: str = "确认执行",
        danger: bool = False,
        checkbox_text: str = "",
        checked: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMaximumWidth(620)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(10)
        icon = QLabel()
        icon.setPixmap(icon_pixmap("info" if not danger else "trash",
                                   ICON_ERR if danger else ICON_PRIMARY, 24))
        icon.setFixedSize(28, 28)
        head.addWidget(icon, 0, Qt.AlignTop)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size:14px; font-weight:600;")
        head.addWidget(title_label, 1)
        layout.addLayout(head)

        body = QLabel(message)
        body.setObjectName("DialogBody")
        body.setWordWrap(True)
        layout.addWidget(body)

        if details:
            detail_view = QTextEdit()
            detail_view.setObjectName("LogView")
            detail_view.setReadOnly(True)
            detail_view.setPlainText(details)
            lines = details.count("\n") + 1
            height = max(84, min(172, 22 + lines * 18))
            detail_view.setFixedHeight(height)
            layout.addWidget(detail_view)

        self.check_switch: ToggleSwitch | None = None
        if checkbox_text:
            row = QHBoxLayout()
            row.setSpacing(9)
            self.check_switch = ToggleSwitch(checked)
            label = QLabel(checkbox_text)
            label.setObjectName("DialogBody")
            row.addWidget(self.check_switch, 0, Qt.AlignVCenter)
            row.addWidget(label, 1)
            layout.addLayout(row)

        row = QHBoxLayout()
        row.addStretch(1)
        cancel = _button("取消", "default")
        cancel.clicked.connect(self.reject)
        confirm = _button(confirm_text, "danger" if danger else "primary")
        confirm.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(confirm)
        layout.addLayout(row)

    def checkbox_checked(self) -> bool:
        return bool(self.check_switch and self.check_switch.isChecked())


def confirm(
    parent: QWidget | None,
    title: str,
    message: str,
    details: str = "",
    confirm_text: str = "确认执行",
    danger: bool = False,
    checkbox_text: str = "",
    checked: bool = False,
) -> tuple[bool, bool]:
    dialog = ConfirmDialog(title, message, details, confirm_text, danger, checkbox_text, checked, parent)
    accepted = dialog.exec() == QDialog.Accepted
    return accepted, dialog.checkbox_checked()
