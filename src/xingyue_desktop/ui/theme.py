"""主题与样式：浅色 / 深色两套色板 + 全局 QSS。"""

from __future__ import annotations

from string import Template

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

PALETTES: dict[str, dict[str, str]] = {
    "light": {
        "bg": "#F2F4FB",
        "bg_grad_a": "#F5F7FD",
        "bg_grad_b": "#ECEFFA",
        "surface": "#FFFFFF",
        "surface_alt": "#F7F8FD",
        "surface_sunken": "#EFF2FA",
        "border": "#E4E8F3",
        "border_strong": "#CBD2E4",
        "text": "#1B1F3B",
        "text_soft": "#49506E",
        "muted": "#8A91A8",
        "primary": "#4F5BD5",
        "primary_strong": "#414CC0",
        "primary_soft": "#EDEFFF",
        "btn_primary": "#4F5BD5",
        "btn_primary_strong": "#414CC0",
        "on_primary": "#FFFFFF",
        "accent": "#D9A441",
        "accent_soft": "#FBF2DF",
        "ok": "#1F9D6B",
        "ok_soft": "#E8F7F0",
        "warn": "#C07C22",
        "warn_soft": "#FBF0DC",
        "err": "#D14B4B",
        "err_soft": "#FBEAEA",
        "hover": "#F4F6FE",
        "selection": "#EEF1FF",
        "canvas": "#FFFFFF",
        "canvas_alt": "#F8F9FE",
        "grid_dot": "#DCE1EF",
        "shadow": "rgba(37, 48, 100, 0.10)",
        "scroll": "#CBD2E4",
    },
    "dark": {
        "bg": "#0B0E1C",
        "bg_grad_a": "#0D1122",
        "bg_grad_b": "#080B16",
        "surface": "#151932",
        "surface_alt": "#1A1F3B",
        "surface_sunken": "#11152A",
        "border": "#272D4E",
        "border_strong": "#3A426B",
        "text": "#E9EBF8",
        "text_soft": "#BEC4DE",
        "muted": "#8B93B6",
        "primary": "#7C88FF",
        "primary_strong": "#6874F2",
        "primary_soft": "#222858",
        "btn_primary": "#5864E6",
        "btn_primary_strong": "#4651CE",
        "on_primary": "#0C1024",
        "accent": "#F0C572",
        "accent_soft": "#2B2413",
        "ok": "#4BD08C",
        "ok_soft": "#143527",
        "warn": "#F0AE5A",
        "warn_soft": "#332614",
        "err": "#FF8080",
        "err_soft": "#3A1A1E",
        "hover": "#1E2445",
        "selection": "#212856",
        "canvas": "#11152B",
        "canvas_alt": "#0E1226",
        "grid_dot": "#2A3155",
        "shadow": "rgba(0, 0, 0, 0.35)",
        "scroll": "#39416A",
    },
}

