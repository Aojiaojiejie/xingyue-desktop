"""数据模型与常量：桌面图标、快照方案、设置项、操作报告。"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Iterable

APP_NAME = "星月-桌面整理"
APP_ID = "XingYueDesktop"
APP_VERSION = "1.0.0"

# 预览面板中各类图标使用的色板（与主题无关，保证辨识度）
KIND_COLORS: dict[str, str] = {
    "app": "#5B6BE8",
    "folder": "#E0A93F",
    "image": "#35B08A",
    "doc": "#4C8FDB",
    "sheet": "#2FA36B",
    "slide": "#E07A4F",
    "archive": "#8B6FD6",
    "installer": "#D9704E",
    "media": "#D95C8A",
    "code": "#3FA8BE",
    "system": "#7C8698",
    "other": "#8A93A8",
}

KIND_LABELS: dict[str, str] = {
    "app": "应用",
    "folder": "文件夹",
    "image": "图片",
    "doc": "文档",
    "sheet": "表格",
    "slide": "演示",
    "archive": "压缩包",
    "installer": "安装包",
    "media": "音视频",
    "code": "代码",
    "system": "系统",
    "other": "其他",
}

# Windows 桌面上的系统级图标（默认锁定，不参与自动排序）
SYSTEM_ICON_NAMES: set[str] = {
    "此电脑", "我的电脑", "回收站", "网络", "控制面板", "用户文件夹",
    "administrator", "公用", "public", "users", "this pc", "my computer",
    "recycle bin", "network", "control panel", "user's files",
}

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".tif", ".tiff", ".heic", ".ico", ".raw"}
DOC_EXT = {".doc", ".docx", ".pdf", ".txt", ".md", ".rtf", ".odt", ".wps", ".pages", ".epub"}
SHEET_EXT = {".xls", ".xlsx", ".csv", ".tsv", ".ods", ".et"}
SLIDE_EXT = {".ppt", ".pptx", ".key", ".dps", ".pps"}
ARCHIVE_EXT = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"}
INSTALLER_EXT = {".exe", ".msi", ".msix", ".appx"}
MEDIA_EXT = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}
CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".html", ".css", ".scss", ".java", ".c", ".cpp", ".h",
            ".cs", ".go", ".rs", ".sh", ".bat", ".ps1", ".sql", ".yml", ".yaml", ".toml", ".ini", ".vue"}
SHORTCUT_EXT = {".lnk", ".url"}
APP_EXT = SHORTCUT_EXT | {".exe", ".appref-ms"}

_EXT_KIND: dict[str, str] = {}
for _exts, _kind in (
    (IMAGE_EXT, "image"),
    (DOC_EXT, "doc"),
    (SHEET_EXT, "sheet"),
    (SLIDE_EXT, "slide"),
    (ARCHIVE_EXT, "archive"),
    (INSTALLER_EXT, "installer"),
    (MEDIA_EXT, "media"),
    (CODE_EXT, "code"),
    (SHORTCUT_EXT, "app"),
):
    for _e in _exts:
        _EXT_KIND[_e] = _kind


def kind_for_suffix(suffix: str, is_dir: bool = False) -> str:
    if is_dir:
        return "folder"
    return _EXT_KIND.get(suffix.lower(), "other")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def pretty_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or "—"
    today = datetime.now().date()
    if dt.date() == today:
        return dt.strftime("今天 %H:%M")
    if dt.year == today.year:
        return dt.strftime("%m-%d %H:%M")
    return dt.strftime("%Y-%m-%d %H:%M")


def normalize_key(name: str) -> str:
    """用于名称匹配的归一化键：去空格、去常见后缀、忽略大小写。"""
    s = (name or "").strip().casefold()
    for ext in (".lnk", ".url", ".exe", ".appref-ms"):
        if s.endswith(ext):
            s = s[: -len(ext)]
            break
    return re.sub(r"\s+", "", s)


def display_stem(filename: str) -> str:
    """资源管理器隐藏已知扩展名时显示的标签。"""
    if "." not in filename:
        return filename
    stem, dot, ext = filename.rpartition(".")
    if not stem:
        return filename
    if f".{ext.lower()}" in _EXT_KIND:
        return stem
    return filename


_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def is_valid_id(value: str) -> bool:
    return bool(_ID_PATTERN.fullmatch(str(value or "")))


def new_id(prefix: str = "s") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def is_system_icon(name: str) -> bool:
    return (name or "").strip().casefold() in SYSTEM_ICON_NAMES


@dataclass
class DesktopItem:
    """桌面列表视图中的一个图标（坐标为列表视图客户区像素）。"""

    index: int
    name: str
    x: int
    y: int
    kind: str = "other"
    path: str | None = None
    is_dir: bool = False

    @property
    def key(self) -> str:
        return normalize_key(self.name)

    @property
    def system(self) -> bool:
        return is_system_icon(self.name)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SnapshotItem:
    name: str
    x: int
    y: int
    kind: str = "other"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SnapshotItem":
        return cls(
            name=str(data.get("name", "")),
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            kind=str(data.get("kind", "other")),
        )


@dataclass
class Snapshot:

    id: str
    name: str
    created_at: str
    desktop_w: int
    desktop_h: int
    items: list[SnapshotItem] = field(default_factory=list)
    spacing: tuple[int, int] = (96, 96)
    dpi: int = 96
    auto: bool = False
    note: str = ""

    @property
    def cover_count(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["spacing"] = list(self.spacing)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Snapshot":
        spacing = data.get("spacing") or [96, 96]
        try:
            spacing_t = (int(spacing[0]), int(spacing[1]))
        except (TypeError, ValueError, IndexError):
            spacing_t = (96, 96)
        raw_id = str(data.get("id") or "")
        snapshot_id = raw_id if is_valid_id(raw_id) else new_id("s")
        return cls(
            id=snapshot_id,
            name=str(data.get("name") or "未命名方案"),
            created_at=str(data.get("created_at") or now_iso()),
            desktop_w=int(data.get("desktop_w") or 0),
            desktop_h=int(data.get("desktop_h") or 0),
            items=[SnapshotItem.from_dict(i) for i in data.get("items", []) if isinstance(i, dict)],
            spacing=spacing_t,
            dpi=int(data.get("dpi") or 96),
            auto=bool(data.get("auto", False)),
            note=str(data.get("note", "")),
        )


@dataclass
class Settings:
    theme: str = "light"
    tidy_zone_width: int = 272
    tidy_zone_margin: int = 18
    zone_columns: int = 2
    lock_system: bool = True
    auto_backup: bool = True
    apply_moves_new: bool = True
    confirm_destructive: bool = True
    order_scope: str = "apps"          # apps | all
    order_by: str = "name"             # name | type | mtime
    order_direction: str = "column"    # column | row
    category_shortcuts: bool = False
    include_executables: bool = False
    tidy_unknown: bool = False
    skip_hidden: bool = True
    dry_run: bool = False
    log_limit: int = 600
    window_w: int = 1320
    window_h: int = 860
    demo_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Settings":
        s = cls()
        if not isinstance(data, dict):
            return s
        for key, value in data.items():
            if not hasattr(s, key):
                continue
            current = getattr(s, key)
            try:
                if isinstance(current, bool):
                    setattr(s, key, bool(value))
                elif isinstance(current, int):
                    setattr(s, key, int(value))
                elif isinstance(current, str):
                    setattr(s, key, str(value))
            except (TypeError, ValueError):
                continue
        s.tidy_zone_width = max(160, min(520, s.tidy_zone_width))
        s.tidy_zone_margin = max(0, min(80, s.tidy_zone_margin))
        s.zone_columns = max(1, min(4, s.zone_columns))
        s.log_limit = max(100, min(3000, s.log_limit))
        s.window_w = max(900, min(5000, s.window_w))
        s.window_h = max(600, min(4000, s.window_h))
        if s.theme not in ("light", "dark"):
            s.theme = "light"
        if s.order_by not in ("name", "type", "mtime"):
            s.order_by = "name"
        if s.order_direction not in ("column", "row"):
            s.order_direction = "column"
        if s.order_scope not in ("apps", "all"):
            s.order_scope = "apps"
        return s


@dataclass
class Report:
    title: str
    ok: bool = True
    moved: int = 0
    skipped: int = 0
    failed: int = 0
    lines: list[tuple[str, str]] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)

    def add(self, message: str, level: str = "info") -> None:
        self.lines.append((level, message))

    @property
    def summary(self) -> str:
        return f"{self.title}：移动 {self.moved}，跳过 {self.skipped}，失败 {self.failed}"


def total(items: Iterable[DesktopItem]) -> int:
    return sum(1 for _ in items)
