import threading
from typing import Callable, Iterable

from pynput import keyboard


class HotkeyListener:
    def __init__(
        self,
        hotkey: str = "<ctrl>+<alt>+<space>",
        on_activate: Callable[[], None] | None = None,
        on_deactivate: Callable[[], None] | None = None,
        timeout: int = 5,
    ) -> None:
        self._hotkey = hotkey
        self._hotkey_keys = list(keyboard.HotKey.parse(self._normalize_hotkey(hotkey)))
        self._hotkey_handler = keyboard.HotKey(self._hotkey_keys, self._handle_activate)
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate
        self._timeout = timeout
        self._pressed: set = set()
        self._active = False
        self._listener: keyboard.Listener | None = None
        self._timer: threading.Timer | None = None

    def start(self) -> None:
        if self._listener:
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._cancel_timer()
        self._pressed.clear()
        self._active = False

    def update_hotkey(self, hotkey: str) -> None:
        self._hotkey = hotkey
        self._hotkey_keys = list(keyboard.HotKey.parse(self._normalize_hotkey(hotkey)))
        self._hotkey_handler = keyboard.HotKey(self._hotkey_keys, self._handle_activate)
        self._pressed.clear()
        self._active = False

    @staticmethod
    def _normalize_hotkey(hotkey: str) -> str:
        value = (hotkey or "").strip()
        if not value:
            return "<ctrl>+<alt>+<space>"

        if "<" in value:
            return value

        tokens = [token.strip() for token in value.split("+") if token.strip()]
        normalized = []
        for token in tokens:
            lower = token.lower()
            if lower in {"ctrl", "alt", "shift", "cmd", "win"}:
                key_name = "cmd" if lower == "win" else lower
                normalized.append(f"<{key_name}>")
            elif lower == "space":
                normalized.append("<space>")
            else:
                normalized.append(lower)

        return "+".join(normalized)

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key is None:
            return
        if self._listener:
            key = self._listener.canonical(key)
        self._pressed.add(key)
        self._hotkey_handler.press(key)

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key is None:
            return
        if self._listener:
            key = self._listener.canonical(key)
        if key in self._pressed:
            self._pressed.remove(key)
        self._hotkey_handler.release(key)
        if self._active and not self._hotkey_handler._state:
            self._deactivate()

    def _handle_activate(self) -> None:
        if self._active:
            return
        self._active = True
        self._start_timer()
        if self._on_activate:
            self._on_activate()

    def _start_timer(self) -> None:
        self._cancel_timer()
        self._timer = threading.Timer(self._timeout, self._deactivate)
        self._timer.daemon = True
        self._timer.start()

    def _cancel_timer(self) -> None:
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _deactivate(self) -> None:
        if not self._active:
            return
        self._active = False
        self._cancel_timer()
        if self._on_deactivate:
            self._on_deactivate()
