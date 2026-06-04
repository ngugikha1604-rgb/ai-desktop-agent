"""STTEngine — chuyển đổi giọng nói → văn bản bằng faster-whisper (chạy cục bộ).

Model được tải LAZY — chỉ load khi transcribe() được gọi lần đầu.
Không tải gì khi khởi động app để tránh đơ UI.
"""
from __future__ import annotations

import threading

from agent.logger import get_logger

log = get_logger(__name__)

_MODEL_SIZE   = "base"   # ~145 MB, hỗ trợ vi + en
_SAMPLE_RATE  = 16000
_MIN_DURATION = 0.5      # giây — ngắn hơn → trả về chuỗi rỗng


class STTEngine:
    """Chạy Whisper cục bộ, không gửi dữ liệu ra ngoài internet.

    Model được load lười (lazy): lần đầu gọi transcribe() mới tải vào RAM.
    """

    def __init__(self, model_size: str = _MODEL_SIZE) -> None:
        self._model_size = model_size
        self._model = None
        self._available: bool | None = None   # None = chưa biết, True/False = đã kiểm tra
        self._lock = threading.Lock()

        # Kiểm tra import sẵn sàng (không tải model, chỉ check thư viện)
        self._importable = self._check_importable()

    @staticmethod
    def _check_importable() -> bool:
        """Kiểm tra faster-whisper có được cài chưa (không tải model)."""
        try:
            import faster_whisper  # noqa: F401
            return True
        except ImportError:
            log.warning("[STT] faster-whisper chưa cài. Chạy: pip install faster-whisper")
            return False

    def _ensure_loaded(self) -> bool:
        """Tải model nếu chưa tải. Thread-safe. Trả về True nếu sẵn sàng."""
        if self._available is True:
            return True
        if self._available is False:
            return False
        if not self._importable:
            self._available = False
            return False

        with self._lock:
            if self._available is not None:   # double-check sau khi lấy lock
                return self._available is True
            try:
                from faster_whisper import WhisperModel
                log.debug("[STT] Đang tải model '%s'...", self._model_size)
                self._model = WhisperModel(
                    self._model_size,
                    device="cpu",
                    compute_type="int8",
                )
                self._available = True
                log.debug("[STT] Model '%s' đã sẵn sàng.", self._model_size)
            except Exception as e:
                log.warning("[STT] Không load được model: %s", e)
                self._available = False
        return self._available is True

    @property
    def importable(self) -> bool:
        """faster-whisper đã cài chưa (kiểm tra nhanh khi khởi động app)."""
        return self._importable

    @property
    def available(self) -> bool:
        """Model đã load xong và sẵn sàng transcribe chưa."""
        return self._available is True

    def transcribe(self, audio_bytes: bytes, sample_rate: int = _SAMPLE_RATE) -> str:
        """Chuyển đổi audio bytes → text.

        Load model tự động nếu chưa load.
        Trả về chuỗi rỗng nếu audio quá ngắn hoặc không có giọng nói.
        """
        if not self._ensure_loaded():
            return ""
        try:
            import numpy as np
            audio_array = (
                np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
                / 32768.0
            )
            duration = len(audio_array) / sample_rate
            if duration < _MIN_DURATION:
                log.debug("[STT] Audio quá ngắn: %.2fs", duration)
                return ""
            segments, _ = self._model.transcribe(
                audio_array,
                language=None,    # tự nhận vi / en
                beam_size=5,
                vad_filter=True,
            )
            text = " ".join(seg.text for seg in segments).strip()
            log.debug("[STT] Kết quả: %r", text)
            return text
        except Exception as e:
            log.warning("[STT] Lỗi transcribe: %s", e)
            return ""
