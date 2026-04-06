import logging

from PyQt6.QtCore import QThread
import sounddevice as sd
import whisper

from config.settings import SAMPLE_RATE, RECORD_DURATION
from workers.base_signals import WorkerSignals

logger = logging.getLogger(__name__)


class STTWorker(QThread):
    WHISPER_MODEL = "base"

    def __init__(self, language="en"):
        super().__init__()
        self.signals = WorkerSignals()
        self.language = language
        logger.info(
            "stt_worker | loading_whisper | model=%s | language=%s",
            self.WHISPER_MODEL,
            language,
        )
        self.model = whisper.load_model(self.WHISPER_MODEL)

    def run(self):
        samples = int(RECORD_DURATION * SAMPLE_RATE)
        logger.info(
            "stt_worker | record_start | duration_s=%s | sample_rate=%s | samples=%s | language=%s",
            RECORD_DURATION,
            SAMPLE_RATE,
            samples,
            self.language,
        )
        try:
            audio = sd.rec(
                samples,
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
            )
            sd.wait()
            audio = audio.flatten()
            logger.debug("stt_worker | record_complete | audio_shape=%s", audio.shape)

            logger.info("stt_worker | transcribe_start | model=%s", self.WHISPER_MODEL)
            result = self.model.transcribe(audio, fp16=False, language=self.language)
            text = result.get("text", "").strip()
            logger.info("stt_worker | transcribe_complete | text_chars=%s", len(text))

            if text:
                logger.info("stt_worker | result_ok | preview=%s", text[:80] + ("…" if len(text) > 80 else ""))
                self.signals.result.emit(text)
            else:
                logger.warning("stt_worker | no_speech")
                self.signals.error.emit("No speech detected")

        except Exception as e:
            logger.error("stt_worker | error | %s", e, exc_info=True)
            self.signals.error.emit(str(e))
        finally:
            logger.debug("stt_worker | thread_finish")
            self.signals.finished.emit()