QSS = Template(
    """
* { outline: none; }
QWidget {
    color: $text;
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI";
    font-size: 13px;
}
QMainWindow, QWidget#Root {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $bg_grad_a, stop:1 $bg_grad_b);
}
QDialog, QMessageBox { background: $bg; }
QFrame#Card {
    background: $surface;
    border: 1px solid $border;
    border-radius: 14px;
}
QLabel#H1 { font-size: 17px; font-weight: 600; color: $text; }
QLabel#H2 { font-size: 13px; font-weight: 600; color: $text; }
QLabel#Muted { color: $muted; font-size: 12px; }
QLabel#MutedSmall { color: $muted; font-size: 11px; }
QLabel#DialogBody { color: $text_soft; font-size: 12px; }
QLabel#Chip {
    background: $surface_alt;
    border: 1px solid $border;
    border-radius: 9px;
    padding: 4px 9px;
    color: $text_soft;
    font-size: 11px;
}
QLabel#ChipWarn {
    background: $warn_soft;
    border: 1px solid $warn;
    border-radius: 9px;
    padding: 4px 9px;
    color: $warn;
    font-size: 11px;
}
QLabel#Badge {
    background: $primary_soft;
    color: $primary;
    border-radius: 7px;
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 600;
}
QLabel#BadgeAuto {
    background: $surface_sunken;
    color: $muted;
    border-radius: 7px;
    padding: 2px 7px;
    font-size: 10px;
}
QLabel#StatValue { font-size: 16px; font-weight: 600; color: $text; }
QLabel#StatLabel { font-size: 11px; color: $muted; }
QFrame#AccentBar { background: $primary; border-radius: 2px; }

QPushButton {
    background: $surface_alt;
    color: $text;
    border: 1px solid $border;
    border-radius: 9px;
    padding: 8px 12px;
    font-size: 12px;
}
QPushButton:hover { background: $hover; border-color: $border_strong; }
QPushButton:pressed { background: $selection; }
QPushButton:disabled { color: $muted; background: $surface_sunken; border-color: $border; }

QPushButton[variant="primary"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $btn_primary, stop:1 $btn_primary_strong);
    color: #FFFFFF;
    border: none;
    border-radius: 9px;
    padding: 9px 14px;
    font-weight: 600;
}
QPushButton[variant="primary"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6A75E8, stop:1 $btn_primary);
}
QPushButton[variant="primary"]:pressed { background: $btn_primary_strong; }
QPushButton[variant="ghost"] {
    background: transparent;
    border: 1px solid transparent;
    color: $text_soft;
    padding: 6px 8px;
}
QPushButton[variant="ghost"]:hover { background: $hover; border-color: $border; }
QPushButton[variant="icon"] {
    background: transparent;
    border: 1px solid $border;
    border-radius: 9px;
    padding: 6px;
}
QPushButton[variant="icon"]:hover { background: $hover; border-color: $border_strong; }
QPushButton[variant="icon"]:checked { background: $primary_soft; border-color: $primary; }
QPushButton[variant="danger"] {
    background: transparent;
    border: 1px solid $err;
    color: $err;
}
QPushButton[variant="danger"]:hover { background: $err_soft; }

QPushButton#ActionCard {
    background: $surface_alt;
    border: 1px solid $border;
    border-radius: 11px;
    padding: 9px 11px;
    text-align: left;
}
QPushButton#ActionCard:hover { background: $hover; border-color: $border_strong; }
QPushButton#ActionCard:pressed { background: $selection; }
QPushButton#ActionCard QLabel#ActionTitle { color: $text; font-size: 12.5px; font-weight: 600; }
QPushButton#ActionCard QLabel#ActionSub { color: $muted; font-size: 10.5px; }
QPushButton#ActionCard[variant="primary"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $btn_primary, stop:1 $btn_primary_strong);
    border: 1px solid $btn_primary_strong;
}
QPushButton#ActionCard[variant="primary"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $btn_primary_strong, stop:1 $btn_primary);
}
QPushButton#ActionCard[variant="primary"] QLabel#ActionTitle { color: #FFFFFF; }
QPushButton#ActionCard[variant="primary"] QLabel#ActionSub { color: rgba(255, 255, 255, 0.78); }

QPushButton#ToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 6px;
}
QPushButton#ToolButton:hover { background: $hover; border-color: $border; }
QPushButton#ToolButton:checked { background: $primary_soft; border-color: $primary; color: $primary; }
QPushButton#ToolButton[expanded="true"] {
    background: $surface_alt;
    border: 1px solid $border;
    color: $text_soft;
    font-size: 12px;
}
QPushButton#ToolButton[expanded="true"]:hover { background: $hover; border-color: $border_strong; }
QPushButton#ToolButton[expanded="true"]:checked {
    background: $primary_soft;
    border-color: $primary;
    color: $primary;
}

QLineEdit {
    background: $surface_alt;
    border: 1px solid $border;
    border-radius: 9px;
    padding: 7px 10px;
    color: $text;
    selection-background-color: $primary;
    selection-color: $on_primary;
}
QLineEdit:focus { border-color: $primary; background: $surface; }

QComboBox, QSpinBox {
    background: $surface_alt;
    border: 1px solid $border;
    border-radius: 8px;
    padding: 5px 8px;
    color: $text;
    min-height: 24px;
}
QComboBox:hover, QSpinBox:hover { border-color: $border_strong; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: $surface;
    border: 1px solid $border;
    border-radius: 8px;
    selection-background-color: $primary_soft;
    selection-color: $text;
    padding: 4px;
    outline: none;
}
QSpinBox::up-button, QSpinBox::down-button { width: 16px; border: none; background: transparent; }

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: $scroll; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: $muted; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: $scroll; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QSplitter::handle { background: transparent; }
QSplitter::handle:horizontal { width: 8px; }
QSplitter::handle:vertical { height: 8px; }

QStatusBar { background: transparent; border-top: 1px solid $border; color: $muted; font-size: 11px; }
QStatusBar::item { border: none; }

QTextEdit#LogView {
    background: $surface_alt;
    border: none;
    border-radius: 10px;
    padding: 6px 8px;
    color: $text_soft;
    font-size: 12px;
}
QTextEdit#LogView QScrollBar:vertical { width: 8px; }

QToolTip {
    background: $surface;
    color: $text;
    border: 1px solid $border;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 11px;
}
QMenu {
    background: $surface;
    border: 1px solid $border;
    border-radius: 10px;
    padding: 6px;
}
QMenu::item { padding: 6px 22px 6px 12px; border-radius: 6px; color: $text; }
QMenu::item:selected { background: $primary_soft; color: $text; }
QMenu::separator { height: 1px; background: $border; margin: 4px 6px; }

QFrame#Divider { background: $border; max-height: 1px; border: none; }

QFrame#Toast {
    background: $surface;
    border: 1px solid $border;
    border-radius: 10px;
}
QFrame#Toast[kind="ok"] { border: 1px solid $ok; }
QFrame#Toast[kind="warn"] { border: 1px solid $warn; }
QFrame#Toast[kind="error"] { border: 1px solid $err; }
QFrame#Toast[kind="info"] { border: 1px solid $primary; }
QLabel#ToastText { color: $text; font-size: 12px; }
"""
)


