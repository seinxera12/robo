import logging
import os
import sys
import subprocess
import tempfile
import wave

from PyQt6.QtCore import QThread

import sounddevice as sd
import soundfile as sf

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

# Piper (optional)
try:
    from piper import PiperVoice
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False

from workers.base_signals import WorkerSignals
from services.tts_service import PIPER_VOICES

logger = logging.getLogger(__name__)


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

            if PIPER_AVAILABLE and self.language in PIPER_VOICES:
                try:
                    logger.info("tts_worker | attempt | backend=Piper")
                    voice = PIPER_VOICES[self.language]
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                        with wave.open(tmp_file.name, "wb") as wav_file:
                            voice.synthesize_wav(self.text, wav_file)
                        wav_path = tmp_file.name
                    data, samplerate = sf.read(wav_path, samplerate=None, dtype="int16")
                    sd.play(data, samplerate)
                    sd.wait()
                    os.unlink(wav_path)
                    success = True
                    logger.info("tts_worker | success | backend=Piper")
                except Exception as e:
                    logger.warning("tts_worker | Piper_failed | %s", e, exc_info=True)

            if not success and GTTS_AVAILABLE:
                try:
                    logger.info("tts_worker | attempt | backend=gTTS")
                    gtts_lang = "ja" if self.language == "ja" else "en"
                    tts = gTTS(text=self.text, lang=gtts_lang, slow=False)
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                        tts.save(tmp_file.name)
                        mp3_path = tmp_file.name
                    wav_path = mp3_path.replace(".mp3", ".wav")
                    try:
                        subprocess.run(
                            ["ffmpeg", "-i", mp3_path, wav_path, "-y"],
                            check=True,
                            capture_output=True,
                        )
                        data, samplerate = sf.read(wav_path, samplerate=None, dtype="int16")
                        sd.play(data, samplerate)
                        sd.wait()
                        success = True
                        logger.info("tts_worker | success | backend=gTTS | path=ffmpeg_wav")
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        if sys.platform.startswith("win"):
                            os.startfile(mp3_path)
                        elif sys.platform.startswith("darwin"):
                            subprocess.run(["afplay", mp3_path])
                        elif sys.platform.startswith("linux"):
                            subprocess.run(["mpg123", mp3_path], capture_output=True)
                        success = True
                        logger.info("tts_worker | success | backend=gTTS | path=system_player")
                    finally:
                        try:
                            os.unlink(mp3_path)
                            if os.path.exists(wav_path):
                                os.unlink(wav_path)
                        except OSError:
                            pass
                except Exception as e:
                    logger.warning("tts_worker | gTTS_failed | %s", e, exc_info=True)

            if not success and PYTTSX3_AVAILABLE:
                try:
                    logger.info("tts_worker | attempt | backend=pyttsx3")
                    engine = pyttsx3.init()
                    voices = engine.getProperty("voices")
                    if self.language == "ja":
                        for voice in voices:
                            if "japan" in voice.name.lower() or "ja" in voice.id.lower():
                                engine.setProperty("voice", voice.id)
                                break
                    else:
                        for voice in voices:
                            if "english" in voice.name.lower() or "en" in voice.id.lower():
                                engine.setProperty("voice", voice.id)
                                break
                    engine.setProperty("rate", 150)
                    engine.setProperty("volume", 0.9)
                    engine.say(self.text)
                    engine.runAndWait()
                    engine.stop()
                    success = True
                    logger.info("tts_worker | success | backend=pyttsx3")
                except Exception as e:
                    logger.warning("tts_worker | pyttsx3_failed | %s", e, exc_info=True)

            if not success:
                try:
                    logger.info("tts_worker | attempt | backend=system")
                    if sys.platform.startswith("win"):
                        import win32com.client
                        speaker = win32com.client.Dispatch("SAPI.SpVoice")
                        speaker.Speak(self.text)
                        success = True
                        logger.info("tts_worker | success | backend=Windows_SAPI")
                    elif sys.platform.startswith("darwin"):
                        voice = "Kyoko" if self.language == "ja" else "Alex"
                        subprocess.run(["say", "-v", voice, self.text])
                        success = True
                        logger.info("tts_worker | success | backend=macOS_say")
                    elif sys.platform.startswith("linux"):
                        lang_code = "ja" if self.language == "ja" else "en"
                        subprocess.run(["espeak", "-v", lang_code, self.text])
                        success = True
                        logger.info("tts_worker | success | backend=espeak")
                except Exception as e:
                    logger.warning("tts_worker | system_failed | %s", e, exc_info=True)

            if not success:
                logger.error("tts_worker | all_backends_failed")
                self.signals.error.emit(
                    "All TTS methods failed. Please check your system audio settings."
                )

        except Exception as e:
            logger.error("tts_worker | error | %s", e, exc_info=True)
            self.signals.error.emit(f"TTS Error: {e}")
        finally:
            logger.debug("tts_worker | thread_finish")
            self.signals.finished.emit()
