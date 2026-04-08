import logging
import re
import threading
import queue
import sys
import subprocess
import tempfile
import os
import wave

import numpy as np
import sounddevice as sd
import soundfile as sf

from PyQt6.QtCore import QThread

# Optional TTS libraries
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

from workers.base_signals import WorkerSignals
from services.tts_service import (
    KOKORO_AVAILABLE,
    KOKORO_PIPELINES,
    PIPER_AVAILABLE,
    PIPER_VOICES,
    DEVICE,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────

KOKORO_VOICES = {
    "en": "af_heart",
    "ja": "jf_alpha",
}

KOKORO_SAMPLE_RATE = 24_000

# ── Text chunking ─────────────────────────────────────────────

_SPLIT_RE = re.compile(
    r'(?<=[.!?…])\s+'
    r'|(?<=。|！|？|…)\s*'
    r'|(?<=[,;:])\s+(?=\S{20,})'
)

def _split_into_chunks(text: str, max_chars: int = 200) -> list[str]:
    raw = _SPLIT_RE.split(text.strip())

    chunks = []
    current = ""

    for segment in raw:
        segment = segment.strip()
        if not segment:
            continue

        if current and len(current) + 1 + len(segment) > max_chars:
            chunks.append(current)
            current = segment
        else:
            current = (current + " " + segment).strip() if current else segment

    if current:
        chunks.append(current)

    final = []
    for chunk in chunks:
        while len(chunk) > max_chars:
            final.append(chunk[:max_chars])
            chunk = chunk[max_chars:]
        if chunk:
            final.append(chunk)

    return final

# ── Streaming Player ──────────────────────────────────────────

class _StreamingPlayer:
    _SENTINEL = object()

    def __init__(self, samplerate=KOKORO_SAMPLE_RATE):
        self._sr = samplerate
        self._q = queue.Queue()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self._thread.start()

    def push(self, chunk):
        self._q.put(chunk)

    def finish(self):
        self._q.put(self._SENTINEL)
        self._thread.join()

    def _loop(self):
        while True:
            item = self._q.get()
            if item is self._SENTINEL:
                break
            try:
                sd.play(item.astype(np.float32), samplerate=self._sr)
                sd.wait()
            except Exception as e:
                logger.warning("tts_worker | playback error | %s", e)

# ─────────────────────────────────────────────────────────────
# ✅ RESTORED CLASS (THIS WAS YOUR BREAKING CHANGE)
# ─────────────────────────────────────────────────────────────

class TTSWorker(QThread):
    def __init__(self, text, language="en"):
        super().__init__()
        self.text = text
        self.language = language
        self.signals = WorkerSignals()

    def run(self):
        logger.info(
            "tts_worker | start | language=%s | text_chars=%s",
            self.language,
            len(self.text or ""),
        )

        try:
            success = False

            # ── Backend 1: Kokoro (streaming) ─────────────────────
            if KOKORO_AVAILABLE and self.language in KOKORO_PIPELINES:
                try:
                    logger.info(
                        "tts_worker | attempt | backend=Kokoro | device=%s",
                        DEVICE,
                    )

                    pipeline = KOKORO_PIPELINES[self.language]
                    voice = KOKORO_VOICES.get(self.language, "af_heart")

                    chunks = _split_into_chunks(self.text or "")

                    player = _StreamingPlayer()
                    player.start()

                    total_chunks = 0

                    for text_chunk in chunks:
                        parts = []

                        for _, _, audio in pipeline(text_chunk, voice=voice):
                            if audio is not None:
                                if hasattr(audio, "cpu"):
                                    audio = audio.cpu().numpy()
                                parts.append(np.asarray(audio, dtype=np.float32))

                        if parts:
                            player.push(np.concatenate(parts))
                            total_chunks += 1

                    player.finish()

                    if total_chunks > 0:
                        success = True
                        logger.info("tts_worker | success | backend=Kokoro")

                except Exception as e:
                    logger.warning("tts_worker | Kokoro_failed | %s", e, exc_info=True)

            # ── Backend 2: Piper (RESTORED SAFE VERSION) ───────────
            if not success and PIPER_AVAILABLE and self.language in PIPER_VOICES:
                try:
                    logger.info("tts_worker | attempt | backend=Piper")

                    voice = PIPER_VOICES[self.language]

                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        with wave.open(f.name, "wb") as wf:
                            voice.synthesize_wav(self.text, wf)
                        wav_path = f.name

                    data, sr = sf.read(wav_path, dtype="int16")
                    sd.play(data, sr)
                    sd.wait()
                    os.unlink(wav_path)

                    success = True
                    logger.info("tts_worker | success | backend=Piper")

                except Exception as e:
                    logger.warning("tts_worker | Piper_failed | %s", e, exc_info=True)

            # ── Backend 3: gTTS (RESTORED ROBUST VERSION) ─────────
            if not success and GTTS_AVAILABLE:
                try:
                    logger.info("tts_worker | attempt | backend=gTTS")

                    lang = "ja" if self.language == "ja" else "en"

                    tts = gTTS(text=self.text, lang=lang)
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                        tts.save(f.name)
                        mp3_path = f.name

                    wav_path = mp3_path.replace(".mp3", ".wav")

                    try:
                        subprocess.run(
                            ["ffmpeg", "-i", mp3_path, wav_path, "-y"],
                            check=True,
                            capture_output=True,
                        )
                        data, sr = sf.read(wav_path, dtype="int16")
                        sd.play(data, sr)
                        sd.wait()
                    except Exception:
                        subprocess.run(["mpg123", mp3_path], capture_output=True)

                    os.unlink(mp3_path)
                    if os.path.exists(wav_path):
                        os.unlink(wav_path)

                    success = True
                    logger.info("tts_worker | success | backend=gTTS")

                except Exception as e:
                    logger.warning("tts_worker | gTTS_failed | %s", e, exc_info=True)

            # ── Backend 4: pyttsx3 ────────────────────────────────
            if not success and PYTTSX3_AVAILABLE:
                try:
                    logger.info("tts_worker | attempt | backend=pyttsx3")

                    engine = pyttsx3.init()
                    engine.say(self.text)
                    engine.runAndWait()
                    engine.stop()

                    success = True
                    logger.info("tts_worker | success | backend=pyttsx3")

                except Exception as e:
                    logger.warning("tts_worker | pyttsx3_failed | %s", e, exc_info=True)

            if not success:
                logger.error("tts_worker | all_backends_failed")
                self.signals.error.emit("All TTS methods failed.")

        except Exception as e:
            logger.error("tts_worker | fatal | %s", e, exc_info=True)
            self.signals.error.emit(str(e))

        finally:
            self.signals.finished.emit()