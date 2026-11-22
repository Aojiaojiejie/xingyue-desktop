"""桌面图标底层访问（Windows Shell SysListView32）。

通过 ListView 消息读取/写入图标位置与名称。跨进程读取文本和坐标需要在
explorer.exe 中分配远程内存，因此使用 VirtualAllocEx / ReadProcessMemory。
本模块只负责与 Shell 通信，不做文件系统判断。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from .models import DesktopItem

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LVM_FIRST = 0x1000
LVM_GETITEMCOUNT = LVM_FIRST + 4
LVM_SETITEMPOSITION = LVM_FIRST + 15
LVM_GETITEMPOSITION = LVM_FIRST + 16
LVM_REDRAWITEMS = LVM_FIRST + 21
LVM_SETITEMPOSITION32 = LVM_FIRST + 49
LVM_GETITEMSPACING = LVM_FIRST + 51
LVM_GETITEMTEXTW = LVM_FIRST + 115

LVIF_TEXT = 0x0001
LVS_AUTOARRANGE = 0x0100
GWL_STYLE = -16
WM_SETREDRAW = 0x000B

PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04

# 同一块远程缓冲被三种结构复用，偏移必须互不重叠并留足余量：
# [0, sizeof(LVITEMW)) 放结构体，TEXT_OFF 起放 TEXT_CHARS 个 UTF-16 字符，
# POINT_OFF 起放 POINT。调整任一常量前先确认
# TEXT_OFF + TEXT_CHARS * 2 <= POINT_OFF 且 POINT_OFF + 8 <= BUF_SIZE，
# 否则跨进程写入会越界破坏 explorer 内存。
BUF_SIZE = 4096
TEXT_OFF = 1024
TEXT_CHARS = 260
POINT_OFF = 2048

user32.FindWindowW.restype = wintypes.HWND
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowExW.restype = wintypes.HWND
user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.IsWindow.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.GetClientRect.restype = wintypes.BOOL
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
user32.InvalidateRect.restype = wintypes.BOOL
user32.InvalidateRect.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.BOOL]
user32.UpdateWindow.restype = wintypes.BOOL
user32.UpdateWindow.argtypes = [wintypes.HWND]
try:
    user32.GetDpiForWindow.restype = wintypes.UINT
    user32.GetDpiForWindow.argtypes = [wintypes.HWND]
except AttributeError:  # pragma: no cover
    pass

kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
try:
    kernel32.IsWow64Process.restype = wintypes.BOOL
    kernel32.IsWow64Process.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
except AttributeError:  # pragma: no cover
    pass
kernel32.VirtualAllocEx.restype = ctypes.c_void_p
kernel32.VirtualAllocEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualFreeEx.restype = wintypes.BOOL
kernel32.VirtualFreeEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]
kernel32.WriteProcessMemory.restype = wintypes.BOOL
kernel32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                        ctypes.POINTER(ctypes.c_size_t)]
kernel32.ReadProcessMemory.restype = wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                       ctypes.POINTER(ctypes.c_size_t)]


class DesktopError(RuntimeError):
    """桌面 Shell 不可用或拒绝访问。"""


class LVITEMW(ctypes.Structure):
    _fields_ = [
        ("mask", wintypes.UINT),
        ("iItem", ctypes.c_int),
        ("iSubItem", ctypes.c_int),
        ("state", wintypes.UINT),
        ("stateMask", wintypes.UINT),
        ("pszText", ctypes.c_void_p),
        ("cchTextMax", ctypes.c_int),
        ("iImage", ctypes.c_int),
        ("lParam", ctypes.c_ssize_t),
        ("iIndent", ctypes.c_int),
        ("iGroupId", ctypes.c_int),
        ("cColumns", wintypes.UINT),
        ("puColumns", ctypes.c_void_p),
        ("piColFmt", ctypes.c_void_p),
        ("iGroup", ctypes.c_int),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _Remote:
    """在 explorer.exe 内的一块可读写缓冲区。"""

    def __init__(self, hwnd: int, size: int = BUF_SIZE) -> None:
        # 先置 None：__init__ 中途抛异常时 close()/__del__ 仍能安全执行。
        self.address: int | None = None
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        self.pid = int(pid.value)
        access = PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_QUERY_INFORMATION
        self.process = kernel32.OpenProcess(access, False, self.pid)
        if not self.process:
            code = ctypes.get_last_error()
            raise DesktopError(
                f"无法访问资源管理器进程（错误码 {code}）。请尝试以与资源管理器相同的权限运行本程序。"
            )
        try:
            is_wow = wintypes.BOOL()
            if not kernel32.IsWow64Process(self.process, ctypes.byref(is_wow)):
                code = ctypes.get_last_error()
                kernel32.CloseHandle(self.process)
                self.process = None
                raise DesktopError(f"无法确定资源管理器的位数（错误码 {code}），已拒绝读写桌面图标。")
            explorer_bits = 32 if is_wow.value else 64
            # 位数不一致时结构体布局不同，写入会破坏 explorer 内存，必须拒绝而不是降级。
            if explorer_bits != ctypes.sizeof(ctypes.c_void_p) * 8:
                kernel32.CloseHandle(self.process)
                self.process = None
                raise DesktopError("Python 与资源管理器的位数不一致，无法安全读写桌面图标。")
        except AttributeError:  # pragma: no cover
            pass
        self.address = kernel32.VirtualAllocEx(
            self.process, None, size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE
        )
        if not self.address:
            code = ctypes.get_last_error()
            kernel32.CloseHandle(self.process)
            self.process = None
            raise DesktopError(f"远程内存分配失败（错误码 {code}）。")

    def write(self, data: bytes, offset: int = 0) -> None:
        written = ctypes.c_size_t(0)
        ok = kernel32.WriteProcessMemory(
            self.process, ctypes.c_void_p(self.address + offset), data, len(data), ctypes.byref(written)
        )
        if not ok or written.value != len(data):
            raise DesktopError("写入桌面进程内存失败。")

    def read(self, size: int, offset: int = 0) -> bytes:
        buf = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t(0)
        ok = kernel32.ReadProcessMemory(
            self.process, ctypes.c_void_p(self.address + offset), buf, size, ctypes.byref(got)
        )
        if not ok or got.value != size:
            raise DesktopError("读取桌面进程内存失败。")
        return buf.raw[: got.value]

    def close(self) -> None:
        # __init__ 可能在 self.process 赋值之前就失败，__del__ 仍会走到这里。
        process = getattr(self, "process", None)
        if not process:
            return
        address = getattr(self, "address", None)
        if address:
            kernel32.VirtualFreeEx(process, ctypes.c_void_p(address), 0, MEM_RELEASE)
            self.address = None
        kernel32.CloseHandle(process)
        self.process = None


def _find_listview() -> int | None:
    progman = user32.FindWindowW("Progman", None)
    if progman:
        defview = user32.FindWindowExW(progman, None, "SHELLDLL_DefView", None)
        if defview:
            lv = user32.FindWindowExW(defview, None, "SysListView32", None)
            if lv:
                return int(lv)
    worker = None
    while True:
        worker = user32.FindWindowExW(None, worker, "WorkerW", None)
        if not worker:
            break
        defview = user32.FindWindowExW(worker, None, "SHELLDLL_DefView", None)
        if defview:
            lv = user32.FindWindowExW(defview, None, "SysListView32", None)
            if lv:
                return int(lv)
    return None


class DesktopAPI:
    """封装桌面图标 ListView 的读写。"""

    def __init__(self) -> None:
        self._hwnd: int | None = None
        self._remote: _Remote | None = None
    def _ensure(self) -> None:
        if self._hwnd and user32.IsWindow(self._hwnd):
            if self._remote is None:
                self._remote = _Remote(self._hwnd)
            return
        self.close()
        hwnd = _find_listview()
        if not hwnd:
            raise DesktopError("未找到桌面图标视图，请确认资源管理器（explorer.exe）正在运行。")
        self._hwnd = hwnd
        self._remote = _Remote(hwnd)

    def close(self) -> None:
        if self._remote:
            self._remote.close()
            self._remote = None
        self._hwnd = None

    @property
    def hwnd(self) -> int:
        self._ensure()
        assert self._hwnd is not None
        return self._hwnd

    def available(self) -> bool:
        try:
            self._ensure()
            return True
        except DesktopError:
            return False

    def canvas_size(self) -> tuple[int, int]:
        self._ensure()
        rect = wintypes.RECT()
        if not user32.GetClientRect(self.hwnd, ctypes.byref(rect)):
            raise DesktopError("无法读取桌面区域尺寸。")
        return max(1, rect.right - rect.left), max(1, rect.bottom - rect.top)

    def dpi(self) -> int:
        try:
            value = int(user32.GetDpiForWindow(self.hwnd))
            return value or 96
        except Exception:
            return 96
    def count(self) -> int:
        return int(user32.SendMessageW(self.hwnd, LVM_GETITEMCOUNT, 0, 0))

    def _item_text(self, index: int) -> str:
        assert self._remote is not None
        remote = self._remote
        lv = LVITEMW()
        lv.mask = LVIF_TEXT
        lv.iItem = index
        lv.iSubItem = 0
        lv.pszText = ctypes.c_void_p(remote.address + TEXT_OFF)
        lv.cchTextMax = TEXT_CHARS
        remote.write(bytes(lv), 0)
        user32.SendMessageW(self.hwnd, LVM_GETITEMTEXTW, index, remote.address)
        raw = remote.read(TEXT_CHARS * 2, TEXT_OFF)
        text = raw.decode("utf-16-le", "ignore").split("\x00", 1)[0]
        return text.strip()

    def _item_pos(self, index: int) -> tuple[int, int]:
        assert self._remote is not None
        addr = self._remote.address + POINT_OFF
        # 失败时 SendMessage 不会写远程缓冲，读回来的是上一轮残留坐标，必须显式拒绝。
        if not user32.SendMessageW(self.hwnd, LVM_GETITEMPOSITION, index, addr):
            raise DesktopError(f"读取第 {index} 个图标的坐标失败。")
        raw = self._remote.read(8, POINT_OFF)
        if len(raw) < 8:
            raise DesktopError("读取图标坐标失败。")
        pt = POINT.from_buffer_copy(raw)
        return int(pt.x), int(pt.y)

    def list_items(self) -> list[DesktopItem]:
        self._ensure()
        total = self.count()
        items: list[DesktopItem] = []
        for i in range(total):
            name = self._item_text(i)
            if not name:
                continue
            x, y = self._item_pos(i)
            items.append(DesktopItem(index=i, name=name, x=x, y=y))
        return items

    def spacing(self) -> tuple[int, int]:
        value = int(user32.SendMessageW(self.hwnd, LVM_GETITEMSPACING, 0, 0))
        cx = value & 0xFFFF
        cy = (value >> 16) & 0xFFFF
        if cx <= 0 or cy <= 0:
            return 96, 96
        return cx, cy

    def _window_style(self) -> int:
        # GetWindowLongPtrW 失败返回 0，与合法的样式值 0 无法区分，只能靠 last error 判定。
        # 若把失败当成 0 继续按位改写，会把桌面视图的其他样式位一并清掉。
        ctypes.set_last_error(0)
        style = int(user32.GetWindowLongPtrW(self.hwnd, GWL_STYLE))
        if style == 0:
            code = ctypes.get_last_error()
            if code != 0:
                raise DesktopError(f"读取桌面视图样式失败（错误码 {code}）。")
        return style

    def auto_arrange(self) -> bool:
        return bool(self._window_style() & LVS_AUTOARRANGE)

    def set_auto_arrange(self, enabled: bool) -> bool:
        """切换桌面「自动排列图标」，返回是否发生了改变。"""
        style = self._window_style()
        current = bool(style & LVS_AUTOARRANGE)
        if current == enabled:
            return False
        new_style = (style | LVS_AUTOARRANGE) if enabled else (style & ~LVS_AUTOARRANGE)
        ctypes.set_last_error(0)
        if int(user32.SetWindowLongPtrW(self.hwnd, GWL_STYLE, new_style)) == 0:
            code = ctypes.get_last_error()
            if code != 0:
                raise DesktopError(f"修改桌面视图样式失败（错误码 {code}）。")
        user32.InvalidateRect(self.hwnd, None, True)
        return True
    def set_positions(self, moves: list[tuple[int, int, int]], disable_auto: bool = True,
                      redraw: bool = True) -> int:
        """moves: [(列表索引, x, y)]，返回成功写入的数量。"""
        if not moves:
            return 0
        self._ensure()
        assert self._remote is not None
        if disable_auto:
            # 关不掉自动排列时仍继续尝试写入：LVM_SETITEMPOSITION32 一旦成功即返回 TRUE，
            # 本层无法区分「写入后被自动排列覆盖」，真实结果交由上层的 applied 计数判断。
            try:
                self.set_auto_arrange(False)
            except DesktopError:
                pass
        hwnd = self.hwnd
        applied = 0
        try:
            user32.SendMessageW(hwnd, WM_SETREDRAW, 0, 0)
            for index, x, y in moves:
                pt = POINT(int(x), int(y))
                self._remote.write(bytes(pt), POINT_OFF)
                ok = user32.SendMessageW(hwnd, LVM_SETITEMPOSITION32, index, self._remote.address + POINT_OFF)
                if ok:
                    applied += 1
        finally:
            user32.SendMessageW(hwnd, WM_SETREDRAW, 1, 0)
            if redraw:
                self.refresh()
        return applied

    def move_item(self, index: int, x: int, y: int) -> bool:
        self._ensure()
        assert self._remote is not None
        pt = POINT(int(x), int(y))
        self._remote.write(bytes(pt), POINT_OFF)
        ok = bool(user32.SendMessageW(self.hwnd, LVM_SETITEMPOSITION32, index,
                                      self._remote.address + POINT_OFF))
        return ok

    def refresh(self) -> None:
        try:
            total = self.count()
            if total:
                user32.SendMessageW(self.hwnd, LVM_REDRAWITEMS, 0, total - 1)
            user32.InvalidateRect(self.hwnd, None, True)
            user32.UpdateWindow(self.hwnd)
        except DesktopError:
            pass

    def __del__(self) -> None:  # pragma: no cover
        try:
            self.close()
        except Exception:
            pass
