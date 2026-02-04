import tkinter as tk
from tkinter import ttk

from voicecode.config import Config


class SettingsDialog:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._root: tk.Tk | None = None

    def show(self) -> None:
        self._root = tk.Tk()
        root = self._root
        root.title("VoiceCode 设置")
        root.geometry("420x300")
        root.resizable(False, False)

        appid, api_secret, api_key = self._config.get_xfyun_keys()

        fields = [
            ("讯飞 AppID", appid),
            ("讯飞 API Secret", api_secret),
            ("讯飞 API Key", api_key),
            ("快捷键", self._config.get_hotkey()),
            ("窗口标题关键字", self._config.get_window_title_keyword()),
            ("发送按键(enter/ctrl+enter)", self._config.get_send_key()),
        ]

        entries: list[ttk.Entry] = []
        for index, (label, value) in enumerate(fields):
            ttk.Label(root, text=label).grid(
                row=index, column=0, sticky="w", padx=10, pady=6
            )
            entry = ttk.Entry(root, width=40)
            entry.insert(0, value)
            entry.grid(row=index, column=1, padx=10, pady=6)
            entries.append(entry)

        def on_save() -> None:
            self._config.set_xfyun_keys(
                entries[0].get().strip(),
                entries[1].get().strip(),
                entries[2].get().strip(),
            )
            self._config.set_hotkey(entries[3].get().strip())
            self._config.set_window_title_keyword(entries[4].get().strip())
            self._config.set_send_key(entries[5].get().strip())
            self._config.save()
            root.destroy()

        def on_cancel() -> None:
            root.destroy()

        button_frame = ttk.Frame(root)
        button_frame.grid(row=len(fields), column=0, columnspan=2, pady=12)
        ttk.Button(button_frame, text="保存", command=on_save).grid(
            row=0, column=0, padx=8
        )
        ttk.Button(button_frame, text="取消", command=on_cancel).grid(
            row=0, column=1, padx=8
        )

        self._root.mainloop()


def show_settings(config: Config) -> None:
    SettingsDialog(config).show()
