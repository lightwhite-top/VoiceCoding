import logging
import queue
import threading
from typing import Any, Tuple

from voicecode.audio import AudioRecorder
from voicecode.config import Config
from voicecode.hotkey import HotkeyListener
from voicecode.opencode import OpenCodeCLI
from voicecode.speech import XfyunSpeech
from voicecode.ui import TrayIcon, show_settings

EVENT_RECORDING_STOPPED = "recording_stopped"
EVENT_RECOGNITION_RESULT = "recognition_result"
EVENT_RECOGNITION_ERROR = "recognition_error"
EVENT_SEND_COMPLETE = "send_complete"
EVENT_SEND_ERROR = "send_error"


class VoiceCodeApp:
    def __init__(self) -> None:
        self._logger = self._setup_logging()
        self._config = Config()
        self._config.load()
        self._queue: queue.Queue[Tuple[str, Any]] = queue.Queue()
        self._state = "IDLE"
        self._lock = threading.Lock()
        self._running = True
        self._stop_event = threading.Event()

        self._recorder = AudioRecorder()
        self._speech = self._build_speech()
        self._cli = self._build_cli()

        self._tray = TrayIcon(
            on_settings=self._open_settings,
            on_reset=self._reset,
            on_quit=self._quit,
            theme_mode_getter=self._config.get_theme_mode,
        )
        self._hotkey = HotkeyListener(
            hotkey=self._config.get_hotkey(),
            on_activate=self._on_activate,
            on_deactivate=self._on_deactivate,
        )

    def run(self) -> None:
        self._running = True
        self._stop_event.clear()
        self._logger.info("程序启动")
        self._precheck()
        self._hotkey.start()
        self._schedule_poll()
        self._tray.run_detached()
        self._stop_event.wait()

    def _precheck(self) -> None:
        if not self._config.is_xfyun_configured():
            self._tray.show_message("VoiceCode", "讯飞密钥未配置")
            self._logger.warning("讯飞密钥未配置")

        # 现在不再依赖 opencode CLI；发送阶段会尝试写入 OpenCode Desktop 输入框

    def _build_speech(self) -> XfyunSpeech | None:
        appid, api_secret, api_key = self._config.get_xfyun_keys()
        if not (appid and api_secret and api_key):
            return None
        return XfyunSpeech(appid, api_secret, api_key)

    def _build_cli(self) -> OpenCodeCLI:
        return OpenCodeCLI(
            send_key=self._config.get_send_key(),
        )

    def _open_settings(self) -> None:
        self._logger.info("打开设置")
        show_settings(self._config)
        self._config.load()
        self._hotkey.update_hotkey(self._config.get_hotkey())
        self._speech = self._build_speech()
        self._cli = self._build_cli()
        self._logger.info("设置已更新")

    def _reset(self) -> None:
        self._logger.info("手动重置")
        with self._lock:
            self._state = "IDLE"
        self._tray.set_status("idle")
        self._recorder.stop_recording()

    def _quit(self) -> None:
        self._logger.info("退出程序")
        self._running = False
        self._stop_event.set()
        self._hotkey.stop()
        self._tray.stop()

    def _on_activate(self) -> None:
        with self._lock:
            if self._state != "IDLE":
                return
            self._state = "RECORDING"
        self._tray.set_status("recording")
        self._tray.show_message("VoiceCode", "开始录音")
        self._logger.info("开始录音")
        self._recorder.start_recording()

    def _on_deactivate(self) -> None:
        with self._lock:
            if self._state != "RECORDING":
                return
            self._state = "RECOGNIZING"
        self._tray.set_status("recognizing")
        self._tray.show_message("VoiceCode", "结束录音，开始识别")
        self._logger.info("结束录音，开始识别")
        audio_data = self._recorder.stop_recording()
        self._enqueue(EVENT_RECORDING_STOPPED, audio_data)

    def _enqueue(self, event: str, payload: Any) -> None:
        self._queue.put((event, payload))

    def _schedule_poll(self) -> None:
        if not self._running:
            return
        timer = threading.Timer(0.2, self._poll_queue)
        timer.daemon = True
        timer.start()

    def _poll_queue(self) -> None:
        if not self._running:
            return
        while not self._queue.empty():
            event, payload = self._queue.get()
            if event == EVENT_RECORDING_STOPPED:
                self._handle_recording_stopped(payload)
            elif event == EVENT_RECOGNITION_RESULT:
                self._handle_recognition_result(payload)
            elif event == EVENT_RECOGNITION_ERROR:
                self._handle_recognition_error(payload)
            elif event == EVENT_SEND_COMPLETE:
                self._handle_send_complete(payload)
            elif event == EVENT_SEND_ERROR:
                self._handle_send_error(payload)

        self._schedule_poll()

    def _handle_recording_stopped(self, audio_data: bytes) -> None:
        if not audio_data:
            self._logger.warning("录音数据为空")
            self._to_idle()
            return
        speech = self._speech
        if not speech:
            self._tray.show_message("VoiceCode", "讯飞密钥未配置")
            self._logger.warning("讯飞密钥未配置")
            self._to_idle()
            return

        def recognize() -> None:
            try:
                self._logger.info("开始调用讯飞识别")
                text = speech.recognize(audio_data)
                self._logger.info("讯飞识别完成")
                self._enqueue(EVENT_RECOGNITION_RESULT, text)
            except Exception as exc:
                self._logger.exception("讯飞识别异常")
                self._enqueue(EVENT_RECOGNITION_ERROR, str(exc))

        threading.Thread(target=recognize, daemon=True).start()

    def _handle_recognition_result(self, text: str) -> None:
        message = (text or "").strip()
        if not message:
            self._logger.warning("识别结果为空")
            self._to_idle()
            return

        self._logger.info("识别结果：%s", message)

        with self._lock:
            self._state = "SENDING"

        def send() -> None:
            try:
                self._logger.info("开始发送到 OpenCode")
                ok = self._cli.send_message(message)
                if ok:
                    self._logger.info("发送成功")
                    self._enqueue(EVENT_SEND_COMPLETE, message)
                else:
                    self._logger.warning("发送失败")
                    err = getattr(self._cli, "last_error", "") or "发送失败"
                    self._enqueue(EVENT_SEND_ERROR, err)
            except Exception as exc:
                self._logger.exception("发送异常")
                self._enqueue(EVENT_SEND_ERROR, str(exc))

        threading.Thread(target=send, daemon=True).start()

    def _handle_recognition_error(self, message: str) -> None:
        self._tray.show_message("VoiceCode", f"识别错误：{message}")
        self._logger.warning("识别错误：%s", message)
        self._to_idle()

    def _handle_send_complete(self, _message: str) -> None:
        self._to_idle()

    def _handle_send_error(self, message: str) -> None:
        self._tray.show_message("VoiceCode", f"发送错误：{message}")
        self._logger.warning("发送错误：%s", message)
        self._to_idle()

    def _to_idle(self) -> None:
        with self._lock:
            self._state = "IDLE"
        self._tray.set_status("idle")

    @staticmethod
    def _setup_logging() -> logging.Logger:
        logger = logging.getLogger("voicecode")
        if logger.handlers:
            return logger
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        return logger


def main() -> None:
    VoiceCodeApp().run()


if __name__ == "__main__":
    main()
