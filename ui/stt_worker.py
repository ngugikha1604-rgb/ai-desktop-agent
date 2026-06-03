"""SttWorker — QThread quản lý ghi âm và chuyển đổi giọng nói → văn bản."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QThread, Signal

from agent.logger import get_logger
from agent.stt_engine import STTEngine

log = get_logger(__name__)

_SAMPLE_RATE    = 16000
_CHANNELS       = 1
_CHUNK_DURATION = 0.1            # giây mỗi chunk đọc từ mic
_CHUNK_FRAMES   = int(_SAMPLE_RATE * _CHUNK_DURATION)
_SILENCE_DBFS   = -40.0          # ngưỡng im lặng
_SILENCE_SEC    = 1.5            # giây im lặng liên tục → kết thúc ghi
_TIMEOUT_SEC    = 10.0           # giây không có âm → tự huỷ


def _rms_dbfs(chunk: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
    return 20.0 * np.log10(rms / 32768.0) if rms > 0 else -96.0


class SttWorker(QThread):
    """Ghi âm liên tục → phát hiện im lặng → transcribe."""

    transcribed    = Signal(str)   # văn bản kết quả (có thể rỗng)
    error_occurred = Signal(str)   # thông báo lỗi hiển thị cho user
    cancelled      = Signal()      # bị huỷ bởi Esc hoặc timeout

    def __init__(self, engine: STTEngine, preferred_device=None) -> None:
        super().__init__()
        self._engine  = engine
        self._device  = preferred_device
        self._stop    = False

    def stop(self) -> None:
        """Dừng ghi âm ngay lập tức (nhấn Esc)."""
        self._stop = True

    def run(self) -> None:
        try:
            import sounddevice as sd
        except ImportError:
            self.error_occurred.emit(
                "Không thể truy cập microphone. "
                "Hãy cài thư viện: pip install sounddevice"
            )
            return

        # Validate thiết bị — fallback về mặc định nếu lỗi
        device = self._device
        try:
            sd.check_input_settings(
                device=device, samplerate=_SAMPLE_RATE, channels=_CHANNELS
            )
        except Exception as e:
            log.warning("[STT] Thiết bị ưa thích lỗi, dùng mặc định: %s", e)
            device = None

        audio_chunks: list[np.ndarray] = []
        silence_acc  = 0.0
        no_audio_acc = 0.0
        has_speech   = False

        try:
            with sd.InputStream(
                device=device,
                samplerate=_SAMPLE_RATE,
                channels=_CHANNELS,
                dtype="int16",
                blocksize=_CHUNK_FRAMES,
            ) as stream:
                while not self._stop:
                    chunk, _ = stream.read(_CHUNK_FRAMES)
                    mono = chunk[:, 0] if chunk.ndim > 1 else chunk.flatten()
                    silent = _rms_dbfs(mono) < _SILENCE_DBFS

                    if not silent:
                        has_speech   = True
                        silence_acc  = 0.0
                        no_audio_acc = 0.0
                        audio_chunks.append(mono)
                    else:
                        no_audio_acc += _CHUNK_DURATION
                        if has_speech:
                            silence_acc += _CHUNK_DURATION
                            audio_chunks.append(mono)
                            if silence_acc >= _SILENCE_SEC:
                                break   # im lặng đủ → kết thúc tự nhiên
                        else:
                            if no_audio_acc >= _TIMEOUT_SEC:
                                log.debug("[STT] Timeout không có âm.")
                                self.cancelled.emit()
                                return

        except Exception as e:
            log.warning("[STT] Lỗi stream: %s", e)
            self.error_occurred.emit(
                "Không thể truy cập microphone. "
                "Hãy kiểm tra quyền truy cập trong Settings → Privacy → Microphone."
            )
            return

        if self._stop:
            self.cancelled.emit()
            return

        if not audio_chunks:
            self.transcribed.emit("")
            return

        # Transcribe
        audio_bytes = np.concatenate(audio_chunks).tobytes()
        text = self._engine.transcribe(audio_bytes, _SAMPLE_RATE)

        if not text:
            self.error_occurred.emit("Không nhận dạng được giọng nói, vui lòng thử lại.")
            return

        self.transcribed.emit(text)
