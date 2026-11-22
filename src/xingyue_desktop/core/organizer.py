"""整理算法：文件归类、待整理区排布、应用图标排序、快照坐标缩放。

本模块保持纯函数式（除文件系统查询外不产生副作用），便于单元测试与预演。
"""

from __future__ import annotations

import locale
import math
import re
from dataclasses import dataclass
from pathlib import Path

from .desktop_files import EntryInfo, scan_desktop_files
from .models import (
    ARCHIVE_EXT,
    CODE_EXT,
    DOC_EXT,
    IMAGE_EXT,
    INSTALLER_EXT,
    MEDIA_EXT,
    SHORTCUT_EXT,
    SLIDE_EXT,
    SHEET_EXT,
    DesktopItem,
    Settings,
    Snapshot,
)

CATEGORY_ORDER = ["图片", "文档", "表格", "演示", "压缩包", "安装包", "音视频", "代码", "其他"]
CATEGORY_FOLDERS = {
    "图片": "图片",
    "文档": "文档",
    "表格": "表格",
    "演示": "演示文稿",
    "压缩包": "压缩包",
    "安装包": "安装包",
    "音视频": "音视频",
    "代码": "代码",
    "其他": "其他",
}

_CATEGORY_EXT: dict[str, str] = {}
for _exts, _cat in (
    (IMAGE_EXT, "图片"),
    (DOC_EXT, "文档"),
    (SHEET_EXT, "表格"),
    (SLIDE_EXT, "演示"),
    (ARCHIVE_EXT, "压缩包"),
    (INSTALLER_EXT, "安装包"),
    (MEDIA_EXT, "音视频"),
    (CODE_EXT, "代码"),
):
    for _e in _exts:
        _CATEGORY_EXT[_e] = _cat

KIND_RANK = {
    "app": 0,
    "installer": 1,
    "folder": 2,
    "doc": 3,
    "sheet": 4,
    "slide": 5,
    "image": 6,
    "media": 7,
    "archive": 8,
    "code": 9,
    "other": 10,
    "system": 11,
}

try:  # 使用系统区域设置做拼音/笔画排序
    locale.setlocale(locale.LC_COLLATE, "")
except locale.Error:  # pragma: no cover
    pass


def _collate(text: str) -> str:
    try:
        return locale.strxfrm(text)
    except (ValueError, TypeError):  # pragma: no cover
        return text.casefold()


def natural_key(name: str) -> list[tuple[int, object]]:
    """自然排序键：数字按数值比较，文本按系统区域排序（中文近似拼音）。"""
    key: list[tuple[int, object]] = []
    for part in re.split(r"(\d+)", name or ""):
        if not part:
            continue
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, _collate(part.casefold())))
    return key


def category_for_suffix(suffix: str) -> str | None:
    return _CATEGORY_EXT.get(suffix.lower())


@dataclass
class MovePlan:
    src: Path
    dst: Path
    category: str
    size: int = 0

    @property
    def name(self) -> str:
        return self.src.name


@dataclass
class TidyPlan:
    moves: list[MovePlan]
    notes: list[str]
    counts: dict[str, int]
    total_bytes: int = 0

    @property
    def folders(self) -> list[str]:
        return [c for c in CATEGORY_ORDER if self.counts.get(c)]


def unique_target(target: Path, reserved: set[Path] | None = None) -> Path:
    reserved = reserved or set()
    if not target.exists() and target not in reserved:
        return target
    stem, suffix = target.stem, target.suffix
    index = 2
    while True:
        candidate = target.with_name(f"{stem} ({index}){suffix}")
        if not candidate.exists() and candidate not in reserved:
            return candidate
        index += 1
        if index > 9999:  # 极端兜底，避免死循环
            return target.with_name(f"{stem} ({index}){suffix}")


