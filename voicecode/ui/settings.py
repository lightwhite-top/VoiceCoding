import customtkinter as ctk

from voicecode.config import Config


THEMES = {
    "dark": {
        "bg": "#0a0c10",
        "card": "#12161c",
        "card_hover": "#181d25",
        "border": "#1e2530",
        "border_focus": "#3b82f6",
        "input_bg": "#0d1014",
        "text": "#f1f5f9",
        "text_secondary": "#94a3b8",
        "text_muted": "#64748b",
        "accent": "#3b82f6",
        "accent_hover": "#2563eb",
        "accent_text": "#ffffff",
        "secondary_btn": "#1e2530",
        "secondary_btn_hover": "#2a3441",
        "success": "#22c55e",
        "warning": "#f59e0b",
        "error": "#ef4444",
        "dropdown_bg": "#0d1014",
        "dropdown_hover": "#1e2530",
    },
    "light": {
        "bg": "#f8fafc",
        "card": "#ffffff",
        "card_hover": "#f1f5f9",
        "border": "#e2e8f0",
        "border_focus": "#2563eb",
        "input_bg": "#f8fafc",
        "text": "#0f172a",
        "text_secondary": "#475569",
        "text_muted": "#64748b",
        "accent": "#2563eb",
        "accent_hover": "#1d4ed8",
        "accent_text": "#ffffff",
        "secondary_btn": "#e2e8f0",
        "secondary_btn_hover": "#cbd5e1",
        "success": "#16a34a",
        "warning": "#d97706",
        "error": "#dc2626",
        "dropdown_bg": "#ffffff",
        "dropdown_hover": "#f1f5f9",
    },
}


def _get_system_theme() -> str:
    try:
        import darkdetect

        return "dark" if darkdetect.isDark() else "light"
    except Exception:
        return "dark"


def _center_window(window: ctk.CTk, width: int, height: int) -> None:
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


def _resolve_theme_mode(mode: str) -> str:
    if mode == "system":
        return _get_system_theme()
    return mode if mode in {"dark", "light"} else "dark"


def _bind_fast_scroll(scroll_frame: ctk.CTkScrollableFrame) -> None:
    try:
        canvas = scroll_frame._parent_canvas
    except Exception:
        return

    def on_mousewheel(event) -> None:
        delta = int(-1 * (event.delta / 120))
        canvas.yview_scroll(delta * 3, "units")

    def on_mousewheel_linux_up(_event) -> None:
        canvas.yview_scroll(-3, "units")

    def on_mousewheel_linux_down(_event) -> None:
        canvas.yview_scroll(3, "units")

    canvas.bind("<MouseWheel>", on_mousewheel)
    canvas.bind("<Button-4>", on_mousewheel_linux_up)
    canvas.bind("<Button-5>", on_mousewheel_linux_down)


def _apply_segmented_text_colors(
    widget: ctk.CTkSegmentedButton, theme: dict, selected_value: str
) -> None:
    """设置分段按钮的文字颜色，选中态用浅色，未选中用深色"""
    try:
        for btn_value, btn in widget._buttons_dict.items():
            if btn_value == selected_value:
                btn.configure(text_color=theme["accent_text"])
            else:
                btn.configure(text_color=theme["text"])
    except Exception:
        pass


