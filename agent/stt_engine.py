"""STTEngine — chuyển đổi giọng nói → văn bản bằng faster-whisper (chạy cục bộ)."""
from __future__ import annotations

from agent.logger import get_logger

log = get_logger(__name__)

_MODEL_SIZE    = "base"   # ~145 MB, hỗ trợ vi + en
_SAMPLE_RATE   = 16000
_MIN_DURATION  = 0.5      # giây — ngắn hơn → trả về chuỗi rỗng


class STTEngine:
    """Chạy Whisper cục bộ, không gửi dữ liệu ra ngoài internet."""

    def __init__(self, model_size: str = _MODEL_SIZE) -> None:
        self._model_size = model_size
        self._model = None
        self._available = False
        self._load_model()

    def _load_model(self) -> None:
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self._model_size,
                device="cpu",
                compute_type="int8",
            )
            self._available = True
            log.debug("[STT] Model '%s' loaded thành công.", self._model_size)
        except ImportError:
            log.warning("[STT] faster-whisper chưa cài. Chạy: pip install faster-whisper")
        except Exception as e:
            log.warning("[STT] Không load được model: %s", e)

    @property
    def available(self) -> bool:
        return self._available

    def transcribe(self, audio_bytes: bytes, sample_rate: int = _SAMPLE_RATE) -> str:
        """Chuyển đổi audio bytes → text.
        Trả về chuỗi rỗng nếu audio quá ngắn hoặc không có giọng nói.
        """
        if not self._available or not self._model:
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
                language=None,    # tự động nhận dạng vi / en
                beam_size=5,
                vad_filter=True,  # lọc khoảng lặng
            )
            text = " ".join(seg.text for seg in segments).strip()
            log.debug("[STT] Kết quả: %r", text)
            return text
        except Exception as e:
            log.warning("[STT] Lỗi transcribe: %s", e)
            return ""
