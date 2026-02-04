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
    def __init__(
        self,
        window_title_keyword: str = "OpenCode",
        send_key: str = "enter",
    ) -> None:
        self._window_title_keyword = window_title_keyword or "OpenCode"
        self._send_key = (send_key or "enter").strip().lower()
        self.last_error: str = ""

    def send_message(self, text: str, timeout: int = 30) -> bool:
        message = (text or "").strip()
        if not message:
            self.last_error = "文本为空"
            return False

        ok = self._send_to_opencode_desktop_input(message)
        if not ok and not self.last_error:
            self.last_error = "无法定位或聚焦 OpenCode 输入框"
        return ok

    def _send_to_opencode_desktop_input(self, message: str) -> bool:
        """只使用 UI Automation，不使用任何点击/坐标方案。

        成功标准：识别文本出现在 OpenCode Desktop 输入框中。
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
            if win_rect is not None:
                if rect.height() > int(win_rect.height() * 0.45):
                    continue
                if rect.width() < int(win_rect.width() * 0.30):
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
            try:
                ctrl.set_focus()
            except Exception:
                return False

            # Electron/DOM 输入框常见问题：set_edit_text / ValuePattern 只改了可访问性值，
            # 但不触发真正的 input 事件，导致发送按钮不可用。
            # 因此这里优先走“模拟键盘输入”的路径。
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
            "UIA 未能找到可写入的输入控件（无法 set_edit_text/ValuePattern/type_keys），"
            f"候选控件数={total_candidates}。"
        )
        return False

    def _submit_message(self) -> bool:
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
        """用于诊断：列出匹配窗口的控件类型统计与 Edit 控件信息。"""

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
        if Desktop is None:
            self.last_error = "未安装 pywinauto（请先 uv sync）"
            return None

        keyword = self._window_title_keyword
        title_re = re.compile(r".*" + re.escape(keyword) + r".*", re.IGNORECASE)

        deadline = time.monotonic() + 6.0
        last_hwnd = 0

        while time.monotonic() < deadline:
            # 1) Prefer: find HWND via Win32, then bind via UIA by handle
            hwnd = self._find_hwnd_candidate(keyword)
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

            # 2) Fallback: UIA title match (may have multiple matches)
            try:
                desktop = Desktop(backend="uia")
                wins = desktop.windows(title_re=title_re)
                if wins:
                    # Prefer a visible, large Window
                    best = None
                    best_score = -1
                    for w in wins:
                        try:
                            ct = w.element_info.control_type
                        except Exception:
                            ct = ""
                        try:
                            rect = w.rectangle()
                            area = max(0, rect.width()) * max(0, rect.height())
                            on_screen = rect.right > 0 and rect.bottom > 0
                        except Exception:
                            area = 0
                            on_screen = False
                        try:
                            visible = w.is_visible()
                        except Exception:
                            visible = False

                        score = 0
                        if ct == "Window":
                            score += 1_000_000
                        if visible:
                            score += 100_000
                        if on_screen:
                            score += 10_000
                        score += area

                        if score > best_score:
                            best_score = score
                            best = w

                    if best is not None:
                        return best
            except Exception:
                pass

            time.sleep(0.2)

        if last_hwnd:
            self.last_error = "找到了窗口句柄但 UIA 无法访问（可能权限不一致）。请尝试以管理员身份启动 VoiceCode。"
        else:
            self.last_error = f"未找到窗口（标题包含：{keyword}）。请确认 OpenCode Desktop 已打开，或调整窗口标题关键字。"
        return None

    @staticmethod
    def _find_hwnd_candidate(keyword: str) -> int:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        matches: list[int] = []

        def get_title(hwnd: int) -> str:
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return ""
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value

        def looks_like_window(hwnd: int) -> bool:
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

                title = get_title(hwnd)
                if title and keyword.lower() in title.lower():
                    matches.append(hwnd)
                    return False

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