def plan_tidy(root: Path, settings: Settings) -> TidyPlan:
    """按扩展名把桌面文件归类到对应文件夹，返回可预演的移动计划。"""
    moves: list[MovePlan] = []
    notes: list[str] = []
    counts: dict[str, int] = {}
    reserved: set[Path] = set()
    total_bytes = 0
    skipped_hidden = 0
    skipped_unknown = 0
    skipped_shortcut = 0
    skipped_exe = 0

    for info in scan_desktop_files(root):
        if info.is_dir:
            continue
        if info.hidden and settings.skip_hidden:
            skipped_hidden += 1
            continue
        suffix = info.suffix.lower()
        if suffix in SHORTCUT_EXT and not settings.category_shortcuts:
            skipped_shortcut += 1
            continue
        if suffix in INSTALLER_EXT and not settings.include_executables:
            skipped_exe += 1
            continue
        category = category_for_suffix(suffix)
        if category is None:
            if not settings.tidy_unknown:
                skipped_unknown += 1
                continue
            category = "其他"
        folder_name = CATEGORY_FOLDERS.get(category, category)
        target = unique_target(root / folder_name / info.path.name, reserved)
        reserved.add(target)
        moves.append(MovePlan(src=info.path, dst=target, category=category, size=info.size))
        counts[category] = counts.get(category, 0) + 1
        total_bytes += info.size

    if skipped_hidden:
        notes.append(f"跳过 {skipped_hidden} 个隐藏/系统文件")
    if skipped_shortcut:
        notes.append(f"跳过 {skipped_shortcut} 个快捷方式（可在设置中开启归类）")
    if skipped_exe:
        notes.append(f"跳过 {skipped_exe} 个可执行文件（可在设置中开启归类）")
    if skipped_unknown:
        notes.append(f"跳过 {skipped_unknown} 个未识别类型（可在设置中开启归入「其他」）")

    return TidyPlan(moves=moves, notes=notes, counts=counts, total_bytes=total_bytes)


