import base64
import hashlib
import hmac
import json
import time
from typing import List
from urllib.parse import quote

import websocket



class XfyunSpeech:
    """
    科大讯飞语音听写 (IAT) 客户端。
    通过 WebSocket 接口实现实时语音转文字功能。
    """
    def __init__(self, app_id: str, api_secret: str, api_key: str) -> None:
        """
        初始化讯飞客户端。
        
        Args:
            app_id: 讯飞控制台获取的 APPID
            api_secret: 讯飞控制台获取的 APISecret
            api_key: 讯飞控制台获取的 APIKey
        """
        self._app_id = app_id
        self._api_secret = api_secret
        self._api_key = api_key
        self._host = "iat-api.xfyun.cn"
        self._path = "/v2/iat"
        self._url = "wss://iat-api.xfyun.cn/v2/iat"

    def recognize(self, audio_data: bytes, timeout: int = 30) -> str:
        """
        执行语音识别。
        
        Args:
            audio_data: 音频文件的二进制数据 (PCM/WAV 格式)
            timeout: WebSocket 连接和接收超时时间 (秒)
            
        Returns:
            识别出的文本结果。如果音频为空或识别失败，可能返回空字符串或抛出异常。
        """
        if not audio_data:
            return ""

        ws = websocket.create_connection(self._get_auth_url(), timeout=timeout)
        try:
            self._send_audio(ws, audio_data)
            return self._receive_result(ws)
        finally:
            ws.close()

    def _get_auth_url(self) -> str:
        """
        生成鉴权 URL。
        讯飞 API 要求根据 host, date, request-line 计算 HMAC-SHA256 签名，
        并将签名和其他参数拼接到 WebSocket URL 中。
        """
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
        """生成符合 RFC1123 格式的当前 GMT 时间字符串，用于鉴权 headers。"""
        return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

    def _send_audio(self, ws: websocket.WebSocket, audio_data: bytes) -> None:
        """
        分帧发送音频数据。
        
        Args:
            ws: 已建立的 WebSocket 连接对象
            audio_data: 完整的音频二进制数据
            
        说明：
        1. 第一帧 (status=0) 包含 common, business 参数配置。
        2. 中间帧 (status=1) 仅包含 data 音频数据。
        3. 最后一帧 (status=2) 发送空 audio 数据以标记结束。
        """
        frame_size = 1280  # 每一帧的音频大小
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
        """
        解析 API 返回的 JSON 结果中的文本内容。
        result 结构通常为 { "ws": [ { "cw": [ { "w": "单词" } ] } ] }
        """
        words: List[str] = []
        for item in result.get("ws", []):
            for candidate in item.get("cw", []):
                words.append(candidate.get("w", ""))
        return "".join(words)

    def _receive_result(self, ws: websocket.WebSocket) -> str:
        """
        循环接收 WebSocket 消息并拼接收集识别结果。
        直到收到 status=2 的结束消息或发生异常。
        """
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
