"""核心逻辑单元测试：归类、待整理区、排序、缩放、存储、服务动作。"""

from __future__ import annotations

from pathlib import Path

import pytest

from xingyue_desktop.core import organizer
from xingyue_desktop.core.models import DesktopItem, Settings, Snapshot, SnapshotItem
from xingyue_desktop.core.service import AppService, DemoBackend
from xingyue_desktop.core.storage import Store


def make_file(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_category_for_suffix() -> None:
    assert organizer.category_for_suffix(".PNG") == "图片"
    assert organizer.category_for_suffix(".docx") == "文档"
    assert organizer.category_for_suffix(".xlsx") == "表格"
    assert organizer.category_for_suffix(".exe") == "安装包"
    assert organizer.category_for_suffix(".unknown") is None


def test_plan_tidy_filters_and_collisions(tmp_path: Path) -> None:
    desktop = tmp_path / "desktop"
    make_file(desktop / "报告.docx")
    make_file(desktop / "封面.PNG")
    make_file(desktop / "setup.exe")
    make_file(desktop / "未知.xyz")
    make_file(desktop / "旧文件.lnk")
    make_file(desktop / "desktop.ini")
    (desktop / "项目文件夹").mkdir()
    make_file(desktop / "文档" / "报告.docx")

    plan = organizer.plan_tidy(desktop, Settings())

    names = {move.src.name for move in plan.moves}
    assert names == {"报告.docx", "封面.PNG"}
    doc_move = next(m for m in plan.moves if m.src.name == "报告.docx")
    assert doc_move.dst == desktop / "文档" / "报告 (2).docx"
    assert plan.counts == {"文档": 1, "图片": 1}
    assert any("可执行文件" in note for note in plan.notes)
    assert any("快捷方式" in note for note in plan.notes)


def test_plan_tidy_can_include_executables_and_unknown(tmp_path: Path) -> None:
    desktop = tmp_path / "desktop"
    make_file(desktop / "setup.exe")
    make_file(desktop / "未知.xyz")
    settings = Settings(include_executables=True, tidy_unknown=True)
    plan = organizer.plan_tidy(desktop, settings)
    assert {m.category for m in plan.moves} == {"安装包", "其他"}


def test_zone_positions_stay_right_and_avoid_collisions() -> None:
    all_items = [DesktopItem(index=i, name=f"a{i}", x=20 + i * 100, y=20, kind="app") for i in range(4)]
    new_items = [DesktopItem(index=10 + i, name=f"new{i}", x=20, y=20, kind="doc") for i in range(6)]
    placed = organizer.zone_positions(
        new_items, all_items + new_items, 1440, 900, (104, 112), 272, 18, 2
    )
    assert len(placed) == 6
    for _index, x, y in placed:
        assert x >= 1440 - 272 - 1
        assert y >= 18
        assert x <= 1440 - 104
        assert y <= 900 - 112
    assert len({(x, y) for _i, x, y in placed}) == 6


def test_order_positions_keeps_system_icons() -> None:
    items = [
        DesktopItem(index=0, name="微信", x=500, y=300, kind="app"),
        DesktopItem(index=1, name="QQ", x=300, y=100, kind="app"),
        DesktopItem(index=2, name="此电脑", x=20, y=20, kind="system"),
        DesktopItem(index=3, name="报告.docx", x=700, y=400, kind="doc"),
    ]
    settings = Settings(order_scope="apps", lock_system=True)
    moves, overflow = organizer.order_positions(items, 1440, 900, (100, 110), settings, False)
    assert overflow == 0
    moved = {index: (x, y) for index, x, y in moves}
    assert 2 not in moved
    assert 3 not in moved
    assert moved[1][0] < moved[0][0]


def test_order_positions_all_uses_grid() -> None:
    items = [DesktopItem(index=i, name=f"应用{i:02d}", x=900, y=600, kind="app") for i in range(5)]
    moves, overflow = organizer.order_positions(
        items, 1440, 900, (100, 110), Settings(order_scope="all"), False
    )
    assert overflow == 0
    coords = [(x, y) for _i, x, y in moves]
    assert coords[0] == (12, 3)
    assert coords[1] == (12, 113)


def test_scaled_positions() -> None:
    snapshot = Snapshot(
        id="s1", name="A", created_at="2026-01-01T00:00:00+08:00",
        desktop_w=1000, desktop_h=500,
        items=[SnapshotItem(name="微信", x=100, y=50)],
    )
    scaled = organizer.scaled_positions(snapshot, 2000, 1000, 100, 100)
    assert scaled == [("微信", 200, 100)]


def test_storage_roundtrip(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    assert store.list_snapshots() == []
    snapshot = Snapshot(
        id="s1", name="工作布局", created_at="2026-01-01T00:00:00+08:00",
        desktop_w=1440, desktop_h=900,
        items=[SnapshotItem(name="微信", x=10, y=20, kind="app")],
    )
    store.save_snapshot(snapshot, make_active=True)
    loaded = store.get_snapshot("s1")
    assert loaded is not None
    assert loaded.name == "工作布局"
    assert loaded.items[0].name == "微信"
    assert store.active_id == "s1"

    store.rename_snapshot("s1", "新名字")
    assert store.get_snapshot("s1").name == "新名字"

    copy = store.duplicate_snapshot("s1", "副本")
    assert copy is not None and copy.id != "s1"
    assert len(store.list_snapshots()) == 2

    store.set_active("s1")
    store.delete_snapshot("s1")
    assert store.get_snapshot("s1") is None
    assert store.active_id == copy.id

    export_path = tmp_path / "export.json"
    assert store.export_snapshots([copy.id], export_path) == 1
    store2 = Store(tmp_path / "data2")
    imported = store2.import_snapshots(export_path)
    assert len(imported) == 1


def test_service_snapshot_and_apply_roundtrip(tmp_path: Path) -> None:
    backend = DemoBackend()
    service = AppService(backend=backend, store=Store(tmp_path / "data"))
    snapshot = service.create_snapshot("基准")
    assert snapshot is not None
    original = {item.name: (item.x, item.y) for item in backend.items}

    backend.items[0].x += 300
    backend.items[0].y += 200
    report = service.apply_snapshot(snapshot)
    assert report.ok
    assert report.moved == len(snapshot.items)
    assert (backend.items[0].x, backend.items[0].y) == original[backend.items[0].name]


def test_service_zone_and_order(tmp_path: Path) -> None:
    backend = DemoBackend()
    service = AppService(backend=backend, store=Store(tmp_path / "data"))
    snapshot = service.create_snapshot("基准")
    assert snapshot is not None
    backend.items.append(DesktopItem(index=99, name="新图标.png", x=40, y=420, kind="image"))
    report = service.move_new_to_zone(snapshot)
    assert report.ok and report.moved == 1
    new_item = next(i for i in backend.items if i.name == "新图标.png")
    assert new_item.x >= backend.canvas[0] - service.settings.tidy_zone_width - 1

    before = {i.name: (i.x, i.y) for i in backend.items}
    report = service.order_icons()
    assert report.ok
    assert "此电脑" in before
    assert (next(i for i in backend.items if i.name == "此电脑").x,
            next(i for i in backend.items if i.name == "此电脑").y) == before["此电脑"]


def test_service_tidy_and_undo(tmp_path: Path) -> None:
    desktop = tmp_path / "desktop"
    make_file(desktop / "报告.docx", "doc")
    make_file(desktop / "图片.png", "img")
    service = AppService(backend=DemoBackend(), store=Store(tmp_path / "data"))
    service.settings.auto_backup = False
    service.desktop_dir = desktop

    report = service.tidy_files(dry_run=True)
    assert report.detail.get("dry_run")
    assert (desktop / "报告.docx").exists()

    report = service.tidy_files()
    assert report.ok and report.moved == 2
    assert (desktop / "文档" / "报告.docx").exists()
    assert (desktop / "图片" / "图片.png").exists()
    assert service.store.last_journal() is not None

    undo = service.undo_last_tidy()
    assert undo.ok and undo.moved == 2
    assert (desktop / "报告.docx").exists()
    assert not (desktop / "文档" / "报告.docx").exists()


def test_service_dry_run_never_moves(tmp_path: Path) -> None:
    desktop = tmp_path / "desktop"
    make_file(desktop / "报告.docx")
    service = AppService(backend=DemoBackend(), store=Store(tmp_path / "data"))
    service.desktop_dir = desktop
    report = service.tidy_files(dry_run=True)
    assert report.ok
    assert (desktop / "报告.docx").exists()
    assert not (desktop / "文档").exists()


def test_snapshot_id_rejects_path_traversal(tmp_path: Path) -> None:
    snapshot = Snapshot.from_dict({
        "id": "../../evil",
        "name": "bad",
        "desktop_w": 100,
        "desktop_h": 100,
        "items": [],
    })
    assert snapshot.id != "../../evil"
    assert "/" not in snapshot.id and "\\" not in snapshot.id
    store = Store(tmp_path / "data")
    store.save_snapshot(snapshot)
    assert (store.schemes_dir / f"{snapshot.id}.json").exists()
    with pytest.raises(ValueError):
        store.delete_snapshot("../../evil")


def test_undo_skips_paths_outside_desktop(tmp_path: Path) -> None:
    desktop = tmp_path / "desktop"
    desktop.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("keep", encoding="utf-8")
    service = AppService(backend=DemoBackend(), store=Store(tmp_path / "data"))
    service.desktop_dir = desktop
    service.store.add_journal({
        "id": "j1",
        "created_at": "2026-01-01T00:00:00+08:00",
        "kind": "tidy",
        "moves": [{"src": str(desktop / "original.txt"), "dst": str(outside)}],
        "count": 1,
    })
    report = service.undo_last_tidy()
    assert not report.ok
    assert outside.exists()
    assert service.store.last_journal() is not None