def zone_positions(
    targets: list[DesktopItem],
    all_items: list[DesktopItem],
    canvas_w: int,
    canvas_h: int,
    spacing: tuple[int, int],
    zone_width: int,
    margin: int,
    columns: int,
) -> list[tuple[int, int, int]]:
    """把待整理图标排进桌面右侧的竖条区域，返回 [(index, x, y)]。"""
    if not targets:
        return []
    cell_w = max(56, int(spacing[0]))
    cell_h = max(56, int(spacing[1]))
    zone_left = max(0, int(canvas_w - zone_width))
    inner_w = max(cell_w, int(zone_width) - margin * 2)
    cols = max(1, min(int(columns), inner_w // cell_w))
    header_h = 30
    usable_h = max(cell_h, canvas_h - margin * 2 - header_h)
    rows = max(1, usable_h // cell_h)
    count = len(targets)
    step_y = cell_h
    if count > cols * rows:
        rows = max(1, math.ceil(count / cols))
        step_y = max(34, usable_h // rows)

    occupied = [(item.x, item.y) for item in all_items]
    placed: list[tuple[int, int, int]] = []
    slot = 0
    for item in targets:
        for _ in range(count * 6 + 32):
            col = slot // rows
            row = slot % rows
            slot += 1
            if col >= cols:
                col = cols - 1
                row = min(rows - 1, row + 1)
            x = zone_left + margin + col * cell_w
            y = margin + header_h + row * step_y
            x = min(max(zone_left, x), max(zone_left, canvas_w - cell_w))
            y = min(max(0, y), max(0, canvas_h - min(step_y, cell_h)))
            collision = any(
                abs(x - ox) < cell_w * 0.55 and abs(y - oy) < min(step_y, cell_h) * 0.55
                for ox, oy in occupied
            )
            if not collision:
                break
        occupied.append((x, y))
        placed.append((item.index, int(x), int(y)))
    return placed


def _sort_items(items: list[DesktopItem], by: str) -> list[DesktopItem]:
    if by == "type":
        return sorted(items, key=lambda i: (KIND_RANK.get(i.kind, 99), natural_key(i.name)))
    if by == "mtime":
        return sorted(items, key=lambda i: (-_mtime(i), natural_key(i.name)))
    return sorted(items, key=lambda i: natural_key(i.name))


def _mtime(item: DesktopItem) -> float:
    if not item.path:
        return 0.0
    try:
        return Path(item.path).stat().st_mtime
    except OSError:
        return 0.0


def order_positions(
    items: list[DesktopItem],
    canvas_w: int,
    canvas_h: int,
    spacing: tuple[int, int],
    settings: Settings,
    reserve_zone: bool,
) -> tuple[list[tuple[int, int, int]], int]:
    """按规则重排图标，返回 ([(index,x,y)], 未能排布的图标数)。

    - 系统图标默认锁定；位于待整理区的图标保持不动。
    - scope=apps：只重排应用/快捷方式，占用其原有槽位，不打扰文件位置。
    - scope=all：所有可移动图标重排为左上角起始的网格。
    """
    cell_w = max(56, int(spacing[0]))
    cell_h = max(56, int(spacing[1]))
    zone_left = canvas_w - settings.tidy_zone_width
    locked: list[DesktopItem] = []
    movable: list[DesktopItem] = []
    for item in items:
        if settings.lock_system and item.system:
            locked.append(item)
            continue
        if reserve_zone and item.x >= zone_left - cell_w * 0.5:
            continue
        if settings.order_scope == "apps" and item.kind not in ("app", "installer"):
            continue
        movable.append(item)

    if len(movable) < 2:
        return [], 0

    sorted_items = _sort_items(movable, settings.order_by)

    if settings.order_scope == "apps":
        slots = sorted(((i.x, i.y) for i in movable), key=lambda p: (p[0], p[1]))
        return [(item.index, int(x), int(y)) for item, (x, y) in zip(sorted_items, slots)], 0

    x0 = max(4, int(cell_w * 0.12))
    y0 = max(2, int(cell_h * 0.03))
    avail_w = canvas_w - (settings.tidy_zone_width if reserve_zone else 0) - x0
    max_cols = max(1, avail_w // cell_w)
    max_rows = max(1, (canvas_h - y0) // cell_h)
    capacity = max_cols * max_rows

    moves: list[tuple[int, int, int]] = []
    for i, item in enumerate(sorted_items[:capacity]):
        if settings.order_direction == "row":
            col = i % max_cols
            row = i // max_cols
        else:
            col = i // max_rows
            row = i % max_rows
        moves.append((item.index, int(x0 + col * cell_w), int(y0 + row * cell_h)))
    overflow = max(0, len(sorted_items) - capacity)
    return moves, overflow


def content_size(
    items: list[DesktopItem], canvas_w: int, canvas_h: int, spacing: tuple[int, int]
) -> tuple[int, int]:
    """桌面内容的实际范围（图标可能超出一屏，需要滚动）。"""
    cell_w = max(48, int(spacing[0]))
    cell_h = max(48, int(spacing[1]))
    width = max(1, canvas_w)
    height = max(1, canvas_h)
    for item in items:
        width = max(width, item.x + cell_w)
        height = max(height, item.y + cell_h)
    return int(width), int(height)


def scaled_positions(
    snapshot: Snapshot,
    canvas_w: int,
    canvas_h: int,
    cell_w: int,
    cell_h: int,
) -> list[tuple[str, int, int]]:
    """按桌面尺寸变化比例缩放快照坐标。"""
    src_w = max(1, snapshot.desktop_w or canvas_w)
    src_h = max(1, snapshot.desktop_h or canvas_h)
    kx = canvas_w / src_w
    ky = canvas_h / src_h
    result: list[tuple[str, int, int]] = []
    for item in snapshot.items:
        x = int(round(item.x * kx))
        y = int(round(item.y * ky))
        x = min(max(0, x), max(0, canvas_w - cell_w))
        y = min(max(0, y), max(0, canvas_h - cell_h))
        result.append((item.name, x, y))
    return result


def pretty_bytes(value: int) -> str:
    size = float(max(0, value))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def entries_by_category(entries: list[EntryInfo]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for info in entries:
        if info.is_dir:
            continue
        cat = category_for_suffix(info.suffix) or "其他"
        counts[cat] = counts.get(cat, 0) + 1
    return counts
