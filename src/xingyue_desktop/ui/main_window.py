"""主窗口：方案库 / 桌面预览 / 整理操作 / 设置 / 日志。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .. import resource_path
from ..core import organizer
from ..core.models import (
    APP_NAME,
    APP_VERSION,
    DesktopItem,
    Snapshot,
    normalize_key,
)
from ..core.service import AppService, DesktopState
from .dialogs import NameDialog, confirm
from .icons import ICON_MUTED, ICON_PRIMARY, make_icon
from .theme import apply_theme, palette
from .widgets import (
    ActionCard,
    Card,
    Chip,
    DesktopPreview,
    Divider,
    LogView,
    SettingRow,
    SchemeList,
    Toast,
    ToggleSwitch,
    repolish,
)


class MainWindow(QMainWindow):
    def __init__(self, service: AppService) -> None:
        super().__init__()
        self.service = service
        self.settings = service.settings
        self.theme = self.settings.theme if self.settings.theme in ("light", "dark") else "light"
        self.colors = palette(self.theme)
        self.state = DesktopState()
        self.snapshots: list[Snapshot] = []
        self.current_id: str | None = None
        self._compact = False
        self._busy = False

        self.setWindowTitle(APP_NAME)
        icon_path = resource_path("resources", "icons", "icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setMinimumSize(900, 620)
        self._restore_geometry()

        self._build_ui()
        self._wire_shortcuts()
        self.service.on_log = self._on_service_log
        self._reload(reload_state=True)
        self._apply_theme()
        self._log_startup()
        QTimer.singleShot(0, self._late_init)
    def _restore_geometry(self) -> None:
        screen = QGuiApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        width = self.settings.window_w
        height = self.settings.window_h
        if available:
            width = min(width, max(900, available.width() - 60))
            height = min(height, max(620, available.height() - 60))
        self.resize(width, height)

    def _tool_button(self, icon_name: str, tooltip: str, checkable: bool = False,
                     color: str = ICON_MUTED) -> QPushButton:
        button = QPushButton()
        button.setObjectName("ToolButton")
        button.setProperty("variant", "icon")
        button.setIcon(make_icon(icon_name, color, 18))
        button.setIconSize(QSize(18, 18))
        button.setFixedSize(34, 34)
        button.setToolTip(tooltip)
        button.setCheckable(checkable)
        button.setCursor(Qt.PointingHandCursor)
        return button

    def _ghost_button(self, text: str, icon_name: str | None = None) -> QPushButton:
        button = QPushButton(text)
        button.setProperty("variant", "ghost")
        button.setCursor(Qt.PointingHandCursor)
        if icon_name:
            button.setIcon(make_icon(icon_name, ICON_MUTED, 14))
            button.setIconSize(QSize(14, 14))
        return button

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_header())
        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFixedHeight(1)
        root_layout.addWidget(divider)

        self.body = QSplitter(Qt.Horizontal)
        self.body.setHandleWidth(8)
        self.body.setChildrenCollapsible(False)
        self.left_panel = self._build_left_panel()
        self.center_area = self._build_center()
        self.right_panel = self._build_right_panel()
        self.body.addWidget(self.left_panel)
        self.body.addWidget(self.center_area)
        self.body.addWidget(self.right_panel)
        self.body.setStretchFactor(0, 0)
        self.body.setStretchFactor(1, 1)
        self.body.setStretchFactor(2, 0)
        root_layout.addWidget(self.body, 1)
        root_layout.addWidget(self._build_status())

        self.setCentralWidget(root)
        self.root = root
        self.toast = Toast(root)
        self.toast.set_theme(self.theme)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(66)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(22, 10, 18, 10)
        layout.setSpacing(12)

        logo = QLabel()
        logo_path = resource_path("resources", "icons", "icon.png")
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path)).scaled(
                40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo.setPixmap(pixmap)
        logo.setFixedSize(40, 40)
        layout.addWidget(logo, 0, Qt.AlignVCenter)

        title = QLabel(APP_NAME)
        title.setObjectName("H1")
        layout.addWidget(title, 0, Qt.AlignVCenter)
        layout.addStretch(1)

        self.chip_pending = Chip("", "warn")
        self.chip_pending.hide()
        layout.addWidget(self.chip_pending, 0, Qt.AlignVCenter)

        self.chip_res = Chip("—")
        self.chip_count = Chip("—")
        self.chip_warn = Chip("自动排列已开启", "warn")
        self.chip_demo = Chip("演示模式", "warn")
        layout.addWidget(self.chip_res, 0, Qt.AlignVCenter)
        layout.addWidget(self.chip_count, 0, Qt.AlignVCenter)
        layout.addWidget(self.chip_warn, 0, Qt.AlignVCenter)
        layout.addWidget(self.chip_demo, 0, Qt.AlignVCenter)
        self.chip_warn.hide()
        self.chip_demo.setVisible(self.service.demo)

        layout.addSpacing(4)
        self.btn_left = self._tool_button("grid", "显示 / 隐藏方案库", checkable=True)
        self.btn_right = self._tool_button("sliders", "显示 / 隐藏操作面板", checkable=True)
        self.btn_left.setChecked(True)
        self.btn_right.setChecked(True)
        self.btn_theme = self._tool_button("moon", "切换深色 / 浅色主题")
        self.btn_refresh = self._tool_button("refresh", "重新读取桌面（F5）")
        for button in (self.btn_left, self.btn_right, self.btn_theme, self.btn_refresh):
            layout.addWidget(button, 0, Qt.AlignVCenter)
        return header

    def _build_left_panel(self) -> QWidget:
        panel = Card()
        panel.setMinimumWidth(264)
        panel.setMaximumWidth(348)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 10, 12)
        layout.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(6)
        title = QLabel("方案库")
        title.setObjectName("H2")
        head.addWidget(title)
        self.scheme_count = Chip("0")
        head.addWidget(self.scheme_count)
        head.addStretch(1)
        self.btn_scheme_menu = self._tool_button("more", "更多操作")
        head.addWidget(self.btn_scheme_menu)
        layout.addLayout(head)

        self.btn_snapshot = QPushButton("  快照当前桌面")
        self.btn_snapshot.setProperty("variant", "primary")
        self.btn_snapshot.setIcon(make_icon("camera", "#FFFFFF", 17))
        self.btn_snapshot.setIconSize(QSize(17, 17))
        self.btn_snapshot.setMinimumHeight(38)
        self.btn_snapshot.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_snapshot)

        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索方案")
        self.search.setClearButtonEnabled(True)
        self.search.addAction(make_icon("search", ICON_MUTED, 14), QLineEdit.LeadingPosition)
        layout.addWidget(self.search)

        self.scheme_list = SchemeList()
        layout.addWidget(self.scheme_list, 1)

        footer = QHBoxLayout()
        footer.setSpacing(4)
        self.btn_import = self._ghost_button("导入", "download")
        self.btn_export = self._ghost_button("导出", "upload")
        footer.addWidget(self.btn_import)
        footer.addWidget(self.btn_export)
        footer.addStretch(1)
        layout.addLayout(footer)
        return panel

    def _build_center(self) -> QWidget:
        container = QSplitter(Qt.Vertical)
        container.setHandleWidth(8)
        container.setChildrenCollapsible(False)

        preview_card = Card()
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)

        head = QWidget()
        head_layout = QHBoxLayout(head)
        head_layout.setContentsMargins(16, 12, 14, 2)
        head_layout.setSpacing(8)
        title = QLabel("桌面预览")
        title.setObjectName("H2")
        head_layout.addWidget(title)
        head_layout.addStretch(1)
        preview_layout.addWidget(head)

        canvas_wrap = QWidget()
        canvas_layout = QVBoxLayout(canvas_wrap)
        canvas_layout.setContentsMargins(10, 4, 10, 12)
        self.preview = DesktopPreview(self.colors)
        canvas_layout.addWidget(self.preview)
        preview_layout.addWidget(canvas_wrap, 1)
        container.addWidget(preview_card)

        log_card = Card()
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(0)
        log_head = QWidget()
        log_head_layout = QHBoxLayout(log_head)
        log_head_layout.setContentsMargins(16, 10, 12, 2)
        log_head_layout.setSpacing(8)
        log_title = QLabel("操作日志")
        log_title.setObjectName("H2")
        log_head_layout.addWidget(log_title)
        log_head_layout.addStretch(1)
        self.btn_log_clear = self._ghost_button("清空")
        self.btn_log_open = self._ghost_button("日志目录")
        log_head_layout.addWidget(self.btn_log_clear)
        log_head_layout.addWidget(self.btn_log_open)
        log_layout.addWidget(log_head)

        log_wrap = QWidget()
        log_wrap_layout = QVBoxLayout(log_wrap)
        log_wrap_layout.setContentsMargins(10, 4, 10, 10)
        self.log = LogView(self.colors, limit=self.settings.log_limit)
        log_wrap_layout.addWidget(self.log)
        log_layout.addWidget(log_wrap, 1)
        container.addWidget(log_card)

        container.setStretchFactor(0, 4)
        container.setStretchFactor(1, 1)
        container.setSizes([580, 200])
        self.center_splitter = container
        return container

    def _build_right_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(300)
        scroll.setMaximumWidth(376)
        scroll.viewport().setAutoFillBackground(False)

        container = QWidget()
        container.setAutoFillBackground(False)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 6, 10)
        layout.setSpacing(10)
        actions = Card()
        actions_layout = QVBoxLayout(actions)
        actions_layout.setContentsMargins(13, 13, 13, 13)
        actions_layout.setSpacing(7)
        head = QHBoxLayout()
        head.setSpacing(6)
        title = QLabel("整理操作")
        title.setObjectName("H2")
        head.addWidget(title)
        head.addStretch(1)
        actions_layout.addLayout(head)
        actions_layout.addSpacing(2)

        self.act_apply = ActionCard("play", "应用选中方案", "", "primary", "#FFFFFF")
        self.act_zone = ActionCard("tray", "新增图标移入待整理")
        self.act_tidy = ActionCard("folder", "一键整理文件")
        self.act_order = ActionCard("sort", "重排图标顺序")
        self.act_undo = ActionCard("undo", "撤销上次文件整理")
        for card in (self.act_apply, self.act_zone, self.act_tidy, self.act_order, self.act_undo):
            actions_layout.addWidget(card)
        layout.addWidget(actions)
        settings_card = Card()
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(13, 13, 13, 13)
        settings_layout.setSpacing(3)
        s_title = QLabel("设置")
        s_title.setObjectName("H2")
        settings_layout.addWidget(s_title)
        settings_layout.addSpacing(2)

        self.sw_dry = ToggleSwitch(self.settings.dry_run)
        self.sw_zone = ToggleSwitch(self.settings.apply_moves_new)
        self.sw_backup = ToggleSwitch(self.settings.auto_backup)
        self.sw_lock = ToggleSwitch(self.settings.lock_system)
        self.sw_shortcut = ToggleSwitch(self.settings.category_shortcuts)
        self.sw_exe = ToggleSwitch(self.settings.include_executables)

        settings_layout.addWidget(SettingRow("预演模式", self.sw_dry, "", "info"))
        settings_layout.addWidget(SettingRow("应用方案时收纳新增", self.sw_zone, "", "tray"))
        settings_layout.addWidget(SettingRow("变更前自动快照", self.sw_backup, "", "camera"))
        settings_layout.addWidget(SettingRow("锁定系统图标", self.sw_lock, "", "shield"))
        settings_layout.addWidget(Divider())
        settings_layout.addWidget(SettingRow("归类快捷方式", self.sw_shortcut, "", "app"))
        settings_layout.addWidget(SettingRow("归类可执行文件", self.sw_exe, "", "box"))

        self.combo_scope = QComboBox()
        self.combo_scope.addItems(["仅应用图标", "全部图标"])
        self.combo_scope.setCurrentIndex(0 if self.settings.order_scope == "apps" else 1)
        self.combo_scope.setFixedWidth(116)
        settings_layout.addWidget(SettingRow("排序范围", self.combo_scope, "", "grid"))

        self.combo_by = QComboBox()
        self.combo_by.addItems(["名称", "类型", "修改时间"])
        self.combo_by.setCurrentIndex({"name": 0, "type": 1, "mtime": 2}.get(self.settings.order_by, 0))
        self.combo_by.setFixedWidth(116)
        settings_layout.addWidget(SettingRow("排序依据", self.combo_by, "", "sort"))

        self.combo_dir = QComboBox()
        self.combo_dir.addItems(["按列排列", "按行排列"])
        self.combo_dir.setCurrentIndex(0 if self.settings.order_direction == "column" else 1)
        self.combo_dir.setFixedWidth(116)
        settings_layout.addWidget(SettingRow("排列方向", self.combo_dir, "", "list"))

        self.spin_zone = QSpinBox()
        self.spin_zone.setRange(160, 520)
        self.spin_zone.setSingleStep(8)
        self.spin_zone.setSuffix(" px")
        self.spin_zone.setValue(self.settings.tidy_zone_width)
        self.spin_zone.setFixedWidth(96)
        settings_layout.addWidget(SettingRow("待整理区宽度", self.spin_zone, "", "tray"))
        layout.addWidget(settings_card)
        layout.addStretch(1)

        scroll.setWidget(container)
        self.right_scroll = scroll
        return scroll

    def _build_status(self) -> QStatusBar:
        bar = QStatusBar()
        bar.setSizeGripEnabled(False)
        self.status_label = QLabel("正在连接桌面…")
        bar.addWidget(self.status_label, 1)
        self.btn_open_data = self._ghost_button("打开数据目录", "external")
        bar.addPermanentWidget(self.btn_open_data)
        version = QLabel(f"v{APP_VERSION}")
        version.setObjectName("MutedSmall")
        bar.addPermanentWidget(version)
        return bar
    def _wire_shortcuts(self) -> None:
        self.btn_snapshot.clicked.connect(self._snapshot_current)
        self.btn_refresh.clicked.connect(self._refresh_desktop)
        self.btn_theme.clicked.connect(self._toggle_theme)
        self.btn_left.toggled.connect(lambda checked: self._set_panel("left", checked))
        self.btn_right.toggled.connect(lambda checked: self._set_panel("right", checked))
        self.btn_scheme_menu.clicked.connect(self._show_more_menu)
        self.btn_import.clicked.connect(self._import_schemes)
        self.btn_export.clicked.connect(self._export_all)
        self.scheme_list.selected.connect(self._on_scheme_selected)
        self.scheme_list.activated.connect(self._apply_by_id)
        self.scheme_list.menu_requested.connect(self._show_scheme_menu)
        self.search.textChanged.connect(self.scheme_list.set_filter)

        self.act_apply.clicked.connect(self._apply_selected)
        self.act_zone.clicked.connect(self._move_new_to_zone)
        self.act_tidy.clicked.connect(self._tidy_files)
        self.act_order.clicked.connect(self._order_icons)
        self.act_undo.clicked.connect(self._undo_tidy)

        self.btn_log_clear.clicked.connect(self._clear_log)
        self.btn_log_open.clicked.connect(self._open_log_dir)
        self.btn_open_data.clicked.connect(self._open_data_dir)

        self.sw_dry.toggled.connect(lambda v: self._set_setting("dry_run", v))
        self.sw_zone.toggled.connect(lambda v: self._set_setting("apply_moves_new", v))
        self.sw_backup.toggled.connect(lambda v: self._set_setting("auto_backup", v))
        self.sw_lock.toggled.connect(lambda v: self._set_setting("lock_system", v))
        self.sw_shortcut.toggled.connect(lambda v: self._set_setting("category_shortcuts", v))
        self.sw_exe.toggled.connect(lambda v: self._set_setting("include_executables", v))
        self.combo_scope.currentIndexChanged.connect(
            lambda i: self._set_setting("order_scope", "apps" if i == 0 else "all")
        )
        self.combo_by.currentIndexChanged.connect(
            lambda i: self._set_setting("order_by", ["name", "type", "mtime"][max(0, min(2, i))])
        )
        self.combo_dir.currentIndexChanged.connect(
            lambda i: self._set_setting("order_direction", "column" if i == 0 else "row")
        )
        self.spin_zone.valueChanged.connect(self._on_zone_width)

        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._snapshot_current)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self._refresh_desktop)
        QShortcut(QKeySequence("F5"), self, activated=self._refresh_desktop)
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self._undo_tidy)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self._export_all)
        QShortcut(QKeySequence("Ctrl+I"), self, activated=self._import_schemes)
        for index in range(9):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{index + 1}"), self)
            shortcut.activated.connect(lambda i=index: self._apply_index(i))
    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app:
            apply_theme(app, self.theme)
        self.colors = palette(self.theme)
        self.preview.apply_theme(self.colors)
        self.log.apply_theme(self.colors)
        self.toast.set_theme(self.theme)
        for toggle in self.findChildren(ToggleSwitch):
            toggle.apply_theme(self.colors)
        self.btn_theme.setIcon(make_icon("sun" if self.theme == "dark" else "moon", ICON_MUTED, 18))
        self.btn_theme.setToolTip("切换为浅色主题" if self.theme == "dark" else "切换为深色主题")
        self.update()

    def _toggle_theme(self) -> None:
        self.theme = "dark" if self.theme == "light" else "light"
        self.settings.theme = self.theme
        self.service.save_settings(self.settings)
        self._apply_theme()
    def _reload(self, select_id: str | None = None, reload_state: bool = True) -> None:
        self.snapshots = self.service.snapshots
        ids = {s.id for s in self.snapshots}
        active = self.service.store.active_id
        if select_id and select_id in ids:
            self.current_id = select_id
        elif self.current_id not in ids:
            self.current_id = active if active in ids else (self.snapshots[0].id if self.snapshots else None)
        if reload_state:
            self.state = self.service.refresh_state()
        self.scheme_list.set_data(self.snapshots, active, self.current_id)
        self._update_all()

    def _current_snapshot(self) -> Snapshot | None:
        for snapshot in self.snapshots:
            if snapshot.id == self.current_id:
                return snapshot
        return None

    def _pending_items(self) -> list[DesktopItem]:
        snapshot = self._current_snapshot()
        if not snapshot or not self.state.available:
            return []
        keys = {normalize_key(i.name) for i in snapshot.items}
        zone_left = self.state.canvas_w - self.settings.tidy_zone_width - self.state.spacing[0] * 0.5
        return [
            item for item in self.state.items
            if item.key not in keys and not item.system and item.x < zone_left
        ]

    def _update_all(self) -> None:
        self._update_header()
        self._update_preview()
        self._update_stats()
        self._update_actions()

    def _update_header(self) -> None:
        available = self.state.available
        if available:
            self.chip_res.setText(f"{self.state.canvas_w} × {self.state.canvas_h}")
            self.chip_count.setText(f"{len(self.state.items)} 个图标")
            self.chip_warn.setVisible(self.state.auto_arrange)
            self.status_label.setText(f"{len(self.state.items)} 个图标 · {len(self.snapshots)} 套方案")
        else:
            self.chip_res.setText("桌面不可用")
            self.chip_count.setText("—")
            self.chip_warn.hide()
            self.status_label.setText(f"无法读取桌面：{self.state.error}")

    def _update_preview(self) -> None:
        snapshot = self._current_snapshot()
        self.preview.set_available(self.state.available)
        self.preview.set_data(
            self.state.items if self.state.available else [],
            (self.state.canvas_w or 1440, self.state.canvas_h or 900),
            self.state.spacing,
            self.settings.tidy_zone_width,
            snapshot,
        )
        pending = self._pending_items()
        self.chip_pending.setVisible(bool(pending))
        self.chip_pending.setText(f"{len(pending)} 个待整理")

    def _update_stats(self) -> None:
        self.scheme_count.setText(str(len(self.snapshots)))

    def _update_actions(self) -> None:
        snapshot = self._current_snapshot()
        available = self.state.available
        has_scheme = snapshot is not None
        self.act_apply.setEnabled(available and has_scheme)
        self.act_zone.setEnabled(available and has_scheme)
        self.act_tidy.setEnabled(available)
        self.act_order.setEnabled(available)
        self.act_undo.setEnabled(bool(self.service.store.last_journal()))
    def _set_panel(self, which: str, visible: bool) -> None:
        if which == "left":
            panel, button = self.left_panel, self.btn_left
        else:
            panel, button = self.right_panel, self.btn_right
        if button.isChecked() != visible:
            button.blockSignals(True)
            button.setChecked(visible)
            button.blockSignals(False)
        panel.setVisible(visible)
        if visible and self._compact:
            other = "right" if which == "left" else "left"
            other_panel, other_button = (
                (self.right_panel, self.btn_right) if other == "right" else (self.left_panel, self.btn_left)
            )
            if other_panel.isVisible():
                other_panel.setVisible(False)
                other_button.blockSignals(True)
                other_button.setChecked(False)
                other_button.blockSignals(False)
        self._apply_sizes()

    def _apply_sizes(self) -> None:
        if not hasattr(self, "body"):
            return
        total = max(760, self.body.width())
        left = 286 if self.left_panel.isVisible() else 0
        right = 330 if self.right_panel.isVisible() else 0
        center = max(380, total - left - right - 16)
        self.body.setSizes([left, center, right])

    def _adapt_layout(self) -> None:
        width = self.width()
        compact = width < 1040
        if compact != self._compact:
            self._compact = compact
            if compact:
                self.left_panel.setVisible(False)
                self.right_panel.setVisible(False)
                for button in (self.btn_left, self.btn_right):
                    button.blockSignals(True)
                    button.setChecked(False)
                    button.blockSignals(False)
            else:
                for panel, button in ((self.left_panel, self.btn_left), (self.right_panel, self.btn_right)):
                    panel.setVisible(True)
                    button.blockSignals(True)
                    button.setChecked(True)
                    button.blockSignals(False)
            self._apply_sizes()
        self.chip_res.setVisible(width >= 1100)
        self.chip_count.setVisible(width >= 1240)
        self._style_panel_toggles(compact)
        if hasattr(self, "toast"):
            self.toast._reposition()

    def _style_panel_toggles(self, compact: bool) -> None:
        state = "true" if compact else "false"
        if self.btn_left.property("expanded") == state:
            return
        for button, text, icon_name in (
            (self.btn_left, "方案", "grid"),
            (self.btn_right, "操作", "sliders"),
        ):
            button.setProperty("expanded", state)
            if compact:
                button.setText(text)
                button.setIcon(QIcon())
                button.setIconSize(QSize(0, 0))
                button.setFixedWidth(62)
            else:
                button.setText("")
                button.setIcon(make_icon(icon_name, ICON_MUTED, 18))
                button.setIconSize(QSize(18, 18))
                button.setFixedWidth(34)
            repolish(button)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._adapt_layout()

    def _late_init(self) -> None:
        self._adapt_layout()
        self._apply_sizes()
    def _on_service_log(self, level: str, message: str) -> None:
        if hasattr(self, "log"):
            self.log.append_entry(level, message)

    def _log_startup(self) -> None:
        self.log.append_entry("action", "星月已启动，正在读取桌面布局")
        if self.state.available:
            self.log.append_entry(
                "info",
                f"桌面 {self.state.canvas_w}×{self.state.canvas_h} · {len(self.state.items)} 个图标 · "
                f"{self.state.dpi / 96 * 100:.0f}% 缩放 · 网格 {self.state.spacing[0]}×{self.state.spacing[1]}",
            )
            if self.state.auto_arrange:
                self.log.append_entry("warn", "桌面「自动排列图标」已开启")
        else:
            self.log.append_entry("error", f"无法读取桌面：{self.state.error}")
        if self.snapshots:
            self.log.append_entry("info", f"已加载 {len(self.snapshots)} 套方案，选中「{self._current_snapshot().name if self._current_snapshot() else '—'}」")
        else:
            self.log.append_entry("info", "尚未创建方案")

    def _clear_log(self) -> None:
        self.log.clear_entries()
        self.log.append_entry("info", "日志面板已清空")

    def _open_log_dir(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.service.store.logs_dir)))

    def _open_data_dir(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.service.store.root)))

    def _refresh_desktop(self) -> None:
        if self._busy:
            return
        self._reload()
        if self.state.available:
            self.log.append_entry("info", f"已重新读取桌面 · {len(self.state.items)} 个图标")
            self.toast.show_message("桌面已刷新", "info", 1600)
        else:
            self.toast.show_message("无法读取桌面，请确认资源管理器正在运行", "error", 3600)
    def _set_busy(self, busy: bool, message: str = "") -> None:
        self._busy = busy
        if busy:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.status_label.setText(message or "正在处理…")
            QApplication.processEvents()
        else:
            QApplication.restoreOverrideCursor()

    def _snapshot_current(self) -> None:
        if self._busy:
            return
        if not self.state.available:
            self.toast.show_message("桌面不可用，无法创建快照", "error")
            return
        default = self.service.next_scheme_name()
        name = NameDialog.ask(self, "快照当前桌面", "", default, "保存快照")
        if not name:
            return
        self._set_busy(True, "正在记录图标坐标…")
        try:
            snapshot = self.service.create_snapshot(name)
        finally:
            self._set_busy(False)
        if snapshot:
            self._reload(select_id=snapshot.id)
            self.toast.show_message(f"已保存「{snapshot.name}」· {len(snapshot.items)} 个图标", "ok")
        else:
            self.toast.show_message("快照失败，请查看日志", "error")

    def _apply_selected(self) -> None:
        snapshot = self._current_snapshot()
        if snapshot is None:
            self.toast.show_message("请先选择一套方案", "warn")
            return
        self._run_apply(snapshot)

    def _apply_by_id(self, snapshot_id: str) -> None:
        self.current_id = snapshot_id
        self.scheme_list.select(snapshot_id)
        snapshot = self._current_snapshot()
        if snapshot:
            self._run_apply(snapshot)

    def _apply_index(self, index: int) -> None:
        if 0 <= index < len(self.snapshots):
            self._apply_by_id(self.snapshots[index].id)

    def _run_apply(self, snapshot: Snapshot) -> None:
        if self._busy:
            return
        if self.state.auto_arrange:
            accepted, _ = confirm(
                self,
                "关闭自动排列？",
                "应用方案需要关闭桌面「自动排列图标」，关闭后可在桌面右键重新开启。",
                confirm_text="继续应用",
            )
            if not accepted:
                return
        self._set_busy(True, f"正在应用「{snapshot.name}」…")
        try:
            report = self.service.apply_snapshot(snapshot)
        finally:
            self._set_busy(False)
        self._emit_report(report)
        if report.ok:
            self._reload()
            self.toast.show_message(f"已应用「{snapshot.name}」· 移动 {report.moved} 个图标", "ok")
        else:
            self.toast.show_message("应用失败，请查看日志", "error")

    def _move_new_to_zone(self) -> None:
        if self._busy:
            return
        self._set_busy(True, "正在识别新增图标…")
        try:
            report = self.service.move_new_to_zone()
        finally:
            self._set_busy(False)
        self._emit_report(report)
        self._reload()
        if report.moved:
            self.toast.show_message(f"已将 {report.moved} 个图标移入待整理区", "ok")
        elif report.ok:
            self.toast.show_message("没有发现新增图标", "info")
        else:
            self.toast.show_message("操作未完成，请查看日志", "warn")

    def _tidy_files(self) -> None:
        if self._busy:
            return
        if self.service.demo:
            self.log.append_entry("info", "演示模式：一键整理仅展示流程，不会移动真实文件")
            self.toast.show_message("演示模式：不执行真实文件操作", "info")
            return
        settings = self.settings
        try:
            plan = organizer.plan_tidy(self.service.desktop_dir, settings)
        except OSError as exc:
            self.toast.show_message(f"无法读取桌面目录：{exc}", "error")
            return
        if not plan.moves:
            self.log.append_entry("ok", "桌面已经很整洁，没有需要归类的文件")
            self.toast.show_message("没有需要归类的文件", "info")
            return

        details = []
        for move in plan.moves[:14]:
            details.append(f"{move.src.name}  →  {move.dst.parent.name}/")
        if len(plan.moves) > 14:
            details.append(f"… 其余 {len(plan.moves) - 14} 个文件")
        if plan.notes:
            details.append("")
            details.extend(plan.notes)
        message = (
            f"将把 {len(plan.moves)} 个文件移动到桌面上的 {len(plan.folders)} 个分类文件夹"
            f"（{', '.join(plan.folders)}），共 {organizer.pretty_bytes(plan.total_bytes)}。\n"
            "文件只会被归类，不会被删除；整理后可通过「撤销」还原。"
        )
        if settings.dry_run:
            self._set_busy(True, "正在预演整理计划…")
            try:
                report = self.service.tidy_files(dry_run=True)
            finally:
                self._set_busy(False)
            self._emit_report(report)
            self.toast.show_message(f"预演完成 · {len(plan.moves)} 个文件待归类", "info")
            return

        accepted, backup_checked = confirm(
            self,
            f"确认整理 {len(plan.moves)} 个文件？",
            message,
            "\n".join(details),
            "开始整理",
            danger=False,
            checkbox_text="整理前记录桌面快照",
            checked=settings.auto_backup,
        )
        if not accepted:
            return
        self._set_busy(True, "正在归类桌面文件…")
        try:
            report = self.service.tidy_files(dry_run=False, auto_backup=backup_checked)
        finally:
            self._set_busy(False)
        self._emit_report(report)
        self._reload()
        if report.moved:
            self.toast.show_message(f"已归类 {report.moved} 个文件", "ok")
        elif report.failed:
            self.toast.show_message("部分文件移动失败，请查看日志", "error")
        else:
            self.toast.show_message("没有文件被移动", "warn")

    def _order_icons(self) -> None:
        if self._busy:
            return
        if self.state.auto_arrange:
            accepted, _ = confirm(
                self,
                "关闭自动排列？",
                "重排图标需要关闭桌面「自动排列图标」，关闭后可在桌面右键重新开启。",
                confirm_text="继续排序",
            )
            if not accepted:
                return
        self._set_busy(True, "正在重排图标…")
        try:
            report = self.service.order_icons()
        finally:
            self._set_busy(False)
        self._emit_report(report)
        self._reload()
        if report.moved:
            self.toast.show_message(f"已重排 {report.moved} 个图标", "ok")
        else:
            self.toast.show_message("没有可重排的图标", "info")

    def _undo_tidy(self) -> None:
        if self._busy:
            return
        journal = self.service.store.last_journal()
        if not journal:
            self.toast.show_message("没有可撤销的整理记录", "info")
            return
        moves = journal.get("moves", [])
        details = []
        for move in moves[:12]:
            if not isinstance(move, dict):
                continue
            src = Path(str(move.get("src", ""))).name
            dst = Path(str(move.get("dst", "")))
            details.append(f"{dst.parent.name}/{dst.name}  →  {src}")
        if len(moves) > 12:
            details.append(f"… 其余 {len(moves) - 12} 个文件")
        accepted, _ = confirm(
            self,
            "撤销上次整理？",
            f"将把 {len(moves)} 个文件移回原来的桌面位置。若文件已被移动或删除，将自动跳过。",
            "\n".join(details),
            "确认撤销",
            danger=True,
        )
        if not accepted:
            return
        self._set_busy(True, "正在还原文件…")
        try:
            report = self.service.undo_last_tidy()
        finally:
            self._set_busy(False)
        self._emit_report(report)
        self._reload()
        self.toast.show_message(f"已还原 {report.moved} 个文件" if report.moved else "没有文件被还原",
                                "ok" if report.moved else "warn")
    def _on_scheme_selected(self, snapshot_id: str) -> None:
        self.current_id = snapshot_id
        self._update_preview()
        self._update_stats()
        self._update_actions()

    def _show_scheme_menu(self, snapshot_id: str, pos: QPoint) -> None:
        snapshot = next((s for s in self.snapshots if s.id == snapshot_id), None)
        if not snapshot:
            return
        menu = QMenu(self)
        menu.addAction(make_icon("play", ICON_PRIMARY, 16), "应用这套方案",
                       lambda: self._apply_by_id(snapshot_id))
        menu.addAction(make_icon("pencil", ICON_MUTED, 16), "重命名",
                       lambda: self._rename_scheme(snapshot_id))
        menu.addAction(make_icon("copy", ICON_MUTED, 16), "创建副本",
                       lambda: self._duplicate_scheme(snapshot_id))
        menu.addAction(make_icon("download", ICON_MUTED, 16), "导出这套方案",
                       lambda: self._export_one(snapshot_id))
        menu.addSeparator()
        menu.addAction(make_icon("trash", "#D14B4B", 16), "删除方案",
                       lambda: self._delete_scheme(snapshot_id))
        menu.exec(pos)

    def _show_more_menu(self) -> None:
        menu = QMenu(self)
        menu.addAction(make_icon("camera", ICON_MUTED, 16), "快照当前桌面", self._snapshot_current)
        menu.addSeparator()
        menu.addAction(make_icon("download", ICON_MUTED, 16), "导入方案…", self._import_schemes)
        menu.addAction(make_icon("upload", ICON_MUTED, 16), "导出全部方案…", self._export_all)
        menu.addSeparator()
        menu.addAction(make_icon("external", ICON_MUTED, 16), "打开数据目录", self._open_data_dir)
        menu.addAction(make_icon("list", ICON_MUTED, 16), "快捷键说明", self._show_shortcuts)
        menu.addAction(make_icon("info", ICON_MUTED, 16), "关于星月", self._show_about)
        menu.exec(self.btn_scheme_menu.mapToGlobal(QPoint(0, self.btn_scheme_menu.height() + 4)))

    def _rename_scheme(self, snapshot_id: str) -> None:
        snapshot = next((s for s in self.snapshots if s.id == snapshot_id), None)
        if not snapshot:
            return
        name = NameDialog.ask(self, "重命名方案", "", snapshot.name, "保存")
        if not name:
            return
        self.service.rename_snapshot(snapshot_id, name)
        self._reload(select_id=snapshot_id)
        self.toast.show_message("方案已重命名", "ok")

    def _duplicate_scheme(self, snapshot_id: str) -> None:
        snapshot = next((s for s in self.snapshots if s.id == snapshot_id), None)
        if not snapshot:
            return
        name = NameDialog.ask(self, "创建副本", "", f"{snapshot.name} 副本", "创建")
        if not name:
            return
        copy = self.service.duplicate_snapshot(snapshot_id, name)
        if copy:
            self._reload(select_id=copy.id)
            self.toast.show_message(f"已创建「{copy.name}」", "ok")

    def _delete_scheme(self, snapshot_id: str) -> None:
        snapshot = next((s for s in self.snapshots if s.id == snapshot_id), None)
        if not snapshot:
            return
        accepted, _ = confirm(
            self,
            "删除这套方案？",
            f"「{snapshot.name}」记录了 {len(snapshot.items)} 个图标的坐标，删除后无法恢复。\n"
            "桌面上的图标本身不会受到影响。",
            confirm_text="删除方案",
            danger=True,
        )
        if not accepted:
            return
        self.service.delete_snapshot(snapshot_id)
        self.current_id = None
        self._reload()
        self.toast.show_message("方案已删除", "info")

    def _export_all(self) -> None:
        if not self.snapshots:
            self.toast.show_message("还没有可导出的方案", "info")
            return
        default = str(Path.home() / f"星月桌面方案-{datetime.now():%Y%m%d}.json")
        path, _ = QFileDialog.getSaveFileName(self, "导出全部方案", default, "方案文件 (*.json)")
        if not path:
            return
        try:
            count = self.service.export_snapshots([s.id for s in self.snapshots], Path(path))
            self.toast.show_message(f"已导出 {count} 套方案", "ok")
        except OSError as exc:
            self.toast.show_message(f"导出失败：{exc}", "error")

    def _export_one(self, snapshot_id: str) -> None:
        snapshot = next((s for s in self.snapshots if s.id == snapshot_id), None)
        if not snapshot:
            return
        safe_name = "".join(c for c in snapshot.name if c not in '\\/:*?"<>|').strip() or "方案"
        default = str(Path.home() / f"星月-{safe_name}.json")
        path, _ = QFileDialog.getSaveFileName(self, "导出方案", default, "方案文件 (*.json)")
        if not path:
            return
        try:
            self.service.export_snapshots([snapshot_id], Path(path))
            self.toast.show_message("方案已导出", "ok")
        except OSError as exc:
            self.toast.show_message(f"导出失败：{exc}", "error")

    def _import_schemes(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "导入方案", str(Path.home()), "方案文件 (*.json)")
        if not path:
            return
        try:
            imported = self.service.import_snapshots(Path(path))
        except OSError as exc:
            self.toast.show_message(f"导入失败：{exc}", "error")
            return
        if imported:
            self._reload(select_id=imported[0].id)
            self.toast.show_message(f"已导入 {len(imported)} 套方案", "ok")
        else:
            self.toast.show_message("文件中没有可导入的方案", "warn")

    def _show_shortcuts(self) -> None:
        QMessageBox.information(
            self,
            "快捷键",
            "Ctrl + N    快照当前桌面\n"
            "Ctrl + 1…9  应用第 1…9 套方案\n"
            "F5 / Ctrl+R 重新读取桌面\n"
            "Ctrl + Z    撤销上次文件整理\n"
            "Ctrl + E    导出全部方案\n"
            "Ctrl + I    导入方案",
        )

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            f"关于 {APP_NAME}",
            f"<b>{APP_NAME}</b> v{APP_VERSION}<br><br>"
            f"数据目录：<br>{self.service.store.root}",
        )
    def _set_setting(self, key: str, value) -> None:
        setattr(self.settings, key, value)
        self.service.save_settings(self.settings)
        if key == "dry_run":
            self.log.append_entry("info", "预演模式已开启：整理操作只生成计划，不移动文件"
                                  if value else "预演模式已关闭：整理操作将实际移动文件")
        if key in ("order_scope", "order_by", "order_direction", "lock_system"):
            self._update_preview()

    def _on_zone_width(self, value: int) -> None:
        self.settings.tidy_zone_width = int(value)
        self.service.save_settings(self.settings)
        self._update_preview()
    def _emit_report(self, report) -> None:
        if report is None:
            return
        for level, message in report.lines:
            self.log.append_entry(level, message)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._busy:
            self.toast.show_message("正在处理，请稍候", "warn", 1800)
            event.ignore()
            return
        try:
            self.settings.window_w = max(900, self.width())
            self.settings.window_h = max(620, self.height())
            self.service.save_settings(self.settings)
        except Exception:
            pass
        super().closeEvent(event)
