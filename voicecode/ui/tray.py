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
            "idle": self._make_icon("#10a37f"),
            "recording": self._make_icon("#f04f5f"),
            "recognizing": self._make_icon("#f6c453"),
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
        outer = (center - radius, center - radius, center + radius, center + radius)
        draw.ellipse(outer, fill="#0b0f14")
        inner = (
            center - radius + 2,
            center - radius + 2,
            center + radius - 2,
            center + radius - 2,
        )
        draw.ellipse(inner, fill=color)
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
        try:
            import customtkinter as ctk

            ctk.set_appearance_mode("Dark")
            root = ctk.CTk()
            root.withdraw()

            toast = ctk.CTkToplevel(root)
            toast.title(title)
            toast.geometry("420x200")
            toast.resizable(False, False)
            toast.configure(fg_color="#0f1115")
            toast.attributes("-topmost", True)

            card = ctk.CTkFrame(
                toast,
                fg_color="#161a22",
                corner_radius=16,
                border_width=1,
                border_color="#2a2f3a",
            )
            card.pack(fill="both", expand=True, padx=16, pady=16)

            ctk.CTkLabel(
                card,
                text=title,
                text_color="#e7e7e7",
                font=ctk.CTkFont("Segoe UI", 14, "bold"),
            ).pack(pady=(14, 6))

            ctk.CTkLabel(
                card,
                text=message,
                text_color="#c9d1de",
                font=ctk.CTkFont("Segoe UI", 12),
                wraplength=360,
                justify="left",
            ).pack(padx=16)

            def on_close() -> None:
                toast.destroy()
                root.destroy()

            ctk.CTkButton(
                card,
                text="知道了",
                fg_color="#10a37f",
                hover_color="#0e8f71",
                text_color="#ffffff",
                width=120,
                command=on_close,
            ).pack(pady=(14, 8))

            toast.after(50, toast.focus_force)
            toast.mainloop()
        except Exception:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning(title, message)
            root.destroy()
