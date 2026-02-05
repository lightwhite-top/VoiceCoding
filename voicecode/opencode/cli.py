import ctypes
from ctypes.wintypes import RECT
import re
import time
from typing import List

try:
    from pywinauto import Desktop
    from pywinauto.keyboard import send_keys
except Exception:  # pragma: no cover
    Desktop = None
    send_keys = None



class OpenCodeCLI:
    """
    OpenCode Desktop 客户端控制器。
    
    使用 pywinauto 和 UI Automation (UIA) 技术，模拟用户操作，
    将语音识别结果发送到 OpenCode Desktop 的输入框中。
    """
    def __init__(
        self,
        send_key: str = "enter",
    ) -> None:
        """
        初始化控制器。
        
        Args:
            send_key: 发送消息的快捷键，支持 "enter" 或 "ctrl+enter"。
        """
        self._send_key = (send_key or "enter").strip().lower()
        self.last_error: str = ""

    def send_message(self, text: str, timeout: int = 30) -> bool:
        """
        发送文本消息到 OpenCode Desktop。
        
        Args:
            text: 要发送的文本内容
            timeout: 操作超时时间（目前主要用于预留接口，内部暂未严格使用此 timeout）
            
        Returns:
            bool: 发送成功返回 True，失败返回 False。失败原因保存在 last_error 属性中。
        """
        message = (text or "").strip()
        if not message:
            self.last_error = "文本为空"
            return False

        ok = self._send_to_opencode_desktop_input(message)
        if not ok and not self.last_error:
            self.last_error = "无法定位或聚焦 OpenCode 输入框"
        return ok

    def _send_to_opencode_desktop_input(self, message: str) -> bool:
        """
        核心逻辑：查找输入框并写入文本。
        
        策略：
        1. 使用 pywinauto (UIA) 查找 OpenCode 窗口。
        2. 遍历窗口内的所有控件 (Descendants)。
        3. 筛选出可能是输入框的控件 (Edit/Document 类型，且位于窗口底部)。
        4. 尝试聚焦并输入文本。
        
        只使用 UI Automation，不使用任何坐标点击方案，以提高稳定性。
        """

        self.last_error = ""

        if Desktop is None or send_keys is None:
            self.last_error = "未安装 pywinauto（请先 uv sync）"
            return False

        win = self._find_opencode_window_uia()
        if win is None:
            return False

        # 在部分应用里，先 restore 再 focus 更稳
        try:
            win.restore()
        except Exception:
            pass
        try:
            win.set_focus()
        except Exception:
            # 仍然尝试继续（后续控件 set_focus 可能成功）
            pass

        try:
            win_rect = win.rectangle()
        except Exception:
            win_rect = None

        candidates = []
        for control_type in ("Edit", "Document"):
            try:
                candidates.extend(win.descendants(control_type=control_type))
            except Exception:
                pass

        # Some Electron apps (Monaco/WebView) may not expose Edit/Document; fall back to all
        if not candidates:
            try:
                candidates = win.descendants()
            except Exception:
                self.last_error = "UIA 无法枚举窗口控件（可能权限不一致）。请尝试以管理员身份启动 VoiceCode。"
                return False

        if not candidates:
            self.last_error = "UIA 未找到任何可用控件"
            return False

        # Quick diagnostic: if we still fail later, expose some counts
        total_candidates = len(candidates)

        filtered = []
        for ctrl in candidates:
            try:
                if hasattr(ctrl, "is_visible") and not ctrl.is_visible():
                    continue
            except Exception:
                pass
            try:
                if hasattr(ctrl, "is_enabled") and not ctrl.is_enabled():
                    continue
            except Exception:
                pass
            # Filter out obviously off-screen (pywinauto sometimes reports huge negative coords)
            try:
                rect = ctrl.rectangle()
                if rect.width() <= 0 or rect.height() <= 0:
                    continue
                if rect.right < -10000 or rect.bottom < -10000:
                    continue
            except Exception:
                pass
            filtered.append(ctrl)

        if filtered:
            candidates = filtered

        def rect_of(ctrl):
            try:
                return ctrl.rectangle()
            except Exception:
                return None

        def in_bottom_area(rect) -> bool:
            if win_rect is None:
                return True
            bottom_band = max(220, int(win_rect.height() * 0.35))
            return rect.bottom >= (win_rect.bottom - bottom_band)

        # Prefer candidates near the bottom that look like an input box
        bottom_candidates = []
        other_candidates = []
        for ctrl in candidates:
            rect = rect_of(ctrl)
            if rect is None:
                continue
            if rect.height() <= 0 or rect.width() <= 0:
                continue
            # 放宽过滤条件：只排除明显不是输入框的控件
            if win_rect is not None:
                # 排除占据大部分窗口高度的控件（可能是主内容区）
                if rect.height() > int(win_rect.height() * 0.6):
                    continue
                # 排除太窄的控件（可能是按钮或图标）
                if rect.width() < int(win_rect.width() * 0.15):
                    continue
            if in_bottom_area(rect):
                bottom_candidates.append((ctrl, rect))
            else:
                other_candidates.append((ctrl, rect))

        # Sort by: supports set_edit_text first, then bottom-most
        def sort_key(item) -> tuple[int, int]:
            ctrl, rect = item
            return (1 if hasattr(ctrl, "set_edit_text") else 0, rect.bottom)

        bottom_candidates.sort(key=sort_key, reverse=True)
        other_candidates.sort(key=sort_key, reverse=True)

        def try_write(ctrl) -> bool:
            # 尝试聚焦控件，但不要因为聚焦失败就放弃
            try:
                ctrl.set_focus()
            except Exception:
                pass  # 继续尝试写入

            # Electron/DOM 输入框常见问题：set_edit_text / ValuePattern 只改了可访问性值，
            # 但不触发真正的 input 事件，导致发送按钮不可用。
            # 因此这里优先走"模拟键盘输入"的路径。
            try:
                time.sleep(0.05)
            except Exception:
                pass

            # Clear existing text
            try:
                ctrl.type_keys("^a{BACKSPACE}", set_foreground=False)
            except Exception:
                if send_keys is not None:
                    try:
                        send_keys("^a{BACKSPACE}")
                    except Exception:
                        pass

            try:
                try:
                    ctrl.type_keys(message, with_spaces=True, set_foreground=False)
                except Exception:
                    if send_keys is None:
                        return False
                    send_keys(message, with_spaces=True)
                return True
            except Exception:
                return False

        for ctrl, _ in bottom_candidates:
            if try_write(ctrl):
                return self._submit_message()

        for ctrl, _ in other_candidates:
            if try_write(ctrl):
                return self._submit_message()

        self.last_error = (
            f"UIA 未能找到可写入的输入控件，"
            f"总控件数={total_candidates}，底部候选={len(bottom_candidates)}，其他候选={len(other_candidates)}。"
        )
        return False

    def _submit_message(self) -> bool:
        """
        模拟按键提交消息。
        根据配置发送 Enter 或 Ctrl+Enter。
        """
        # 发送：默认 Enter；如 OpenCode 是多行输入可改为 ctrl+enter
        try:
            time.sleep(0.05)
        except Exception:
            pass

        key = self._send_key
        if send_keys is None:
            self.last_error = "pywinauto keyboard 不可用"
            return False

        try:
            if key == "ctrl+enter":
                send_keys("^{ENTER}")
            else:
                send_keys("{ENTER}")
            return True
        except Exception:
            self.last_error = "已写入输入框，但无法触发发送按键"
            return False

    @staticmethod
    def debug_dump_opencode_controls(keyword: str = "OpenCode", limit: int = 20) -> str:
        """
        调试工具：打印 OpenCode 窗口的控件树信息。
        用于开发调试，分析界面结构，寻找输入框特征。
        
        Args:
            keyword: 窗口标题匹配关键字
            limit: 打印 Edit 控件详情的最大数量
        """

        if Desktop is None:
            return "pywinauto 未安装"

        title_re = re.compile(r".*" + re.escape(keyword) + r".*", re.IGNORECASE)
        try:
            desktop = Desktop(backend="uia")
            wins = desktop.windows(title_re=title_re)
        except Exception as exc:
            return f"枚举窗口失败：{exc}"

        if not wins:
            return f"未找到窗口（标题包含：{keyword}）"

        wins_sorted = []
        for w in wins:
            try:
                ct = w.element_info.control_type
            except Exception:
                ct = ""
            score = 1 if ct == "Window" else 0
            wins_sorted.append((score, w))
        wins_sorted.sort(key=lambda t: t[0], reverse=True)
        win = wins_sorted[0][1]

        try:
            controls = win.descendants()
        except Exception as exc:
            return f"无法枚举控件：{exc}"

        counts: dict[str, int] = {}
        for c in controls:
            try:
                ct = c.element_info.control_type
            except Exception:
                ct = "unknown"
            counts[ct] = counts.get(ct, 0) + 1

        lines = [
            f"窗口标题: {win.window_text()}",
            f"窗口类型: {getattr(win.element_info, 'control_type', '')}",
            f"控件总数: {len(controls)}",
        ]
        lines.append("控件类型统计(Top):")
        for k, v in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:10]:
            lines.append(f"- {k}: {v}")

        try:
            edits = win.descendants(control_type="Edit")
        except Exception:
            edits = []
        lines.append(f"Edit 控件数: {len(edits)}")
        for e in edits[: max(1, limit)]:
            try:
                r = e.rectangle()
                lines.append(
                    f"- Edit rect=({r.left},{r.top},{r.right},{r.bottom}) text={e.window_text()!r}"
                )
            except Exception:
                lines.append("- Edit (无法获取 rect/text)")

        return "\n".join(lines)

    def _find_opencode_window_uia(self):
        """
        查找 OpenCode Desktop 的主窗口。
        
        优先通过 Win32 API 查找窗口句柄 (HWND)，然后通过 pywinauto 包装为 WindowSpecification。
        这种混合方式比纯 UIA 查找更快且更稳定。
        """
        if Desktop is None:
            self.last_error = "未安装 pywinauto（请先 uv sync）"
            return None

        deadline = time.monotonic() + 6.0
        last_hwnd = 0

        while time.monotonic() < deadline:
            # 1) Prefer: find HWND via Win32, then bind via UIA by handle
            hwnd = self._find_hwnd_candidate()
            if hwnd:
                last_hwnd = hwnd
                try:
                    win = Desktop(backend="uia").window(handle=hwnd)
                    if hasattr(win, "exists") and not win.exists(timeout=0.2):
                        raise RuntimeError("not found")
                    return win
                except Exception:
                    # keep retrying
                    pass

            time.sleep(0.2)

        if last_hwnd:
            self.last_error = "找到了窗口句柄但 UIA 无法访问（可能权限不一致）。请尝试以管理员身份启动 VoiceCode。"
        else:
            self.last_error = "未找到 OpenCode 窗口。请确认 OpenCode Desktop 已打开。"
        return None

    @staticmethod
    def _find_hwnd_candidate() -> int:
        """
        使用 Win32 API 遍历所有窗口，查找属于 OpenCode 进程的窗口句柄。
        
        Returns:
            int: 找到的窗口句柄 (HWND)，未找到返回 0。
        """
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        matches: list[int] = []

        def looks_like_window(hwnd: int) -> bool:
            """过滤掉太小的窗口（悬浮窗、隐藏窗口等）。"""
            rect = RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return False
            return (rect.right - rect.left) > 100 and (rect.bottom - rect.top) > 100

        def get_process_image(hwnd: int) -> str:
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if not pid.value:
                return ""

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value
            )
            if not handle:
                return ""
            try:
                buf_len = ctypes.c_ulong(32768)
                buf = ctypes.create_unicode_buffer(buf_len.value)
                if kernel32.QueryFullProcessImageNameW(
                    handle, 0, buf, ctypes.byref(buf_len)
                ):
                    return buf.value
                return ""
            finally:
                kernel32.CloseHandle(handle)

        def looks_like_opencode_process(path: str) -> bool:
            low = (path or "").lower()
            if not low:
                return False
            return ("opencode" in low) or ("open-code" in low) or ("open code" in low)

        def enum_proc(hwnd, lparam):
            try:
                if not user32.IsWindowVisible(hwnd):
                    return True
                if not looks_like_window(hwnd):
                    return True

                proc_image = get_process_image(hwnd)
                if looks_like_opencode_process(proc_image):
                    matches.append(hwnd)
                    return False

                return True
            except Exception:
                # Must not raise inside EnumWindows callback
                return True

        cb = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(
            enum_proc
        )
        user32.EnumWindows(cb, 0)
        return matches[0] if matches else 0
