"""桌面文件系统辅助：定位真实桌面目录、建立图标名到文件的映射。"""

from __future__ import annotations

import os
import winreg
from dataclasses import dataclass
from pathlib import Path

from .models import DesktopItem, display_stem, is_system_icon, kind_for_suffix, normalize_key

FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_SYSTEM = 0x4
FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def _known_folder(reg_name: str, fallback: Path) -> Path:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        )
        try:
            value, _ = winreg.QueryValueEx(key, reg_name)
        finally:
            key.Close()
        expanded = os.path.expandvars(str(value))
        return Path(expanded)
    except OSError:
        return fallback


def user_desktop() -> Path:
    return _known_folder("Desktop", Path.home() / "Desktop")


def public_desktop() -> Path:
    public_dir = os.environ.get("PUBLIC") or r"C:\Users\Public"
    return Path(public_dir) / "Desktop"


def desktop_roots() -> list[Path]:
    roots: list[Path] = []
    for root in (user_desktop(), public_desktop()):
        if root not in roots:
            roots.append(root)
    return roots


def is_hidden(path: Path) -> bool:
    try:
        attrs = getattr(path.stat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attrs & (FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM))


def is_reparse_point(path: Path) -> bool:
    """判断路径本身是否为符号链接或目录联接（junction）。

    桌面目录可能被其他进程替换为重定向点。移动文件前若只校验路径字符串，
    mkdir + move 会把文件带出桌面范围，因此这里用 lstat 检查链接本身而非目标。
    """
    try:
        attrs = getattr(os.lstat(path), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)


@dataclass
class EntryInfo:
    path: Path
    is_dir: bool
    hidden: bool
    suffix: str
    size: int = 0
    mtime: float = 0.0


def build_index(roots: list[Path] | None = None) -> dict[str, EntryInfo]:
    """图标显示名（可能隐藏扩展名）→ 实际文件。"""
    mapping: dict[str, EntryInfo] = {}
    for root in roots or desktop_roots():
        try:
            entries = list(root.iterdir())
        except OSError:
            continue
        for path in entries:
            name = path.name
            if name.lower() == "desktop.ini":
                continue
            try:
                stat = path.stat()
                info = EntryInfo(
                    path=path,
                    is_dir=path.is_dir(),
                    hidden=is_hidden(path),
                    suffix=path.suffix.lower(),
                    size=int(stat.st_size),
                    mtime=float(stat.st_mtime),
                )
            except OSError:
                continue
            for key in {normalize_key(name), normalize_key(display_stem(name))}:
                mapping.setdefault(key, info)
    return mapping


def enrich(items: list[DesktopItem], index: dict[str, EntryInfo] | None = None) -> list[DesktopItem]:
    """补齐图标的类型与实际路径，供预览着色和类型整理使用。"""
    mapping = build_index() if index is None else index
    for item in items:
        if is_system_icon(item.name):
            item.kind = "system"
            item.path = None
            item.is_dir = False
            continue
        info = mapping.get(normalize_key(item.name))
        if info is None:
            item.kind = "app" if item.name.lower().endswith((".lnk", ".url")) else "other"
            continue
        item.path = str(info.path)
        item.is_dir = info.is_dir
        item.kind = kind_for_suffix(info.suffix, info.is_dir)
    return items


def scan_desktop_files(root: Path) -> list[EntryInfo]:
    """列出桌面根目录下的文件（不递归）。"""
    result: list[EntryInfo] = []
    try:
        entries = list(root.iterdir())
    except OSError:
        return result
    for path in entries:
        name = path.name
        if name.lower() == "desktop.ini":
            continue
        try:
            stat = path.stat()
            is_dir = path.is_dir()
        except OSError:
            continue
        result.append(
            EntryInfo(
                path=path,
                is_dir=is_dir,
                hidden=is_hidden(path),
                suffix=path.suffix.lower(),
                size=0 if is_dir else int(stat.st_size),
                mtime=float(stat.st_mtime),
            )
        )
    return result


def notify_shell(path: Path | str) -> None:
    import ctypes

    try:
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        SHCNE_UPDATEDIR = 0x00001000
        SHCNF_PATHW = 0x0005
        SHCNF_FLUSH = 0x1000
        shell32.SHChangeNotify(SHCNE_UPDATEDIR, SHCNF_PATHW | SHCNF_FLUSH, str(path), None)
    except Exception:
        pass
