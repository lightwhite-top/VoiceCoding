from __future__ import annotations

import threading
from typing import Callable

from PIL import Image, ImageDraw
import pystray


class TrayIcon:
    def __init__(
        self,
        on_settings: Callable[[], None] | None = None,
        on_reset: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
    ) -> None:
        self._on_settings = on_settings
        self._on_reset = on_reset
        self._on_quit = on_quit
        self._icons = {
            "idle": self._make_icon("#2ecc71"),
            "recording": self._make_icon("#e74c3c"),
            "recognizing": self._make_icon("#f1c40f"),
        }
        menu = pystray.Menu(
            pystray.MenuItem("设置", self._handle_settings),
            pystray.MenuItem("重置", self._handle_reset),
            pystray.MenuItem("退出", self._handle_quit),
        )
        self._icon = pystray.Icon("VoiceCode", self._icons["idle"], "VoiceCode", menu)

    def run(self) -> None:
        self._icon.run()

    def run_detached(self) -> None:
        self._icon.run_detached()
        try:
            self._icon.visible = True
        except Exception:
            pass

    def stop(self) -> None:
        self._icon.stop()

    def set_status(self, status: str) -> None:
        icon = self._icons.get(status, self._icons["idle"])
        self._icon.icon = icon
        try:
            self._icon.update_menu()
        except Exception:
            pass

    def show_message(self, title: str, message: str) -> None:
        try:
            if hasattr(self._icon, "notify") and callable(self._icon.notify):
                try:
                    self._icon.notify(title, message)
                except TypeError:
                    self._icon.notify(message, title)
            else:
                self._fallback_message(title, message)
        except Exception:
            self._fallback_message(title, message)

    @staticmethod
    def _make_icon(color: str, size: int = 32) -> Image.Image:
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        radius = size // 2 - 2
        center = size // 2
        draw.ellipse(
            (center - radius, center - radius, center + radius, center + radius),
            fill=color,
        )
        return image

    def _handle_settings(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        if self._on_settings:
            threading.Thread(target=self._on_settings, daemon=True).start()

    def _handle_reset(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        if self._on_reset:
            self._on_reset()

    def _handle_quit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        if self._on_quit:
            self._on_quit()

    @staticmethod
    def _fallback_message(title: str, message: str) -> None:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(title, message)
        root.destroy()