class SettingsDialog:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._theme_mode = _resolve_theme_mode(config.get_theme_mode())
        self._theme = THEMES[self._theme_mode]
        self._root: ctk.CTk | None = None
        self._entries: dict[str, ctk.CTkEntry] = {}
        self._send_key_var: ctk.StringVar | None = None
        self._theme_label_var: ctk.StringVar | None = None

    def _apply_theme(self, mode: str) -> None:
        self._theme_mode = _resolve_theme_mode(mode)
        self._theme = THEMES[self._theme_mode]
        ctk.set_appearance_mode("Dark" if self._theme_mode == "dark" else "Light")
        ctk.set_default_color_theme("blue")

    def _collect_values(self) -> dict[str, str]:
        values = {
            "appid": self._config.get_xfyun_keys()[0],
            "api_secret": self._config.get_xfyun_keys()[1],
            "api_key": self._config.get_xfyun_keys()[2],
            "hotkey": self._config.get_hotkey(),
            "send_key": self._config.get_send_key(),
            "theme_label": "跟随系统",
        }

        if self._entries:
            values["appid"] = self._entries["appid"].get().strip()
            values["api_secret"] = self._entries["api_secret"].get().strip()
            values["api_key"] = self._entries["api_key"].get().strip()
            values["hotkey"] = self._entries["hotkey"].get().strip()

        if self._send_key_var is not None:
            values["send_key"] = self._send_key_var.get()

        if self._theme_label_var is not None:
            values["theme_label"] = self._theme_label_var.get()

        return values

    def _on_theme_change(self, selected_label: str) -> None:
        values = self._collect_values()
        values["theme_label"] = selected_label
        theme_value_by_label = {
            "跟随系统": "system",
            "深色": "dark",
            "浅色": "light",
        }
        self._apply_theme(theme_value_by_label.get(selected_label, "system"))
        self._render(values)

    def _render(self, values: dict[str, str] | None = None) -> None:
        root = self._root
        if root is None:
            return

        for child in root.winfo_children():
            child.destroy()

        root.configure(fg_color=self._theme["bg"])
        _center_window(root, 520, 560)

        current = values or {
            "appid": self._config.get_xfyun_keys()[0],
            "api_secret": self._config.get_xfyun_keys()[1],
            "api_key": self._config.get_xfyun_keys()[2],
            "hotkey": self._config.get_hotkey(),
            "send_key": self._config.get_send_key(),
            "theme_label": "跟随系统",
        }

        header = ctk.CTkFrame(root, fg_color="transparent")
        header.pack(fill="x", padx=32, pady=(28, 0))

        ctk.CTkLabel(
            header,
            text="VoiceCode",
            text_color=self._theme["text"],
            font=ctk.CTkFont("Segoe UI", 24, "bold"),
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="语音驱动 OpenCode Desktop",
            text_color=self._theme["text_secondary"],
            font=ctk.CTkFont("Segoe UI", 13),
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        ctk.CTkFrame(
            root,
            fg_color=self._theme["border"],
            height=1,
        ).pack(fill="x", padx=32, pady=(10, 0))

        form_container = ctk.CTkScrollableFrame(
            root,
            fg_color="transparent",
            scrollbar_button_color=self._theme["border"],
            scrollbar_button_hover_color=self._theme["text_muted"],
        )
        form_container.pack(fill="both", expand=True, padx=24, pady=(16, 0))
        _bind_fast_scroll(form_container)

        def add_section_label(text: str) -> None:
            ctk.CTkLabel(
                form_container,
                text=text,
                text_color=self._theme["text_muted"],
                font=ctk.CTkFont("Segoe UI", 11, "bold"),
                anchor="w",
            ).pack(anchor="w", padx=8, pady=(16, 8))

        def build_card() -> ctk.CTkFrame:
            card = ctk.CTkFrame(
                form_container,
                fg_color=self._theme["card"],
                corner_radius=12,
                border_width=1,
                border_color=self._theme["border"],
            )
            card.pack(fill="x", padx=0, pady=(0, 8))
            return card

        def add_divider(parent: ctk.CTkFrame) -> None:
            ctk.CTkFrame(
                parent,
                fg_color=self._theme["border"],
                height=1,
            ).pack(fill="x", padx=16)

        self._entries = {}

        add_section_label("讯飞语音识别")
        voice_card = build_card()

        voice_items = [
            ("AppID", "appid", current["appid"], "填写讯飞 AppID", False),
            (
                "API Secret",
                "api_secret",
                current["api_secret"],
                "填写 API Secret",
                True,
            ),
            ("API Key", "api_key", current["api_key"], "填写 API Key", True),
        ]

        for index, (label, key, value, placeholder, is_secret) in enumerate(
            voice_items
        ):
            field_frame = ctk.CTkFrame(voice_card, fg_color="transparent")
            field_frame.pack(fill="x", padx=16, pady=(12, 12))

            ctk.CTkLabel(
                field_frame,
                text=label,
                text_color=self._theme["text"],
                font=ctk.CTkFont("Segoe UI", 12),
                anchor="w",
                width=120,
            ).pack(side="left")

            entry = ctk.CTkEntry(
                field_frame,
                text_color=self._theme["text"],
                fg_color=self._theme["input_bg"],
                border_color=self._theme["border"],
                border_width=1,
                corner_radius=8,
                placeholder_text=placeholder,
                placeholder_text_color=self._theme["text_muted"],
                height=36,
                show="•" if is_secret else "",
            )
            entry.pack(side="right", fill="x", expand=True)
            if value:
                entry.insert(0, value)
            self._entries[key] = entry

            if index < len(voice_items) - 1:
                add_divider(voice_card)

        add_section_label("快捷键")
        hotkey_card = build_card()

        hotkey_frame = ctk.CTkFrame(hotkey_card, fg_color="transparent")
        hotkey_frame.pack(fill="x", padx=16, pady=(12, 12))

        ctk.CTkLabel(
            hotkey_frame,
            text="快捷键",
            text_color=self._theme["text"],
            font=ctk.CTkFont("Segoe UI", 12),
            anchor="w",
            width=120,
        ).pack(side="left")

        hotkey_entry = ctk.CTkEntry(
            hotkey_frame,
            text_color=self._theme["text"],
            fg_color=self._theme["input_bg"],
            border_color=self._theme["border"],
            border_width=1,
            corner_radius=8,
            placeholder_text="<ctrl>+<alt>+<space>",
            placeholder_text_color=self._theme["text_muted"],
            height=36,
        )
        hotkey_entry.pack(side="right", fill="x", expand=True)
        if current["hotkey"]:
            hotkey_entry.insert(0, current["hotkey"])
        self._entries["hotkey"] = hotkey_entry

        add_section_label("发送设置")
        send_card = build_card()

        send_field = ctk.CTkFrame(send_card, fg_color="transparent")
        send_field.pack(fill="x", padx=16, pady=(12, 12))

        ctk.CTkLabel(
            send_field,
            text="发送按键",
            text_color=self._theme["text"],
            font=ctk.CTkFont("Segoe UI", 12),
            anchor="w",
            width=120,
        ).pack(side="left")

        self._send_key_var = ctk.StringVar(value=current["send_key"])
        send_button = ctk.CTkSegmentedButton(
            send_field,
            values=["enter", "ctrl+enter"],
            variable=self._send_key_var,
            font=ctk.CTkFont("Segoe UI", 11),
            fg_color=self._theme["input_bg"],
            selected_color=self._theme["accent"],
            selected_hover_color=self._theme["accent_hover"],
            unselected_color=self._theme["input_bg"],
            unselected_hover_color=self._theme["card_hover"],
            text_color=self._theme["text"],
            text_color_disabled=self._theme["text_muted"],
            corner_radius=8,
        )
        send_button.pack(side="right")

        def on_send_key_change(value: str) -> None:
            _apply_segmented_text_colors(send_button, self._theme, value)

        send_button.configure(command=on_send_key_change)
        _apply_segmented_text_colors(send_button, self._theme, current["send_key"])

        ctk.CTkLabel(
            send_card,
            text="如果 Enter 无法发送消息，请切换为 ctrl+enter",
            text_color=self._theme["text_muted"],
            font=ctk.CTkFont("Segoe UI", 11),
            anchor="w",
        ).pack(anchor="w", padx=16, pady=(0, 12))

        add_section_label("外观")
        appearance_card = build_card()

        appearance_field = ctk.CTkFrame(appearance_card, fg_color="transparent")
        appearance_field.pack(fill="x", padx=16, pady=(12, 12))

        ctk.CTkLabel(
            appearance_field,
            text="主题模式",
            text_color=self._theme["text"],
            font=ctk.CTkFont("Segoe UI", 12),
            anchor="w",
            width=120,
        ).pack(side="left")

        theme_label_by_value = {
            "system": "跟随系统",
            "dark": "深色",
            "light": "浅色",
        }
        current_label = current.get("theme_label") or theme_label_by_value.get(
            self._config.get_theme_mode(), "跟随系统"
        )
        self._theme_label_var = ctk.StringVar(value=current_label)
        theme_button = ctk.CTkSegmentedButton(
            appearance_field,
            values=["跟随系统", "深色", "浅色"],
            variable=self._theme_label_var,
            command=self._on_theme_change,
            font=ctk.CTkFont("Segoe UI", 11),
            fg_color=self._theme["input_bg"],
            selected_color=self._theme["accent"],
            selected_hover_color=self._theme["accent_hover"],
            unselected_color=self._theme["input_bg"],
            unselected_hover_color=self._theme["card_hover"],
            text_color=self._theme["text"],
            text_color_disabled=self._theme["text_muted"],
            corner_radius=8,
        )
        theme_button.pack(side="right")

        def on_theme_button_change(value: str) -> None:
            _apply_segmented_text_colors(theme_button, self._theme, value)
            self._on_theme_change(value)

        theme_button.configure(command=on_theme_button_change)
        _apply_segmented_text_colors(theme_button, self._theme, current_label)

        ctk.CTkLabel(
            appearance_card,
            text="主题切换将即时生效，保存后会持久化",
            text_color=self._theme["text_muted"],
            font=ctk.CTkFont("Segoe UI", 11),
            anchor="w",
        ).pack(anchor="w", padx=16, pady=(0, 12))

        footer = ctk.CTkFrame(root, fg_color="transparent")
        footer.pack(fill="x", padx=32, pady=(16, 24))

        def on_save() -> None:
            self._config.set_xfyun_keys(
                self._entries["appid"].get().strip(),
                self._entries["api_secret"].get().strip(),
                self._entries["api_key"].get().strip(),
            )
            self._config.set_hotkey(self._entries["hotkey"].get().strip())
            if self._send_key_var is not None:
                self._config.set_send_key(self._send_key_var.get())
            if self._theme_label_var is not None:
                label = self._theme_label_var.get()
                theme_value_by_label = {
                    "跟随系统": "system",
                    "深色": "dark",
                    "浅色": "light",
                }
                self._config.set_theme_mode(theme_value_by_label.get(label, "system"))
            self._config.save()
            root.destroy()

        def on_cancel() -> None:
            root.destroy()

        ctk.CTkButton(
            footer,
            text="取消",
            fg_color=self._theme["secondary_btn"],
            hover_color=self._theme["secondary_btn_hover"],
            text_color=self._theme["text"],
            font=ctk.CTkFont("Segoe UI", 12),
            width=100,
            height=38,
            corner_radius=8,
            command=on_cancel,
        ).pack(side="left")

        ctk.CTkButton(
            footer,
            text="保存设置",
            fg_color=self._theme["accent"],
            hover_color=self._theme["accent_hover"],
            text_color=self._theme["accent_text"],
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            width=120,
            height=38,
            corner_radius=8,
            command=on_save,
        ).pack(side="right")

    def show(self) -> None:
        self._apply_theme(self._config.get_theme_mode())
        root = ctk.CTk()
        root.title("VoiceCode")
        root.resizable(False, False)
        self._root = root
        self._render()
        root.mainloop()


def show_settings(config: Config) -> None:
    SettingsDialog(config).show()
