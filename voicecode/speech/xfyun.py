import base64
import hashlib
import hmac
import json
import time
from typing import List
from urllib.parse import quote

import websocket


class XfyunSpeech:
    def __init__(self, app_id: str, api_secret: str, api_key: str) -> None:
        self._app_id = app_id
        self._api_secret = api_secret
        self._api_key = api_key
        self._host = "iat-api.xfyun.cn"
        self._path = "/v2/iat"
        self._url = "wss://iat-api.xfyun.cn/v2/iat"

    def recognize(self, audio_data: bytes, timeout: int = 30) -> str:
        if not audio_data:
            return ""

        ws = websocket.create_connection(self._get_auth_url(), timeout=timeout)
        try:
            self._send_audio(ws, audio_data)
            return self._receive_result(ws)
        finally:
            ws.close()

    def _get_auth_url(self) -> str:
        date = self._rfc1123_date()
        signature_origin = (
            f"host: {self._host}\ndate: {date}\nGET {self._path} HTTP/1.1"
        )

        signature_sha = hmac.new(
            self._api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("ascii")

        authorization_origin = (
            f'api_key="{self._api_key}", '
            f'algorithm="hmac-sha256", '
            f'headers="host date request-line", '
            f'signature="{signature}"'
        )
        authorization = base64.b64encode(
            "".join(authorization_origin).encode("utf-8")
        ).decode("ascii")

        return f"{self._url}?authorization={authorization}&date={quote(date)}&host={self._host}"

    @staticmethod
    def _rfc1123_date() -> str:
        return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

    def _send_audio(self, ws: websocket.WebSocket, audio_data: bytes) -> None:
        frame_size = 1280
        status = 0
        offset = 0

        while offset < len(audio_data):
            if offset == 0:
                payload = {
                    "common": {"app_id": self._app_id},
                    "business": {
                        "language": "zh_cn",
                        "domain": "iat",
                        "accent": "mandarin",
                        "dwa": "wpgs",
                    },
                    "data": {
                        "status": status,
                        "format": "audio/L16;rate=16000",
                        "encoding": "raw",
                        "audio": base64.b64encode(
                            audio_data[offset : offset + frame_size]
                        ).decode("ascii"),
                    },
                }
                ws.send(json.dumps(payload))
                status = 1
            else:
                chunk = audio_data[offset : offset + frame_size]
                if not chunk:
                    break
                payload = {
                    "data": {
                        "status": status,
                        "format": "audio/L16;rate=16000",
                        "encoding": "raw",
                        "audio": base64.b64encode(chunk).decode("ascii"),
                    }
                }
                ws.send(json.dumps(payload))

            offset += frame_size
            time.sleep(0.04)

        payload = {
            "data": {
                "status": 2,
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": "",
            }
        }
        ws.send(json.dumps(payload))

    @staticmethod
    def _parse_result(result: dict) -> str:
        words: List[str] = []
        for item in result.get("ws", []):
            for candidate in item.get("cw", []):
                words.append(candidate.get("w", ""))
        return "".join(words)

    def _receive_result(self, ws: websocket.WebSocket) -> str:
        results: List[str] = []
        while True:
            message = ws.recv()
            response = json.loads(message)
            if response.get("code") != 0:
                raise RuntimeError(response.get("message", "xfyun error"))

            data = response.get("data", {})
            result = data.get("result")
            if result:
                results.append(self._parse_result(result))

            if data.get("status") == 2:
                break

        return "".join(results)
