from __future__ import annotations

import threading
from typing import Callable

from PIL import Image, ImageDraw
import pystray


def _resolve_theme_mode(mode: str) -> str:
    if mode == "system":
        try:
            import darkdetect

            return "dark" if darkdetect.isDark() else "light"
        except Exception:
            return "dark"
    return mode if mode in {"dark", "light"} else "dark"


def _get_theme_palette(mode: str) -> dict[str, str]:
    if _resolve_theme_mode(mode) == "light":
        return {
            "bg": "#f8fafc",
            "card": "#ffffff",
            "border": "#e2e8f0",
            "text": "#0f172a",
            "text_secondary": "#475569",
            "accent": "#2563eb",
            "accent_hover": "#1d4ed8",
        }
    return {
        "bg": "#0a0c10",
        "card": "#12161c",
        "border": "#1e2530",
        "text": "#f1f5f9",
        "text_secondary": "#94a3b8",
        "accent": "#3b82f6",
        "accent_hover": "#2563eb",
    }


def _center_toplevel(window, width: int, height: int) -> None:
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


class TrayIcon:
    def __init__(
        self,
        on_settings: Callable[[], None] | None = None,
        on_reset: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
        theme_mode_getter: Callable[[], str] | None = None,
    ) -> None:
        self._on_settings = on_settings
        self._on_reset = on_reset
        self._on_quit = on_quit
        self._theme_mode_getter = theme_mode_getter
        self._icons = {
            "idle": self._make_icon("#22c55e"),
            "recording": self._make_icon("#ef4444"),
            "recognizing": self._make_icon("#f59e0b"),
        }
        menu = pystray.Menu(
            pystray.MenuItem("设置", self._handle_settings),
            pystray.Menu.SEPARATOR,
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

    def _get_theme_mode(self) -> str:
        if not self._theme_mode_getter:
            return "system"
        try:
            return self._theme_mode_getter() or "system"
        except Exception:
            return "system"

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

    def _handle_settings(self, icon, item) -> None:
        if self._on_settings:
            threading.Thread(target=self._on_settings, daemon=True).start()

    def _handle_reset(self, icon, item) -> None:
        if self._on_reset:
            self._on_reset()

    def _handle_quit(self, icon, item) -> None:
        if self._on_quit:
            self._on_quit()

    def _fallback_message(self, title: str, message: str) -> None:
        try:
            import customtkinter as ctk

            theme_mode = self._get_theme_mode()
            theme = _get_theme_palette(theme_mode)
            ctk.set_appearance_mode(
                "Light" if _resolve_theme_mode(theme_mode) == "light" else "Dark"
            )
            root = ctk.CTk()
            root.withdraw()

            toast = ctk.CTkToplevel(root)
            toast.title(title)
            toast.resizable(False, False)
            toast.configure(fg_color=theme["bg"])
            toast.attributes("-topmost", True)

            width = 400
            height = 180
            _center_toplevel(toast, width, height)

            card = ctk.CTkFrame(
                toast,
                fg_color=theme["card"],
                corner_radius=12,
                border_width=1,
                border_color=theme["border"],
            )
            card.pack(fill="both", expand=True, padx=16, pady=16)

            ctk.CTkLabel(
                card,
                text=title,
                text_color=theme["text"],
                font=ctk.CTkFont("Segoe UI", 14, "bold"),
            ).pack(pady=(14, 6))

            ctk.CTkLabel(
                card,
                text=message,
                text_color=theme["text_secondary"],
                font=ctk.CTkFont("Segoe UI", 12),
                wraplength=340,
                justify="center",
            ).pack(padx=16)

            def on_close() -> None:
                toast.destroy()
                root.destroy()

            ctk.CTkButton(
                card,
                text="知道了",
                fg_color=theme["accent"],
                hover_color=theme["accent_hover"],
                text_color="#ffffff",
                width=100,
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
