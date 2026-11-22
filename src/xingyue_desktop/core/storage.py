"""本地持久化：设置、方案索引、快照文件、撤销日志、运行日志。"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import APP_ID, Settings, Snapshot, is_valid_id, new_id, now_iso


def default_data_dir() -> Path:
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / APP_ID
    return Path.home() / f".{APP_ID.lower()}"


class Store:
    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root else default_data_dir()
        self.schemes_dir = self.root / "schemes"
        self.logs_dir = self.root / "logs"
        self.settings_path = self.root / "settings.json"
        self.index_path = self.root / "index.json"
        self.journal_path = self.root / "journal.json"
        self.ensure()
    def ensure(self) -> None:
        for path in (self.root, self.schemes_dir, self.logs_dir):
            path.mkdir(parents=True, exist_ok=True)

    def _read_json(self, path: Path, default: Any) -> Any:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, ValueError):
            return default

    def _write_json(self, path: Path, data: Any) -> None:
        # 写完同目录临时文件再 os.replace，读者只会看到完整 JSON。
        # 用 mkstemp 而非固定 .tmp 名：并发保存或上次中断残留时不会互相覆盖。
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f"{path.name}.", suffix=".tmp")
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    def load_settings(self) -> Settings:
        return Settings.from_dict(self._read_json(self.settings_path, {}))

    def save_settings(self, settings: Settings) -> None:
        self._write_json(self.settings_path, settings.to_dict())
    def _load_index(self) -> dict[str, Any]:
        data = self._read_json(self.index_path, {})
        if not isinstance(data, dict):
            data = {}
        order = [str(i) for i in data.get("order", []) if isinstance(i, (str, int))]
        active = data.get("active")
        return {"order": order, "active": str(active) if active else None}

    def _save_index(self, order: list[str], active: str | None) -> None:
        self._write_json(self.index_path, {"order": order, "active": active})

    @property
    def active_id(self) -> str | None:
        return self._load_index().get("active")

    def set_active(self, snapshot_id: str | None) -> None:
        index = self._load_index()
        self._save_index(index["order"], snapshot_id)
    def _scheme_path(self, snapshot_id: str) -> Path:
        if not is_valid_id(snapshot_id):
            raise ValueError("非法的方案标识")
        return self.schemes_dir / f"{snapshot_id}.json"

    def list_snapshots(self) -> list[Snapshot]:
        index = self._load_index()
        found: dict[str, Snapshot] = {}
        for path in self.schemes_dir.glob("*.json"):
            data = self._read_json(path, None)
            if not isinstance(data, dict):
                continue
            try:
                snapshot = Snapshot.from_dict(data)
            except (TypeError, ValueError):
                continue
            found[snapshot.id] = snapshot
        ordered: list[Snapshot] = []
        for snapshot_id in index["order"]:
            snapshot = found.pop(snapshot_id, None)
            if snapshot:
                ordered.append(snapshot)
        ordered.extend(sorted(found.values(), key=lambda s: s.created_at, reverse=True))
        return ordered

    def get_snapshot(self, snapshot_id: str) -> Snapshot | None:
        for snapshot in self.list_snapshots():
            if snapshot.id == snapshot_id:
                return snapshot
        return None

    def save_snapshot(self, snapshot: Snapshot, make_active: bool = False) -> None:
        self._write_json(self._scheme_path(snapshot.id), snapshot.to_dict())
        index = self._load_index()
        order = index["order"]
        if snapshot.id not in order:
            order.insert(0, snapshot.id)
        active = snapshot.id if make_active else index["active"]
        self._save_index(order, active)

    def delete_snapshot(self, snapshot_id: str) -> None:
        path = self._scheme_path(snapshot_id)
        try:
            path.unlink()
        except OSError:
            pass
        index = self._load_index()
        order = [i for i in index["order"] if i != snapshot_id]
        active = index["active"]
        if active == snapshot_id:
            active = order[0] if order else None
        self._save_index(order, active)

    def rename_snapshot(self, snapshot_id: str, name: str) -> None:
        snapshot = self.get_snapshot(snapshot_id)
        if not snapshot:
            return
        snapshot.name = name
        self._write_json(self._scheme_path(snapshot.id), snapshot.to_dict())

    def duplicate_snapshot(self, snapshot_id: str, name: str) -> Snapshot | None:
        source = self.get_snapshot(snapshot_id)
        if not source:
            return None
        copy = Snapshot.from_dict(source.to_dict())
        copy.id = new_id("s")
        copy.name = name
        copy.created_at = now_iso()
        copy.auto = False
        self.save_snapshot(copy, make_active=False)
        return copy

    def prune_auto(self, keep: int = 8) -> list[str]:
        """保留最近的若干自动备份，返回被清理的 id。"""
        autos = [s for s in self.list_snapshots() if s.auto]
        autos.sort(key=lambda s: s.created_at, reverse=True)
        removed: list[str] = []
        for snapshot in autos[keep:]:
            if snapshot.id == self.active_id:
                continue
            self.delete_snapshot(snapshot.id)
            removed.append(snapshot.id)
        return removed

    def export_snapshots(self, ids: list[str], path: Path) -> int:
        payload = {"app": APP_ID, "version": 1, "exported_at": now_iso(), "schemes": []}
        for snapshot_id in ids:
            snapshot = self.get_snapshot(snapshot_id)
            if snapshot:
                payload["schemes"].append(snapshot.to_dict())
        self._write_json(path, payload)
        return len(payload["schemes"])

    def import_snapshots(self, path: Path) -> list[Snapshot]:
        data = self._read_json(path, {})
        schemes = data.get("schemes") if isinstance(data, dict) else None
        imported: list[Snapshot] = []
        if not isinstance(schemes, list):
            return imported
        existing = {s.name for s in self.list_snapshots()}
        for raw in schemes:
            if not isinstance(raw, dict):
                continue
            try:
                snapshot = Snapshot.from_dict(raw)
            except (TypeError, ValueError):
                # 导入文件可能来自旧版本或被手工编辑，单条损坏不应让整批失败。
                continue
            snapshot.id = new_id("s")
            snapshot.auto = False
            snapshot.created_at = now_iso()
            base = snapshot.name or "导入方案"
            name = base
            index = 2
            while name in existing:
                name = f"{base} ({index})"
                index += 1
            snapshot.name = name
            existing.add(name)
            self.save_snapshot(snapshot, make_active=False)
            imported.append(snapshot)
        return imported
    def _load_journal(self) -> list[dict[str, Any]]:
        data = self._read_json(self.journal_path, {"entries": []})
        entries = data.get("entries") if isinstance(data, dict) else None
        return entries if isinstance(entries, list) else []

    def _save_journal(self, entries: list[dict[str, Any]]) -> None:
        self._write_json(self.journal_path, {"entries": entries[-20:]})

    def add_journal(self, entry: dict[str, Any]) -> None:
        entries = self._load_journal()
        entries.append(entry)
        self._save_journal(entries)

    def last_journal(self) -> dict[str, Any] | None:
        entries = self._load_journal()
        return entries[-1] if entries else None

    def pop_journal(self) -> dict[str, Any] | None:
        entries = self._load_journal()
        if not entries:
            return None
        entry = entries.pop()
        self._save_journal(entries)
        return entry

    def replace_last_journal(self, entry: dict[str, Any]) -> None:
        entries = self._load_journal()
        if not entries:
            return
        entries[-1] = entry
        self._save_journal(entries)
    def log_path(self, day: datetime | None = None) -> Path:
        day = day or datetime.now()
        return self.logs_dir / f"app-{day:%Y%m%d}.log"

    def write_log(self, level: str, message: str) -> None:
        line = f"{datetime.now():%Y-%m-%d %H:%M:%S} [{level.upper()}] {message}\n"
        try:
            with open(self.log_path(), "a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError:
            pass

    def clear_logs(self) -> None:
        for path in self.logs_dir.glob("app-*.log"):
            try:
                path.unlink()
            except OSError:
                pass

    def backup_file(self, source: Path, target_dir: Path) -> Path | None:
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"{source.stem}-{datetime.now():%Y%m%d-%H%M%S}{source.suffix}"
            shutil.copy2(source, target)
            return target
        except OSError:
            return None

    def stats(self) -> dict[str, Any]:
        snapshots = self.list_snapshots()
        return {
            "schemes": len(snapshots),
            "auto": sum(1 for s in snapshots if s.auto),
            "active": self.active_id,
            "data_dir": str(self.root),
            "journal": len(self._load_journal()),
        }
