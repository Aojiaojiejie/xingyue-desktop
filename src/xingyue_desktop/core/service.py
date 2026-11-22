"""业务服务层：把桌面读写、快照存储、整理算法组织成可被 UI 调用的动作。"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from . import desktop_files, organizer
from .models import (
    DesktopItem,
    Report,
    Settings,
    Snapshot,
    SnapshotItem,
    new_id,
    normalize_key,
    now_iso,
    pretty_time,
)
from .storage import Store
from .winicon import DesktopAPI, DesktopError

LogFn = Callable[[str, str], None]


class DesktopBackend(Protocol):
    def available(self) -> bool: ...
    def list_items(self) -> list[DesktopItem]: ...
    def canvas_size(self) -> tuple[int, int]: ...
    def spacing(self) -> tuple[int, int]: ...
    def dpi(self) -> int: ...
    def auto_arrange(self) -> bool: ...
    def set_auto_arrange(self, enabled: bool) -> bool: ...
    def set_positions(self, moves: list[tuple[int, int, int]], disable_auto: bool = True,
                      redraw: bool = True) -> int: ...
    def refresh(self) -> None: ...


@dataclass
class DesktopState:
    items: list[DesktopItem] = field(default_factory=list)
    canvas_w: int = 0
    canvas_h: int = 0
    content_w: int = 0
    content_h: int = 0
    spacing: tuple[int, int] = (96, 96)
    dpi: int = 96
    auto_arrange: bool = False
    available: bool = True
    error: str = ""


class DemoBackend:
    """演示后端：不触碰真实桌面，用于首次体验和界面预览。"""

    NAMES: list[tuple[str, str]] = [
        ("微信", "app"), ("QQ", "app"), ("钉钉", "app"), ("Microsoft Edge", "app"),
        ("Steam", "app"), ("Everything", "app"), ("ToDesk", "app"), ("WorkBuddy", "app"),
        ("NVIDIA App", "app"), ("PotPlayer", "app"), ("WPS Office", "app"), ("豆包", "app"),
        ("项目资料", "folder"), ("设计稿", "folder"), ("截图", "folder"),
        ("安装包", "folder"), ("临时文件", "folder"),
        ("季度报告.docx", "doc"), ("预算表.xlsx", "sheet"), ("产品路线图.pptx", "slide"),
        ("会议纪要.md", "doc"), ("封面图.png", "image"), ("演示视频.mp4", "media"),
        ("素材包.zip", "archive"), ("数据备份.7z", "archive"),
        ("需求清单.pdf", "doc"), ("客户名单.csv", "sheet"),
        ("图标设计.ico", "image"), ("字体合集.ttf", "other"),
        ("此电脑", "system"), ("回收站", "system"),
    ]

    def __init__(self) -> None:
        self.canvas = (1440, 900)
        self._spacing = (104, 112)
        self._zone_width = 272
        self.items: list[DesktopItem] = []
        cols = 7
        margin_x, margin_y = 24, 12
        index = 0
        for i, (name, kind) in enumerate(self.NAMES):
            if name in ("此电脑", "回收站"):
                x, y = 24 + (0 if name == "此电脑" else 1) * self._spacing[0], 760
            elif i < 27:
                col, row = i % cols, i // cols
                x = margin_x + col * self._spacing[0]
                y = margin_y + row * self._spacing[1]
            else:
                slot = i - 27
                x = self.canvas[0] - self._zone_width - 96
                y = 520 + slot * 112
            self.items.append(DesktopItem(index=index, name=name, x=x, y=y, kind=kind))
            index += 1
        self._auto = False
        self.applied = 0

    def available(self) -> bool:
        return True

    def list_items(self) -> list[DesktopItem]:
        return [DesktopItem(**item.__dict__) for item in self.items]

    def canvas_size(self) -> tuple[int, int]:
        return self.canvas

    def spacing(self) -> tuple[int, int]:
        return self._spacing

    def dpi(self) -> int:
        return 96

    def auto_arrange(self) -> bool:
        return self._auto

    def set_auto_arrange(self, enabled: bool) -> bool:
        changed = self._auto != enabled
        self._auto = enabled
        return changed

    def set_positions(self, moves: list[tuple[int, int, int]], disable_auto: bool = True,
                      redraw: bool = True) -> int:
        by_index = {item.index: item for item in self.items}
        applied = 0
        for index, x, y in moves:
            item = by_index.get(index)
            if item is None:
                continue
            item.x, item.y = int(x), int(y)
            applied += 1
        self.applied += applied
        return applied

    def refresh(self) -> None:
        return None


class AppService:
    def __init__(
        self,
        backend: DesktopBackend | None = None,
        store: Store | None = None,
        on_log: LogFn | None = None,
        demo: bool = False,
    ) -> None:
        self.demo = demo
        self.backend: DesktopBackend = backend or (DemoBackend() if demo else DesktopAPI())
        self.store = store or Store()
        self.settings: Settings = self.store.load_settings()
        self.on_log = on_log
        self.desktop_dir = desktop_files.user_desktop()
        if demo:
            self.desktop_dir = Path.cwd() / ".demo-desktop"
    def log(self, level: str, message: str) -> None:
        self.store.write_log(level, message)
        if self.on_log:
            try:
                self.on_log(level, message)
            except Exception:
                pass

    @property
    def snapshots(self) -> list[Snapshot]:
        return self.store.list_snapshots()

    @property
    def active_snapshot(self) -> Snapshot | None:
        active_id = self.store.active_id
        if not active_id:
            return None
        return self.store.get_snapshot(active_id)

    def save_settings(self, settings: Settings) -> None:
        self.settings = settings
        self.store.save_settings(settings)

    def refresh_state(self) -> DesktopState:
        try:
            if not self.backend.available():
                raise DesktopError("桌面图标视图不可用")
            items = self.backend.list_items()
            desktop_files.enrich(items)
            canvas_w, canvas_h = self.backend.canvas_size()
            spacing = self.backend.spacing()
            content_w, content_h = organizer.content_size(items, canvas_w, canvas_h, spacing)
            return DesktopState(
                items=items,
                canvas_w=canvas_w,
                canvas_h=canvas_h,
                content_w=content_w,
                content_h=content_h,
                spacing=spacing,
                dpi=self.backend.dpi(),
                auto_arrange=self.backend.auto_arrange(),
            )
        except Exception as exc:
            return DesktopState(available=False, error=str(exc))

    def _state_or_report(self, title: str) -> tuple[DesktopState | None, Report | None]:
        state = self.refresh_state()
        if not state.available:
            report = Report(title=title, ok=False)
            report.add(f"无法读取桌面：{state.error}", "error")
            self.log("error", f"{title}失败：{state.error}")
            return None, report
        return state, None

    def _prepare_target_dir(self, path: Path, desktop_root: Path) -> None:
        # 分类目录建在桌面下，而桌面本身可能被其他进程替换为 junction（联接点）。
        # 只在路径字符串上校验不成立：mkdir 会跟随重定向点，文件随即被移出桌面。
        # 因此建目录前拒绝重定向点，建完再校验解析结果仍落在桌面内。
        if path.is_dir() and desktop_files.is_reparse_point(path):
            raise OSError(f"目标目录是重定向链接，已拒绝：{path}")
        path.mkdir(parents=True, exist_ok=True)
        try:
            path.resolve().relative_to(desktop_root)
        except ValueError:
            raise OSError(f"目标目录解析到桌面之外，已拒绝：{path}") from None
    def next_scheme_name(self) -> str:
        existing = {s.name for s in self.snapshots}
        index = 1
        while f"方案 {index}" in existing:
            index += 1
        return f"方案 {index}"

    def create_snapshot(self, name: str | None = None, auto: bool = False,
                        make_active: bool = True) -> Snapshot | None:
        state, error = self._state_or_report("创建快照")
        if error or state is None:
            return None
        clean = (name or "").strip()
        if not clean:
            clean = f"自动备份 {now_iso()[11:16]}" if auto else self.next_scheme_name()
        snapshot = Snapshot(
            id=new_id("s"),
            name=clean,
            created_at=now_iso(),
            desktop_w=state.content_w,
            desktop_h=state.content_h,
            items=[SnapshotItem(name=i.name, x=i.x, y=i.y, kind=i.kind) for i in state.items],
            spacing=state.spacing,
            dpi=state.dpi,
            auto=auto,
        )
        self.store.save_snapshot(snapshot, make_active=make_active and not auto)
        if auto:
            self.store.prune_auto(8)
        self.log("ok", f"已记录快照「{snapshot.name}」，共 {len(snapshot.items)} 个图标")
        return snapshot

    def apply_snapshot(self, snapshot: Snapshot, dry_run: bool = False,
                       move_new: bool | None = None) -> Report:
        report = Report(title=f"应用方案「{snapshot.name}」")
        state, error = self._state_or_report(report.title)
        if error or state is None:
            return error or report
        cell_w, cell_h = state.spacing
        scaled = organizer.scaled_positions(snapshot, state.content_w, state.content_h, cell_w, cell_h)

        by_key: dict[str, list[DesktopItem]] = {}
        for item in state.items:
            by_key.setdefault(item.key, []).append(item)

        moves: list[tuple[int, int, int]] = []
        used: set[int] = set()
        missing: list[str] = []
        for name, x, y in scaled:
            candidates = by_key.get(normalize_key(name), [])
            target = next((c for c in candidates if c.index not in used), None)
            if target is None:
                missing.append(name)
                continue
            used.add(target.index)
            moves.append((target.index, x, y))

        if not moves:
            report.ok = False
            report.add("当前桌面没有与快照匹配的图标", "warn")
            self.log("warn", f"{report.title}：没有匹配的图标，未做改动")
            return report

        if dry_run:
            report.detail["dry_run"] = True
            report.add(f"预演：将排列 {len(moves)} 个图标，缺失 {len(missing)} 个", "info")
            return report

        if self.settings.auto_backup and self.store.active_id != snapshot.id and state.items:
            backup = self.create_snapshot(auto=True, make_active=False)
            if backup:
                report.add(f"已把当前布局记录为「{backup.name}」", "info")

        if state.auto_arrange:
            try:
                self.backend.set_auto_arrange(False)
            except DesktopError as exc:
                report.ok = False
                report.add(f"无法关闭桌面「自动排列图标」：{exc}", "error")
                self.log("error", str(exc))
                return report
            self.log("warn", "检测到桌面「自动排列图标」已开启，已暂时关闭以便写入位置")

        applied = self.backend.set_positions(moves)
        self.backend.refresh()
        report.moved = applied
        report.skipped = len(missing)
        report.failed = len(moves) - applied
        report.add(f"已移动 {applied} 个图标，缺失 {len(missing)} 个", "ok" if applied else "warn")
        if missing:
            preview = "、".join(missing[:4]) + ("…" if len(missing) > 4 else "")
            report.add(f"快照中有 {len(missing)} 个图标当前不在桌面：{preview}", "warn")
        if applied == 0:
            report.ok = False
            report.add("没有图标被写入，方案未激活", "error")
            self.log("error", f"{report.title}：没有图标被写入")
            return report
        if state.auto_arrange:
            report.add("已关闭桌面「自动排列图标」，可在桌面右键重新开启", "warn")
        self.store.set_active(snapshot.id)

        want_zone = self.settings.apply_moves_new if move_new is None else move_new
        if want_zone:
            extras = self._extras(state, included=used)
            if extras:
                zone_moves = organizer.zone_positions(
                    extras, state.items, state.canvas_w, state.canvas_h, state.spacing,
                    self.settings.tidy_zone_width, self.settings.tidy_zone_margin,
                    self.settings.zone_columns,
                )
                count = self.backend.set_positions(zone_moves)
                self.backend.refresh()
                if count:
                    report.add(f"另有 {count} 个新增图标移入「待整理」区域", "info")
                    self.log("info", f"应用方案后，{count} 个未收录图标移入待整理区")
                else:
                    report.add("新增图标未能移入待整理区", "warn")
        self.log("ok", f"{report.title}：移动 {applied} 个，缺失 {len(missing)} 个")
        return report

    def _extras(self, state: DesktopState, included: set[int]) -> list[DesktopItem]:
        zone_left = state.canvas_w - self.settings.tidy_zone_width - state.spacing[0] * 0.5
        extras: list[DesktopItem] = []
        for item in state.items:
            if item.index in included:
                continue
            if item.system:
                continue
            if item.x >= zone_left:
                continue
            extras.append(item)
        return extras

    def move_new_to_zone(self, snapshot: Snapshot | None = None, dry_run: bool = False) -> Report:
        target = snapshot or self.active_snapshot
        report = Report(title="将新增图标移入待整理区")
        if target is None:
            report.ok = False
            report.add("尚未选择方案，请先创建或选中一套方案", "warn")
            self.log("warn", report.lines[-1][1])
            return report
        state, error = self._state_or_report(report.title)
        if error or state is None:
            return error or report
        reference = {normalize_key(i.name) for i in target.items}
        zone_left = state.canvas_w - self.settings.tidy_zone_width - state.spacing[0] * 0.5
        extras = [
            item for item in state.items
            if item.key not in reference and not item.system and item.x < zone_left
        ]
        if not extras:
            report.add("没有发现新增图标，桌面与方案一致", "ok")
            self.log("info", "未发现需要移动到待整理区的图标")
            return report
        moves = organizer.zone_positions(
            extras, state.items, state.canvas_w, state.canvas_h, state.spacing,
            self.settings.tidy_zone_width, self.settings.tidy_zone_margin,
            self.settings.zone_columns,
        )
        if dry_run:
            report.add(f"预演：将移动 {len(moves)} 个图标到右侧待整理区", "info")
            return report
        applied = self.backend.set_positions(moves)
        self.backend.refresh()
        report.moved = applied
        report.add(f"已将 {applied} 个新增图标移入待整理区", "ok")
        self.log("ok", f"已将 {applied} 个新增图标移入待整理区")
        return report
    def tidy_files(self, dry_run: bool | None = None, auto_backup: bool | None = None) -> Report:
        report = Report(title="一键整理文件")
        root = self.desktop_dir
        if not root.exists():
            report.ok = False
            report.add(f"桌面目录不存在：{root}", "error")
            self.log("error", report.lines[-1][1])
            return report
        plan = organizer.plan_tidy(root, self.settings)
        report.detail["plan"] = plan
        for note in plan.notes:
            report.add(note, "info")
        if not plan.moves:
            report.add("没有需要归类的文件，桌面已经很整洁", "ok")
            self.log("info", "一键整理：没有需要归类的文件")
            return report

        summary = "，".join(f"{cat} {count}" for cat, count in plan.counts.items())
        report.add(f"计划将 {len(plan.moves)} 个文件归入 {len(plan.folders)} 个文件夹（{summary}）", "info")

        preview = self.settings.dry_run if dry_run is None else dry_run
        if preview:
            report.detail["dry_run"] = True
            for move in plan.moves[:40]:
                report.add(f"预演 · {move.src.name} → {move.dst.parent.name}/", "muted")
            if len(plan.moves) > 40:
                report.add(f"预演 · 其余 {len(plan.moves) - 40} 个文件略", "muted")
            self.log("info", f"预演完成：{len(plan.moves)} 个文件待归类（未实际移动）")
            return report

        backup_enabled = self.settings.auto_backup if auto_backup is None else bool(auto_backup)
        if backup_enabled:
            backup = self.create_snapshot(auto=True, make_active=False)
            if backup:
                report.add(f"已在移动前自动记录快照「{backup.name}」", "info")

        done: list[tuple[str, str]] = []
        failed = 0
        desktop_root = root.resolve()
        for move in plan.moves:
            try:
                target = organizer.unique_target(move.dst)
                self._prepare_target_dir(target.parent, desktop_root)
                shutil.move(str(move.src), str(target))
                done.append((str(move.src), str(target)))
            except (OSError, shutil.Error) as exc:
                failed += 1
                report.add(f"移动失败：{move.src.name}（{exc}）", "error")
        if done:
            self.store.add_journal({
                "id": new_id("j"),
                "created_at": now_iso(),
                "kind": "tidy",
                "moves": [{"src": src, "dst": dst} for src, dst in done],
                "count": len(done),
            })
            desktop_files.notify_shell(root)
            try:
                self.backend.refresh()
            except Exception:
                pass
        report.moved = len(done)
        report.failed = failed
        if done:
            report.add(f"已归类 {len(done)} 个文件，可在右侧撤销", "ok")
            self.log("ok", f"一键整理完成：移动 {len(done)} 个文件，失败 {failed} 个")
        else:
            report.ok = False
            self.log("error", "一键整理失败：没有文件被移动")
        return report

    def order_icons(self, dry_run: bool = False) -> Report:
        report = Report(title="重排图标顺序")
        state, error = self._state_or_report(report.title)
        if error or state is None:
            return error or report
        zone_left = state.canvas_w - self.settings.tidy_zone_width
        reserve_zone = any(item.x >= zone_left - state.spacing[0] * 0.5 for item in state.items)
        moves, overflow = organizer.order_positions(
            state.items, state.canvas_w, state.canvas_h, state.spacing, self.settings, reserve_zone
        )
        if not moves:
            report.add("没有可重排的图标（系统图标已锁定，或数量不足）", "warn")
            self.log("info", "重排图标：没有可移动的图标")
            return report
        if dry_run:
            report.add(f"预演：将重排 {len(moves)} 个图标", "info")
            return report
        if state.auto_arrange:
            try:
                self.backend.set_auto_arrange(False)
            except DesktopError as exc:
                report.ok = False
                report.add(f"无法关闭桌面「自动排列图标」：{exc}", "error")
                self.log("error", str(exc))
                return report
            self.log("warn", "已关闭桌面「自动排列图标」以便排序")
        applied = self.backend.set_positions(moves, disable_auto=False)
        self.backend.refresh()
        report.moved = applied
        report.skipped = overflow
        report.add(f"已按规则重排 {applied} 个图标", "ok")
        if state.auto_arrange:
            report.add("已关闭桌面「自动排列图标」，可在桌面右键重新开启", "warn")
        if overflow:
            report.add(f"桌面空间不足，{overflow} 个图标保持原位", "warn")
        self.log("ok", report.lines[0][1])
        return report

    def undo_last_tidy(self) -> Report:
        report = Report(title="撤销上次文件整理")
        entry = self.store.last_journal()
        if not entry:
            report.ok = False
            report.add("没有可撤销的整理记录", "warn")
            return report
        moves = entry.get("moves", [])
        desktop_root = self.desktop_dir.resolve()
        restored = 0
        failed = 0
        remaining: list[dict[str, str]] = []
        touched: set[Path] = set()
        for move in reversed(moves):
            raw_src = move.get("src") if isinstance(move, dict) else None
            raw_dst = move.get("dst") if isinstance(move, dict) else None
            if not isinstance(raw_src, str) or not isinstance(raw_dst, str) or not raw_src or not raw_dst:
                failed += 1
                report.add("撤销记录缺少有效路径，已跳过", "warn")
                continue
            # journal.json 是可被手工编辑的普通文件，按不可信输入处理：
            # 两端都要求解析后落在桌面内，避免被构造的记录把任意文件搬进或搬出桌面。
            try:
                src = Path(raw_src).resolve()
                dst = Path(raw_dst).resolve()
                src.relative_to(desktop_root)
                dst.relative_to(desktop_root)
            except (OSError, ValueError):
                failed += 1
                report.add("撤销记录包含桌面外路径，已跳过", "warn")
                continue
            if not dst.exists():
                failed += 1
                report.add(f"文件已不在原位置：{dst.name}", "warn")
                continue
            try:
                target = organizer.unique_target(src)
                self._prepare_target_dir(target.parent, desktop_root)
                shutil.move(str(dst), str(target))
                restored += 1
                touched.add(dst.parent)
            except (OSError, ValueError, shutil.Error) as exc:
                failed += 1
                remaining.append({"src": str(src), "dst": str(dst)})
                report.add(f"还原失败：{dst.name}（{exc}）", "error")
        for folder in touched:
            try:
                if folder.exists() and not any(folder.iterdir()):
                    folder.rmdir()
            except OSError:
                pass
        if restored:
            if remaining:
                self.store.replace_last_journal({**entry, "moves": remaining, "count": len(remaining)})
            else:
                self.store.pop_journal()
            desktop_files.notify_shell(self.desktop_dir)
            try:
                self.backend.refresh()
            except Exception:
                pass
        report.moved = restored
        report.failed = failed
        report.ok = restored > 0
        report.add(f"已还原 {restored} 个文件" + (f"，失败 {failed} 个" if failed else ""), "ok" if restored else "error")
        self.log("ok" if restored else "warn", report.lines[-1][1])
        return report
    def delete_snapshot(self, snapshot_id: str) -> None:
        snapshot = self.store.get_snapshot(snapshot_id)
        self.store.delete_snapshot(snapshot_id)
        if snapshot:
            self.log("info", f"已删除方案「{snapshot.name}」")

    def rename_snapshot(self, snapshot_id: str, name: str) -> bool:
        clean = name.strip()
        if not clean:
            return False
        self.store.rename_snapshot(snapshot_id, clean)
        self.log("info", f"方案已重命名为「{clean}」")
        return True

    def duplicate_snapshot(self, snapshot_id: str, name: str) -> Snapshot | None:
        copy = self.store.duplicate_snapshot(snapshot_id, name.strip() or "方案副本")
        if copy:
            self.log("info", f"已复制方案为「{copy.name}」")
        return copy

    def export_snapshots(self, ids: list[str], path: Path) -> int:
        count = self.store.export_snapshots(ids, path)
        self.log("ok", f"已导出 {count} 套方案")
        return count

    def import_snapshots(self, path: Path) -> list[Snapshot]:
        imported = self.store.import_snapshots(path)
        if imported:
            self.log("ok", f"已导入 {len(imported)} 套方案")
        return imported

    def friendly_time(self, iso: str) -> str:
        return pretty_time(iso)

