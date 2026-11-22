"""可复用控件：方案卡片、预览画布、日志面板、开关、动作按钮、Toast。"""

from __future__ import annotations

import html
import math
from datetime import datetime

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
    QTextBlockFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.models import KIND_COLORS, KIND_LABELS, DesktopItem, Snapshot, pretty_time
from .icons import ICON_MUTED, icon_pixmap
from .theme import mono_font, palette


def repolish(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")


class Divider(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Divider")
        self.setFixedHeight(1)


class Chip(QLabel):
    def __init__(self, text: str = "", kind: str = "normal", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("ChipWarn" if kind == "warn" else "Chip")
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)


class ElidedLabel(QLabel):
    """按可用宽度省略的标签，悬停显示全文。"""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full = text
        self.setToolTip(text)
        self._apply()

    def set_full_text(self, text: str) -> None:
        self._full = text
        self.setToolTip(text)
        self._apply()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply()

    def _apply(self) -> None:
        metrics = QFontMetrics(self.font())
        width = max(0, self.width() - 2)
        text = metrics.elidedText(self._full, Qt.ElideRight, width) if width else self._full
        super().setText(text)


class ToggleSwitch(QAbstractButton):
    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(40, 22)
        self._offset = 1.0 if checked else 0.0
        self._on = QColor("#4F5BD5")
        self._off = QColor("#CBD2E4")
        self._knob = QColor("#FFFFFF")
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(float(self._offset))
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def apply_theme(self, colors: dict[str, str]) -> None:
        self._on = QColor(colors["primary"])
        self._off = QColor(colors["border_strong"])
        self._knob = QColor("#FFFFFF")
        self.update()

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, value: float) -> None:
        self._offset = float(value)
        self.update()

    offset = Property(float, get_offset, set_offset)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(40, 22)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        track = QRectF(1, 2, self.width() - 2, self.height() - 4)
        color = QColor(self._on if self.isChecked() else self._off)
        if not self.isEnabled():
            color.setAlpha(120)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(track, track.height() / 2, track.height() / 2)
        radius = track.height() / 2 - 2.5
        cx = track.left() + radius + 2.5 + self._offset * (track.width() - 2 * radius - 5)
        painter.setBrush(self._knob)
        painter.drawEllipse(QPointF(cx, track.center().y()), radius, radius)
        painter.end()


class SettingRow(QWidget):
    def __init__(self, title: str, control: QWidget, subtitle: str = "",
                 icon_name: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(9)
        if icon_name:
            icon = QLabel()
            icon.setPixmap(icon_pixmap(icon_name, ICON_MUTED, 16))
            icon.setFixedSize(18, 18)
            icon.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon, 0, Qt.AlignTop)
        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        label = QLabel(title)
        label.setStyleSheet("font-size:12px;")
        text_box.addWidget(label)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("MutedSmall")
            sub.setWordWrap(True)
            text_box.addWidget(sub)
        layout.addLayout(text_box, 1)
        layout.addWidget(control, 0, Qt.AlignVCenter)


class ActionCard(QPushButton):
    def __init__(self, icon_name: str, title: str, subtitle: str = "",
                 variant: str = "default", icon_color: str = ICON_MUTED,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ActionCard")
        self.setProperty("variant", variant)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(56 if subtitle else 46)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(11, 8, 10, 8)
        layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap(icon_name, icon_color, 20))
        icon_label.setFixedSize(26, 26)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label, 0, Qt.AlignVCenter)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        title_label = QLabel(title)
        title_label.setObjectName("ActionTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("ActionSub")
        text_box.addWidget(title_label)
        if subtitle:
            text_box.addWidget(subtitle_label)
        else:
            subtitle_label.hide()
        layout.addLayout(text_box, 1)
        self.title_label = title_label
        self.subtitle_label = subtitle_label
        self._variant = variant

        chevron = QLabel()
        chevron.setPixmap(icon_pixmap("chevron_right", "#FFFFFF" if variant == "primary" else "#A6ADC8", 14))
        chevron.setFixedSize(16, 16)
        layout.addWidget(chevron, 0, Qt.AlignVCenter)

        for child in (icon_label, title_label, subtitle_label, chevron):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802
        super().setEnabled(enabled)
        effect = self.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(effect)
        effect.setOpacity(1.0 if enabled else 0.55)


class SchemeCard(QFrame):
    clicked = Signal(str)
    activated = Signal(str)
    menu_requested = Signal(str, QPoint)

    def __init__(self, snapshot: Snapshot, active: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.snapshot = snapshot
        self.snapshot_id = snapshot.id
        self.setObjectName("SchemeCard")
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("selected", "false")
        self.setToolTip(
            f"{snapshot.name}\n{len(snapshot.items)} 个图标 · {pretty_time(snapshot.created_at)}\n"
            f"记录分辨率 {snapshot.desktop_w} × {snapshot.desktop_h}"
        )

        outer = QHBoxLayout(self)
        outer.setContentsMargins(9, 9, 10, 9)
        outer.setSpacing(9)

        self.bar = QFrame()
        self.bar.setObjectName("AccentBar")
        self.bar.setFixedWidth(3)
        self.bar.setVisible(False)
        outer.addWidget(self.bar)

        content = QVBoxLayout()
        content.setSpacing(3)
        top = QHBoxLayout()
        top.setSpacing(6)
        self.name_label = ElidedLabel(snapshot.name)
        self.name_label.setStyleSheet("font-size:12.5px; font-weight:600;")
        top.addWidget(self.name_label, 1)
        if active:
            badge = QLabel("使用中")
            badge.setObjectName("Badge")
            top.addWidget(badge, 0, Qt.AlignRight)
        if snapshot.auto:
            auto = QLabel("自动")
            auto.setObjectName("BadgeAuto")
            top.addWidget(auto, 0, Qt.AlignRight)
        content.addLayout(top)

        meta = QLabel(f"{len(snapshot.items)} 个图标 · {pretty_time(snapshot.created_at)}")
        meta.setObjectName("MutedSmall")
        content.addWidget(meta)
        outer.addLayout(content, 1)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        self.bar.setVisible(selected)
        repolish(self)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.snapshot_id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.activated.emit(self.snapshot_id)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        self.menu_requested.emit(self.snapshot_id, event.globalPos())


class SchemeList(QScrollArea):
    selected = Signal(str)
    activated = Signal(str)
    menu_requested = Signal(str, QPoint)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.viewport().setAutoFillBackground(False)
        self._container = QWidget()
        self._container.setAutoFillBackground(False)
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(1, 1, 5, 1)
        self._layout.setSpacing(7)
        self._layout.addStretch(1)
        self.setWidget(self._container)
        self._cards: list[SchemeCard] = []
        self._snapshots: list[Snapshot] = []
        self._active_id: str | None = None
        self._selected_id: str | None = None
        self._filter = ""

    def set_data(self, snapshots: list[Snapshot], active_id: str | None,
                 selected_id: str | None = None) -> None:
        self._snapshots = snapshots
        self._active_id = active_id
        self._selected_id = selected_id
        self._rebuild()

    def set_filter(self, text: str) -> None:
        self._filter = text.strip().casefold()
        self._rebuild()

    def selected_id(self) -> str | None:
        return self._selected_id

    def _rebuild(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._cards.clear()

        visible = [s for s in self._snapshots if not self._filter or self._filter in s.name.casefold()]
        if not visible:
            hint = QLabel("暂无方案" if not self._snapshots else "无匹配结果")
            hint.setAlignment(Qt.AlignCenter)
            hint.setObjectName("Muted")
            hint.setMinimumHeight(120)
            self._layout.addWidget(hint)
            self._layout.addStretch(1)
            return

        previous = self._selected_id
        if self._selected_id not in {s.id for s in visible}:
            self._selected_id = visible[0].id
        for snapshot in visible:
            card = SchemeCard(snapshot, active=snapshot.id == self._active_id)
            card.set_selected(snapshot.id == self._selected_id)
            card.clicked.connect(self._on_clicked)
            card.activated.connect(self.activated.emit)
            card.menu_requested.connect(self.menu_requested.emit)
            self._layout.addWidget(card)
            self._cards.append(card)
        self._layout.addStretch(1)
        if previous != self._selected_id and self._selected_id:
            selected = self._selected_id
            QTimer.singleShot(0, lambda: self.selected.emit(selected))

    def _on_clicked(self, snapshot_id: str) -> None:
        self._selected_id = snapshot_id
        for card in self._cards:
            card.set_selected(card.snapshot_id == snapshot_id)
        self.selected.emit(snapshot_id)

    def select(self, snapshot_id: str) -> None:
        self._selected_id = snapshot_id
        for card in self._cards:
            card.set_selected(card.snapshot_id == snapshot_id)


class DesktopPreview(QWidget):
    """按真实坐标比例绘制桌面与待整理区。"""

    def __init__(self, colors: dict[str, str] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.colors = colors or palette("light")
        self.items: list[DesktopItem] = []
        self.canvas_size = (1440, 900)
        self.spacing = (96, 96)
        self.zone_width = 272
        self.snapshot_keys: set[str] = set()
        self.has_snapshot = False
        self.available = True
        self.hover_index: int | None = None
        self._cells: list[tuple[QRectF, DesktopItem, bool]] = []
        self._stage = QRectF()
        self._content = (1440, 900)
        self._scale = 1.0
        self.setMouseTracking(True)
        self.setMinimumSize(360, 220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def apply_theme(self, colors: dict[str, str]) -> None:
        self.colors = colors
        self.update()

    def set_available(self, available: bool) -> None:
        self.available = available

    def set_data(
        self,
        items: list[DesktopItem],
        canvas_size: tuple[int, int],
        spacing: tuple[int, int],
        zone_width: int,
        snapshot: Snapshot | None,
    ) -> None:
        self.items = items
        self.canvas_size = canvas_size
        self.spacing = spacing
        self.zone_width = max(0, zone_width)
        if snapshot:
            self.snapshot_keys = {self._key(i.name) for i in snapshot.items}
            self.has_snapshot = True
        else:
            self.snapshot_keys = set()
            self.has_snapshot = False
        max_x = max((i.x for i in items), default=0) + spacing[0]
        max_y = max((i.y for i in items), default=0) + spacing[1]
        self._content = (max(canvas_size[0], max_x), max(canvas_size[1], max_y))
        self.update()

    @staticmethod
    def _key(name: str) -> str:
        from ..core.models import normalize_key

        return normalize_key(name)

    def _is_extra(self, item: DesktopItem) -> bool:
        return self.has_snapshot and item.key not in self.snapshot_keys

    def _compute_geometry(self) -> QRectF:
        margins = 14
        avail_w = max(10.0, self.width() - margins * 2)
        avail_h = max(10.0, self.height() - margins * 2)
        content_w, content_h = self._content
        scale = min(avail_w / max(1, content_w), avail_h / max(1, content_h))
        width = content_w * scale
        height = content_h * scale
        x = (self.width() - width) / 2
        y = (self.height() - height) / 2
        self._scale = scale
        return QRectF(x, y, width, height)

    def paintEvent(self, event) -> None:  # noqa: N802
        colors = self.colors
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        stage = self._compute_geometry()
        self._stage = stage
        self._cells = []
        if stage.width() < 20 or stage.height() < 20:
            painter.end()
            return

        stage_path = QPainterPath()
        stage_path.addRoundedRect(stage, 12, 12)
        painter.setPen(QPen(QColor(colors["border"]), 1))
        painter.setBrush(QColor(colors["canvas"]))
        painter.drawPath(stage_path)

        painter.save()
        painter.setClipPath(stage_path)

        dot_pen = QPen(QColor(colors["grid_dot"]), 1)
        dot_pen.setWidthF(1.2)
        painter.setPen(dot_pen)
        step = 26.0
        x = stage.left() + step
        while x < stage.right():
            y = stage.top() + step
            while y < stage.bottom():
                painter.drawPoint(QPointF(x, y))
                y += step
            x += step

        scale = self._scale
        stage_left = stage.left()
        stage_top = stage.top()
        spacing_w = self.spacing[0] * scale
        spacing_h = self.spacing[1] * scale

        zone_w = min(stage.width() * 0.45, self.zone_width * scale)
        if zone_w > 8 and self.items:
            zone_rect = QRectF(stage.right() - zone_w, stage.top(), zone_w, stage.height())
            zone_color = QColor(colors["accent"])
            fill = QColor(zone_color)
            fill.setAlpha(18)
            painter.fillRect(zone_rect, fill)
            pen = QPen(zone_color, 1.2, Qt.DashLine)
            pen.setDashPattern([4, 4])
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawLine(zone_rect.topLeft(), zone_rect.bottomLeft())
            label_font = QFont(self.font())
            label_font.setPixelSize(9)
            painter.setFont(label_font)
            label_rect = QRectF(zone_rect.left() + 6, zone_rect.top() + 6, max(46.0, zone_w - 12), 18)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(colors["accent_soft"]))
            painter.drawRoundedRect(label_rect, 6, 6)
            painter.setPen(QColor(colors["warn"]))
            painter.drawText(label_rect, Qt.AlignCenter, "待整理")

        viewport_h = self.canvas_size[1] * scale
        if self._content[1] > self.canvas_size[1] + 1 and viewport_h < stage.height() - 6:
            line_y = stage.top() + viewport_h
            pen = QPen(QColor(colors["border_strong"]), 1, Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(QPointF(stage.left() + 4, line_y), QPointF(stage.right() - 4, line_y))

        if not self.items:
            self._paint_empty(painter, stage)
        else:
            for item in self.items:
                extra = self._is_extra(item)
                cell = QRectF(
                    stage_left + item.x * scale,
                    stage_top + item.y * scale,
                    spacing_w,
                    spacing_h,
                )
                if cell.right() < stage.left() - 2 or cell.bottom() < stage.top() - 2:
                    continue
                if cell.left() > stage.right() + 2 or cell.top() > stage.bottom() + 2:
                    continue
                self._paint_icon(painter, cell, item, extra, scale)
                self._cells.append((cell, item, extra))

        painter.restore()

        hovered: DesktopItem | None = None
        if self.hover_index is not None and 0 <= self.hover_index < len(self._cells):
            hovered = self._cells[self.hover_index][1]
        if hovered is not None:
            self._paint_hover_info(painter, stage, hovered)

        painter.end()

    def _paint_icon(self, painter: QPainter, cell: QRectF, item: DesktopItem,
                    extra: bool, scale: float) -> None:
        colors = self.colors
        base = QColor(KIND_COLORS.get(item.kind, KIND_COLORS["other"]))
        dark = QColor(colors["canvas"]).lightness() < 128
        side = min(cell.width() * 0.52, cell.height() * 0.48, 34.0)
        side = max(12.0, side)
        icon_rect = QRectF(
            cell.center().x() - side / 2,
            cell.top() + max(3.0, cell.height() * 0.12),
            side,
            side,
        )
        painter.save()
        painter.setPen(QPen(base.lighter(132) if dark else base.lighter(118), 1))
        fill = QColor(base)
        fill.setAlpha(62 if dark else 34)
        painter.setBrush(fill)
        painter.drawRoundedRect(icon_rect, side * 0.26, side * 0.26)

        glyph = item.name.strip()[:1] or "?"
        font = QFont(self.font())
        font.setPixelSize(int(max(8, min(side * 0.52, 16))))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(base.lighter(152) if dark else base.darker(135))
        painter.drawText(icon_rect, Qt.AlignCenter, glyph)

        if extra:
            badge_r = max(2.0, side * 0.09)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(colors["accent"]))
            painter.drawEllipse(QPointF(icon_rect.right() - badge_r, icon_rect.top() + badge_r),
                                badge_r, badge_r)
            pen = QPen(QColor(colors["accent"]), 1, Qt.DashLine)
            pen.setDashPattern([2, 2])
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            ring = cell.adjusted(1, 1, -1, -1)
            painter.drawRoundedRect(ring, 7, 7)

        label_font = QFont(self.font())
        label_font.setPixelSize(int(max(7, min(cell.width() * 0.19, 9.5))))
        painter.setFont(label_font)
        metrics = QFontMetrics(label_font)
        available = cell.width() - 4
        if available >= 24 and cell.width() >= 44 and cell.height() >= 42:
            text = metrics.elidedText(item.name, Qt.ElideRight, int(available))
            painter.setPen(QColor(colors["accent"] if extra else colors["text_soft"]))
            label_rect = QRectF(cell.left() + 2, icon_rect.bottom() + 2, available,
                                max(10.0, cell.bottom() - icon_rect.bottom() - 2))
            painter.drawText(label_rect, Qt.AlignHCenter | Qt.AlignTop, text)
        painter.restore()

    def _paint_empty(self, painter: QPainter, stage: QRectF) -> None:
        colors = self.colors
        cx, cy = stage.center().x(), stage.center().y() - 16
        painter.save()
        moon = QPainterPath()
        moon.addEllipse(QRectF(cx - 26, cy - 30, 52, 56))
        cut = QPainterPath()
        cut.addEllipse(QRectF(cx - 10, cy - 36, 50, 50))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(colors["accent"]))
        painter.setOpacity(0.9)
        painter.drawPath(moon.subtracted(cut))
        painter.setOpacity(1.0)
        star = QPointF(cx + 34, cy - 24)
        path = QPainterPath()
        for i in range(8):
            radius = 7.0 if i % 2 == 0 else 1.8
            angle = math.radians(-90 + i * 45)
            point = QPointF(star.x() + radius * math.cos(angle), star.y() + radius * math.sin(angle))
            if i == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        path.closeSubpath()
        painter.setBrush(QColor(colors["primary"]))
        painter.drawPath(path)

        title_font = QFont(self.font())
        title_font.setPixelSize(14)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor(colors["text"]))
        title_rect = QRectF(stage.left(), cy + 44, stage.width(), 22)
        painter.drawText(title_rect, Qt.AlignCenter, "暂无桌面图标" if self.available else "无法读取桌面")
        painter.restore()

    def _paint_hover_info(self, painter: QPainter, stage: QRectF, item: DesktopItem) -> None:
        colors = self.colors
        text = f"{item.name} · {KIND_LABELS.get(item.kind, '其他')} · ({item.x}, {item.y})"
        font = QFont(self.font())
        font.setPixelSize(10)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        text = metrics.elidedText(text, Qt.ElideRight, int(stage.width() - 48))
        width = metrics.horizontalAdvance(text) + 20
        rect = QRectF(stage.left() + 12, stage.bottom() - 30, min(width, stage.width() - 24), 20)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(colors["surface"]))
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(QPen(QColor(colors["border"]), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(QColor(colors["text_soft"]))
        painter.drawText(rect.adjusted(10, 0, -10, 0), Qt.AlignVCenter | Qt.AlignLeft, text)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        index = None
        for i, (cell, _item, _extra) in enumerate(self._cells):
            if cell.contains(pos):
                index = i
                break
        if index != self.hover_index:
            self.hover_index = index
            self.setCursor(Qt.PointingHandCursor if index is not None else Qt.ArrowCursor)
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        if self.hover_index is not None:
            self.hover_index = None
            self.setCursor(Qt.ArrowCursor)
            self.update()
        super().leaveEvent(event)


class LogView(QTextEdit):
    LEVEL_STYLE = {
        "info": "muted",
        "ok": "ok",
        "warn": "warn",
        "error": "err",
        "action": "primary",
        "muted": "muted",
    }
    LEVEL_LABEL = {
        "info": "信息",
        "ok": "完成",
        "warn": "注意",
        "error": "错误",
        "action": "操作",
        "muted": "预演",
    }

    def __init__(self, colors: dict[str, str] | None = None, limit: int = 600,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.colors = colors or palette("light")
        self.limit = limit
        self.entries: list[tuple[str, str, str]] = []
        self.setObjectName("LogView")
        self.setReadOnly(True)
        self.setFont(mono_font())
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.document().setMaximumBlockCount(limit)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def apply_theme(self, colors: dict[str, str]) -> None:
        self.colors = colors
        self.rebuild()

    def append_entry(self, level: str, message: str, time_str: str | None = None) -> None:
        time_str = time_str or datetime.now().strftime("%H:%M:%S")
        level = level if level in self.LEVEL_LABEL else "info"
        self.entries.append((level, message, time_str))
        if len(self.entries) > self.limit:
            self.entries = self.entries[-self.limit:]
        bar = self.verticalScrollBar()
        at_bottom = bar.value() >= bar.maximum() - 4
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        block_format = QTextBlockFormat()
        block_format.setTopMargin(2)
        block_format.setBottomMargin(2)
        if self.document().characterCount() > 1:
            cursor.insertBlock(block_format)
        cursor.insertHtml(self._html(level, message, time_str))
        self.setTextCursor(cursor)
        if at_bottom:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def _html(self, level: str, message: str, time_str: str) -> str:
        colors = self.colors
        color = colors[self.LEVEL_STYLE.get(level, "muted")]
        label = self.LEVEL_LABEL.get(level, "信息")
        safe = html.escape(message).replace("\n", "<br>")
        return (
            f'<span style="color:{colors["muted"]};">{time_str}</span>&nbsp;&nbsp;'
            f'<span style="color:{color}; font-weight:600;">{label}</span>&nbsp;&nbsp;'
            f'<span style="color:{colors["text_soft"]};">{safe}</span>'
        )

    def rebuild(self) -> None:
        bar = self.verticalScrollBar()
        at_bottom = bar.value() >= bar.maximum() - 4
        parts = [f'<body style="background:{self.colors["surface_alt"]}; margin:0;">']
        for level, message, time_str in self.entries:
            parts.append(f'<div style="margin:3px 0;">{self._html(level, message, time_str)}</div>')
        parts.append("</body>")
        self.setHtml("".join(parts))
        if at_bottom:
            bar.setValue(bar.maximum())

    def clear_entries(self) -> None:
        self.entries.clear()
        self.clear()

    def export_text(self) -> str:
        return "\n".join(f"{t} [{self.LEVEL_LABEL.get(l, l)}] {m}" for l, m, t in self.entries)

    def appendPlain(self, text: str) -> None:  # 兼容 QTextEdit 接口
        self.append_entry("info", text)


class Toast(QFrame):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setProperty("kind", "ok")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 9, 16, 9)
        layout.setSpacing(9)
        self.dot = QLabel("●")
        self.dot.setStyleSheet("font-size:10px;")
        self.text = QLabel("")
        self.text.setObjectName("ToastText")
        layout.addWidget(self.dot, 0, Qt.AlignVCenter)
        layout.addWidget(self.text, 1)
        self.effect = QGraphicsOpacityEffect(self)
        self.effect.setOpacity(0.0)
        self.setGraphicsEffect(self.effect)
        self.fade_in = QPropertyAnimation(self.effect, b"opacity", self)
        self.fade_in.setDuration(160)
        self.fade_out = QPropertyAnimation(self.effect, b"opacity", self)
        self.fade_out.setDuration(220)
        self.fade_out.finished.connect(self.hide)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self.hide()

    def show_message(self, message: str, kind: str = "ok", msec: int = 2800) -> None:
        colors = palette(self._theme)
        color = {"ok": colors["ok"], "warn": colors["warn"], "error": colors["err"],
                 "info": colors["primary"]}.get(kind, colors["ok"])
        self.dot.setStyleSheet(f"color:{color}; font-size:10px;")
        self.text.setText(message)
        self.setProperty("kind", kind)
        repolish(self)
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self.fade_in.stop()
        self.fade_out.stop()
        self.effect.setOpacity(0.0)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.start()
        self._timer.start(msec)

    _theme = "light"

    def set_theme(self, theme: str) -> None:
        self._theme = theme

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if not parent:
            return
        x = max(12, parent.width() - self.width() - 24)
        y = max(90, parent.height() - self.height() - 42)
        self.move(x, y)

    def _fade_out(self) -> None:
        self.fade_in.stop()
        self.fade_out.stop()
        self.fade_out.setStartValue(self.effect.opacity())
        self.fade_out.setEndValue(0.0)
        self.fade_out.start()
