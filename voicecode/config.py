import base64
import json
from pathlib import Path
from typing import Tuple


class Config:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or self._default_path()
        self._data = self._default_data()

    @staticmethod
    def _default_path() -> Path:
        return Path.home() / ".voicecode" / "config.json"

    @staticmethod
    def _default_data() -> dict:
        return {
            "xfyun_appid": "",
            "xfyun_api_secret": "",
            "xfyun_api_key": "",
            "hotkey": "<ctrl>+<alt>+<space>",
            "window_title_keyword": "",
            # OpenCode Desktop 默认通常 Enter 发送；如需要可改为 ctrl+enter
            "send_key": "enter",
        }

    def load(self) -> None:
        if not self._path.exists():
            self._data = self._default_data()
            return

        raw = self._path.read_text(encoding="utf-8")
        data = json.loads(raw)
        self._data = self._default_data()

        self._data["xfyun_appid"] = self._decode(data.get("xfyun_appid", ""))
        self._data["xfyun_api_secret"] = self._decode(data.get("xfyun_api_secret", ""))
        self._data["xfyun_api_key"] = self._decode(data.get("xfyun_api_key", ""))
        self._data["hotkey"] = data.get("hotkey", self._data["hotkey"])
        self._data["window_title_keyword"] = data.get("window_title_keyword", "")
        self._data["send_key"] = data.get("send_key", "enter")

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "xfyun_appid": self._encode(self._data.get("xfyun_appid", "")),
            "xfyun_api_secret": self._encode(self._data.get("xfyun_api_secret", "")),
            "xfyun_api_key": self._encode(self._data.get("xfyun_api_key", "")),
            "hotkey": self._data.get("hotkey", "<ctrl>+<alt>+<space>"),
            "window_title_keyword": self._data.get("window_title_keyword", ""),
            "send_key": self._data.get("send_key", "enter"),
        }
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def set_xfyun_keys(self, appid: str, api_secret: str, api_key: str) -> None:
        self._data["xfyun_appid"] = appid or ""
        self._data["xfyun_api_secret"] = api_secret or ""
        self._data["xfyun_api_key"] = api_key or ""

    def get_xfyun_keys(self) -> Tuple[str, str, str]:
        return (
            self._data.get("xfyun_appid", ""),
            self._data.get("xfyun_api_secret", ""),
            self._data.get("xfyun_api_key", ""),
        )

    def set_hotkey(self, hotkey: str) -> None:
        self._data["hotkey"] = hotkey or "<ctrl>+<alt>+<space>"

    def get_hotkey(self) -> str:
        return self._data.get("hotkey", "<ctrl>+<alt>+<space>")

    def set_window_title_keyword(self, keyword: str) -> None:
        self._data["window_title_keyword"] = keyword or ""

    def get_window_title_keyword(self) -> str:
        return self._data.get("window_title_keyword", "")

    def set_send_key(self, send_key: str) -> None:
        value = (send_key or "").strip().lower()
        if value not in {"enter", "ctrl+enter"}:
            value = "enter"
        self._data["send_key"] = value

    def get_send_key(self) -> str:
        value = (self._data.get("send_key", "enter") or "enter").strip().lower()
        return value if value in {"enter", "ctrl+enter"} else "enter"

    def is_xfyun_configured(self) -> bool:
        appid, api_secret, api_key = self.get_xfyun_keys()
        return bool(appid and api_secret and api_key)

    @staticmethod
    def _encode(value: str) -> str:
        if not value:
            return ""
        return base64.b64encode(value.encode("utf-8")).decode("ascii")

    @staticmethod
    def _decode(value: str) -> str:
        if not value:
            return ""
        try:
            return base64.b64decode(value.encode("ascii")).decode("utf-8")
        except Exception:
            return ""
