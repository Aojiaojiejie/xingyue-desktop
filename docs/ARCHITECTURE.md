# 架构说明

## 目标与边界

星月-桌面整理只做两件事：管理桌面图标的坐标布局，以及按扩展名归类桌面文件。它不修改文件内容、不删除文件、不注入资源管理器进程，所有桌面操作通过 `SysListView32` 的公开 Win32 消息完成。

## 分层

```text
UI (PySide6)
  └─ AppService
       ├─ DesktopBackend ── DesktopAPI (Win32) / DemoBackend
       ├─ Store (JSON 持久化)
       └─ organizer (纯函数算法)
```

### `src/xingyue_desktop/core/`

| 模块 | 职责 |
| --- | --- |
| `models.py` | 数据类与常量：图标、快照、设置、报告、类型映射 |
| `winicon.py` | 定位桌面 `SysListView32`，跨进程读写图标名称与坐标；开关「自动排列」 |
| `desktop_files.py` | 解析真实桌面目录，建立图标名到文件的映射；通知 Shell 刷新 |
| `organizer.py` | 文件归类、待整理区排布、图标排序、快照坐标缩放（纯函数，可测试） |
| `storage.py` | 设置、方案索引、快照文件、撤销日志、按天日志的原子读写 |
| `service.py` | 业务编排：创建/应用快照、收纳新图标、整理文件、撤销、排序；以及演示后端 |

### `src/xingyue_desktop/ui/`

| 模块 | 职责 |
| --- | --- |
| `theme.py` | 浅色/深色调色板与全局 QSS |
| `icons.py` | 用 QPainter 绘制线性图标，避免外部图标字体 |
| `widgets.py` | 方案卡片、桌面预览画布、日志面板、开关、动作卡片、Toast |
| `dialogs.py` | 命名对话框、危险操作确认对话框 |
| `main_window.py` | 三栏布局、状态更新、动作绑定、响应式收起/展开 |

### 入口

- `src/xingyue_desktop/cli.py`：参数解析、DPI 感知、演示数据、异常兜底、启动 Qt。
- `src/xingyue_desktop/__main__.py`：`python -m xingyue_desktop`。
- `main.py`：源码启动薄封装，把 `src/` 加入 `sys.path` 后调用 `cli.main`。

## 关键数据流

### 快照

1. `DesktopAPI.list_items()` 读取所有图标的名称与客户区坐标。
2. `desktop_files.enrich()` 将名称映射到实际文件，得到类型与路径。
3. `Service.create_snapshot()` 生成 `Snapshot`，写入 `%APPDATA%\XingYueDesktop\schemes\`。
4. 应用时按当前桌面内容尺寸与快照尺寸计算缩放比例，逐个匹配名称后用 `LVM_SETITEMPOSITION32` 写回。

### 待整理区

快照未收录、且不属于系统图标的项目被视为「新增」。`organizer.zone_positions()` 在桌面右侧竖条内按列排布，避开已占用槽位；状态栏与预览用金色虚线标记这些图标。

### 文件整理

1. `organizer.plan_tidy()` 扫描用户桌面根目录，按扩展名生成移动计划（跳过快捷方式、可执行文件、隐藏文件，默认跳过未知类型）。
2. 确认后执行 `shutil.move`，目标目录为桌面下的分类文件夹；重名自动追加序号。
3. 实际移动记录写入 `journal.json`，撤销时反向移动并清理空目录。

### 排序

- `scope=apps`：只重排应用/快捷方式，占用它们原有槽位，不打扰文件位置。
- `scope=all`：所有可移动图标按网格重排；系统图标锁定，待整理区图标保持原位。
- 排序键支持名称（系统区域排序，中文近似拼音）、类型、修改时间；方向支持按列/按行。

## 并发与线程

桌面消息与文件操作均在 UI 线程同步执行，通常低于 1 秒；执行期间禁用重复点击并显示等待光标。未引入后台线程，避免 Win32 句柄与 Qt 对象跨线程问题。

## 数据与兼容

- 数据目录：`%APPDATA%\XingYueDesktop`，JSON 写入采用临时文件 + `os.replace`。
- 坐标单位为资源管理器列表视图的物理像素；程序启动时声明 Per-Monitor V2 DPI 感知。
- 快照记录桌面内容尺寸，分辨率变化时按比例缩放；网格间距由系统决定，无法完全复刻。

## 设计约束

- 不删除用户文件；文件移动必须二次确认并可撤销。
- 系统图标默认锁定；待整理区不参与排序。
- 界面不显示实现说明或功能注解，解释性内容只保留在源码注释与文档中。
