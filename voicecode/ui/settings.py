import customtkinter as ctk

from voicecode.config import Config


THEME = {
    "bg": "#0f1115",
    "card": "#161a22",
    "border": "#2a2f3a",
    "text": "#e7e7e7",
    "muted": "#9aa3b2",
    "accent": "#10a37f",
    "accent_hover": "#0e8f71",
}


def _apply_theme() -> None:
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("dark-blue")


class SettingsDialog:
    def __init__(self, config: Config) -> None:
        self._config = config

    def show(self) -> None:
        _apply_theme()

        root = ctk.CTk()
        root.title("VoiceCode 设置")
        root.geometry("560x440")
        root.resizable(False, False)
        root.configure(fg_color=THEME["bg"])

        title = ctk.CTkLabel(
            root,
            text="VoiceCode 设置",
            text_color=THEME["text"],
            font=ctk.CTkFont("Segoe UI", 20, "bold"),
        )
        title.pack(pady=(22, 4))

        subtitle = ctk.CTkLabel(
            root,
            text="语音驱动 OpenCode Desktop",
            text_color=THEME["muted"],
            font=ctk.CTkFont("Segoe UI", 12),
        )
        subtitle.pack(pady=(0, 18))

        card = ctk.CTkFrame(
            root,
            fg_color=THEME["card"],
            corner_radius=16,
            border_width=1,
            border_color=THEME["border"],
        )
        card.pack(fill="x", padx=20, pady=(0, 16))

        appid, api_secret, api_key = self._config.get_xfyun_keys()

        fields = [
            ("讯飞 AppID", appid, "填写你的 AppID"),
            ("讯飞 API Secret", api_secret, "填写 API Secret"),
            ("讯飞 API Key", api_key, "填写 API Key"),
            ("快捷键", self._config.get_hotkey(), "例如 <ctrl>+<alt>+<space>"),
            (
                "窗口标题关键字",
                self._config.get_window_title_keyword(),
                "例如 OpenCode",
            ),
        ]

        entries: list[ctk.CTkEntry] = []
        for row, (label, value, placeholder) in enumerate(fields):
            ctk.CTkLabel(
                card,
                text=label,
                text_color=THEME["text"],
                font=ctk.CTkFont("Segoe UI", 12, "bold"),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=18, pady=(12, 6))

            entry = ctk.CTkEntry(
                card,
                width=320,
                text_color=THEME["text"],
                fg_color="#0c0f14",
                border_color=THEME["border"],
                placeholder_text=placeholder,
            )
            if value:
                entry.insert(0, value)
            entry.grid(row=row, column=1, sticky="e", padx=18, pady=(12, 6))
            entries.append(entry)

        ctk.CTkLabel(
            card,
            text="发送按键",
            text_color=THEME["text"],
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            anchor="w",
        ).grid(row=len(fields), column=0, sticky="w", padx=18, pady=(12, 6))

        send_key_menu = ctk.CTkOptionMenu(
            card,
            values=["enter", "ctrl+enter"],
            fg_color="#0c0f14",
            button_color=THEME["accent"],
            button_hover_color=THEME["accent_hover"],
            text_color=THEME["text"],
            dropdown_fg_color="#11151d",
            dropdown_text_color=THEME["text"],
        )
        send_key_menu.set(self._config.get_send_key())
        send_key_menu.grid(row=len(fields), column=1, sticky="e", padx=18, pady=(12, 6))

        tip = ctk.CTkLabel(
            card,
            text="Enter 无法发送时，切换为 ctrl+enter",
            text_color=THEME["muted"],
            font=ctk.CTkFont("Segoe UI", 11),
        )
        tip.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="w", padx=18)

        action = ctk.CTkFrame(root, fg_color=THEME["bg"])
        action.pack(fill="x", padx=20, pady=(0, 16))

        def on_save() -> None:
            self._config.set_xfyun_keys(
                entries[0].get().strip(),
                entries[1].get().strip(),
                entries[2].get().strip(),
            )
            self._config.set_hotkey(entries[3].get().strip())
            self._config.set_window_title_keyword(entries[4].get().strip())
            self._config.set_send_key(send_key_menu.get())
            self._config.save()
            root.destroy()

        def on_cancel() -> None:
            root.destroy()

        save_button = ctk.CTkButton(
            action,
            text="保存",
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color="#ffffff",
            width=140,
            height=36,
            command=on_save,
        )
        save_button.pack(side="right", padx=(8, 0))

        cancel_button = ctk.CTkButton(
            action,
            text="取消",
            fg_color="#1e232d",
            hover_color="#2a2f3a",
            text_color=THEME["text"],
            width=140,
            height=36,
            command=on_cancel,
        )
        cancel_button.pack(side="right", padx=(0, 8))

        root.mainloop()


def show_settings(config: Config) -> None:
    SettingsDialog(config).show()
