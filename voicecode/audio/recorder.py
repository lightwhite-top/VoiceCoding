import threading
import time
from typing import List

import pyaudio


class AudioRecorder:
    def __init__(
        self,
        rate: int = 16000,
        channels: int = 1,
        chunk: int = 1024,
        max_duration: int = 60,
    ) -> None:
        self._rate = rate
        self._channels = channels
        self._chunk = chunk
        self._max_duration = max_duration
        self._lock = threading.Lock()
        self._recording = False
        self._frames: List[bytes] = []
        self._thread: threading.Thread | None = None
        self._audio: pyaudio.PyAudio | None = None
        self._stream: pyaudio.Stream | None = None

    def start_recording(self) -> None:
        with self._lock:
            if self._recording:
                return
            self._recording = True
            self._frames = []
            self._audio = pyaudio.PyAudio()
            self._stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=self._channels,
                rate=self._rate,
                input=True,
                frames_per_buffer=self._chunk,
            )
            self._thread = threading.Thread(target=self._record_loop, daemon=True)
            self._thread.start()

    def stop_recording(self) -> bytes:
        with self._lock:
            if not self._recording:
                return b""
            self._recording = False

        if self._thread:
            self._thread.join(timeout=2)

        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        if self._audio:
            self._audio.terminate()
            self._audio = None

        return b"".join(self._frames)

    def is_recording(self) -> bool:
        with self._lock:
            return self._recording

    def _record_loop(self) -> None:
        start_time = time.monotonic()
        while True:
            with self._lock:
                if not self._recording:
                    break

            if time.monotonic() - start_time >= self._max_duration:
                with self._lock:
                    self._recording = False
                break

            if not self._stream:
                time.sleep(0.01)
                continue

            data = self._stream.read(self._chunk, exception_on_overflow=False)
            self._frames.append(data)