def palette(theme: str) -> dict[str, str]:
    return PALETTES.get(theme, PALETTES["light"])


def qss(theme: str) -> str:
    return QSS.substitute(**palette(theme))


def ui_font() -> QFont:
    families = set(QFontDatabase.families())
    for name in ("Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Segoe UI"):
        if name in families:
            font = QFont(name)
            font.setPixelSize(13)
            return font
    font = QFont()
    font.setPixelSize(13)
    return font


def mono_font() -> QFont:
    families = set(QFontDatabase.families())
    for name in ("Cascadia Mono", "JetBrains Mono", "Consolas"):
        if name in families:
            font = QFont(name)
            font.setPixelSize(12)
            return font
    font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    font.setPixelSize(12)
    return font


def build_palette(theme: str) -> QPalette:
    colors = palette(theme)
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(colors["bg"]))
    pal.setColor(QPalette.WindowText, QColor(colors["text"]))
    pal.setColor(QPalette.Base, QColor(colors["surface"]))
    pal.setColor(QPalette.AlternateBase, QColor(colors["surface_alt"]))
    pal.setColor(QPalette.Text, QColor(colors["text"]))
    pal.setColor(QPalette.Button, QColor(colors["surface_alt"]))
    pal.setColor(QPalette.ButtonText, QColor(colors["text"]))
    pal.setColor(QPalette.Highlight, QColor(colors["primary"]))
    pal.setColor(QPalette.HighlightedText, QColor(colors["on_primary"]))
    pal.setColor(QPalette.ToolTipBase, QColor(colors["surface"]))
    pal.setColor(QPalette.ToolTipText, QColor(colors["text"]))
    pal.setColor(QPalette.PlaceholderText, QColor(colors["muted"]))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(colors["muted"]))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(colors["muted"]))
    return pal


def apply_theme(app: QApplication, theme: str) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(qss(theme))
    app.setPalette(build_palette(theme))
    app.setFont(ui_font())
