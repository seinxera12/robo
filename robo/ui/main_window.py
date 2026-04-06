from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame,
    QScrollArea, QSizePolicy, QComboBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# ✅ NEW IMPORTS (Stage 2 structure)
from workers.stt_worker import STTWorker
from workers.tts_worker import TTSWorker
from workers.ai_worker import AIWorker

from ui.chat_bubble import ChatBubble
from ui.dialogs import LanguageDialog

from core.language import detect_language
from utils.text_cleaner import clean_for_tts

from services.tts_service import check_tts_availability


class PersonalAssistantUI(QMainWindow):
    def __init__(self):
        super().__init__()

        # State
        self.conversation_history = []
        self.current_user_message = ""
        self.user_info = {}
        self.is_listening = False
        self.is_speaking = False
        self.current_language = 'en'

        # ✅ moved to service
        check_tts_availability()

        self.init_ui()
        self.setup_style()

        self.stt_worker = None
        self.tts_worker = None
        self.ai_worker = None
        self._shutting_down = False

    # ---------------- UI ---------------- #

    def init_ui(self):
        self.setWindowTitle("AI Personal Assistant")
        self.setGeometry(100, 100, 550, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()
        header = QLabel("AI Personal Assistant")
        header.setObjectName("headerLabel")
        header.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header_layout.addWidget(header)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Status + Language
        status_layout = QHBoxLayout()

        self.status_label = QLabel("Ready to assist you!")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("color: #7F8C8D;")
        self.status_label.setWordWrap(True)
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )

        lang_hint = QLabel("Language:")
        lang_hint.setFont(QFont("Segoe UI", 9))
        lang_hint.setStyleSheet("color: #7F8C8D;")

        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("langCombo")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("日本語", "ja")
        idx = self.lang_combo.findData(self.current_language)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_combo_changed)

        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(lang_hint)
        status_layout.addWidget(self.lang_combo)
        main_layout.addLayout(status_layout)

        # Chat area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setObjectName("chatScroll")
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.chat_widget = QWidget()
        self.chat_widget.setObjectName("chatInner")
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.addStretch()
        self.chat_layout.setSpacing(10)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.chat_scroll.setWidget(self.chat_widget)
        main_layout.addWidget(self.chat_scroll)

        # Input
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: white; border-radius: 10px;")
        input_layout = QVBoxLayout(input_frame)

        text_layout = QHBoxLayout()
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Type your message...")
        self.text_input.returnPressed.connect(self.send_text_message)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_text_message)

        text_layout.addWidget(self.text_input)
        text_layout.addWidget(self.send_button)
        input_layout.addLayout(text_layout)

        # Buttons
        button_layout = QHBoxLayout()

        self.listen_button = QPushButton("Start Listening")
        self.listen_button.clicked.connect(self.toggle_listening)

        self.language_button = QPushButton("Language")
        self.language_button.clicked.connect(self.change_language)

        self.clear_button = QPushButton("Clear Chat")
        self.clear_button.clicked.connect(self.clear_chat)

        self.test_tts_button = QPushButton("Test TTS")
        self.test_tts_button.clicked.connect(self.test_tts)

        button_layout.addWidget(self.language_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.test_tts_button)
        button_layout.addStretch()
        button_layout.addWidget(self.listen_button)

        input_layout.addLayout(button_layout)
        main_layout.addWidget(input_frame)

    def setup_style(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #F8F9FA; }
            QLabel#headerLabel {
                color: #2C3E50;
            }
            QScrollArea#chatScroll {
                background-color: #FFFFFF;
                border: 1px solid #DDE1E4;
                border-radius: 10px;
            }
            QWidget#chatInner {
                background-color: #FFFFFF;
            }
            QLineEdit {
                color: #2C3E50;
                background-color: #FFFFFF;
                border: 1px solid #BDC3C7;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 14px;
                selection-background-color: #3498DB;
                selection-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 1px solid #3498DB;
            }
            QComboBox#langCombo {
                color: #2C3E50;
                background-color: #FFFFFF;
                border: 1px solid #BDC3C7;
                border-radius: 8px;
                padding: 6px 12px;
                min-width: 140px;
            }
            QComboBox#langCombo QAbstractItemView {
                color: #2C3E50;
                background-color: #FFFFFF;
                selection-background-color: #3498DB;
                selection-color: #FFFFFF;
            }
            QPushButton {
                background-color: #3498DB;
                color: white;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:disabled {
                background-color: #A6BCC6;
                color: #ECF0F1;
            }
            QDialog QLabel {
                color: #2C3E50;
            }
            QDialog QComboBox {
                color: #2C3E50;
                background-color: #FFFFFF;
                border: 1px solid #BDC3C7;
                border-radius: 6px;
                padding: 6px 10px;
            }
        """)

    # ---------------- Core Logic ---------------- #

    def add_chat_message(self, message, is_user=True):
        if self._shutting_down:
            return
        bubble = ChatBubble(message, is_user)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)

        scroll_timer = QTimer(self)
        scroll_timer.setSingleShot(True)
        scroll_timer.timeout.connect(self._scroll_chat_to_bottom)
        scroll_timer.start(100)

    def _scroll_chat_to_bottom(self):
        if self._shutting_down:
            return
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        )

    def _sync_lang_combo(self):
        idx = self.lang_combo.findData(self.current_language)
        if idx >= 0:
            self.lang_combo.blockSignals(True)
            self.lang_combo.setCurrentIndex(idx)
            self.lang_combo.blockSignals(False)

    def _on_lang_combo_changed(self, _index):
        code = self.lang_combo.currentData()
        if code and code != self.current_language:
            self.current_language = code

    def change_language(self):
        dialog = LanguageDialog(self)
        if dialog.exec():
            self.current_language = dialog.get_selected_language()
            self._sync_lang_combo()

    def clear_chat(self):
        for i in reversed(range(self.chat_layout.count())):
            widget = self.chat_layout.itemAt(i).widget()
            if isinstance(widget, ChatBubble):
                widget.deleteLater()

        self.conversation_history.clear()

    # ---------------- Messaging ---------------- #

    def send_text_message(self):
        message = self.text_input.text().strip()
        if not message:
            return

        if self.is_speaking or self.is_listening:
            return

        self.text_input.clear()

        # ✅ moved to utils
        detected_lang = detect_language(message)

        if detected_lang != self.current_language:
            self.current_language = detected_lang
            self._sync_lang_combo()

        self.add_chat_message(message, True)
        self.process_with_ai(message)

    def process_with_ai(self, message):
        self.current_user_message = message

        self.ai_worker = AIWorker(
            message,
            self.conversation_history,
            self.user_info,
            self.current_language
        )

        self.ai_worker.signals.result.connect(self.on_ai_response)
        self.ai_worker.signals.error.connect(self.on_ai_error)
        self.ai_worker.start()

    def on_ai_response(self, response):
        if self._shutting_down:
            return
        # ✅ moved to utils
        cleaned = clean_for_tts(response, self.current_language)

        self.conversation_history.append(
            (self.current_user_message, cleaned)
        )

        self.add_chat_message(cleaned, False)
        self.speak_response(cleaned)

    def on_ai_error(self, error):
        if self._shutting_down:
            return
        self.add_chat_message("Error occurred.", False)

    # ---------------- TTS ---------------- #

    def speak_response(self, text):
        if self._shutting_down:
            return
        self.is_speaking = True

        self.tts_worker = TTSWorker(text, self.current_language)
        self.tts_worker.signals.finished.connect(self.on_tts_finished)
        self.tts_worker.start()

    def on_tts_finished(self):
        if self._shutting_down:
            return
        self.is_speaking = False

    def test_tts(self):
        msg = "TTS test successful." if self.current_language == 'en' else "テスト成功"
        self.speak_response(msg)

    # ---------------- STT ---------------- #

    def toggle_listening(self):
        if self.is_listening or self.is_speaking:
            return
        self.start_listening()

    def start_listening(self):
        self.is_listening = True

        self.stt_worker = STTWorker(language=self.current_language)
        self.stt_worker.signals.result.connect(self.on_speech_recognized)
        self.stt_worker.signals.finished.connect(self.on_stt_finished)
        self.stt_worker.start()

    def on_speech_recognized(self, text):
        if self._shutting_down:
            return
        self.add_chat_message(text, True)
        self.process_with_ai(text)

    def on_stt_finished(self):
        self.is_listening = False

    # ---------------- Cleanup ---------------- #

    def _disconnect_worker_signals(self):
        """Stop background threads from invoking UI slots after close."""
        if self.ai_worker:
            try:
                self.ai_worker.signals.result.disconnect(self.on_ai_response)
                self.ai_worker.signals.error.disconnect(self.on_ai_error)
            except TypeError:
                pass
        if self.stt_worker:
            try:
                self.stt_worker.signals.result.disconnect(self.on_speech_recognized)
                self.stt_worker.signals.finished.disconnect(self.on_stt_finished)
            except TypeError:
                pass
        if self.tts_worker:
            try:
                self.tts_worker.signals.finished.disconnect(self.on_tts_finished)
            except TypeError:
                pass

    def closeEvent(self, event):
        self._shutting_down = True
        self._disconnect_worker_signals()

        wait_ms = 60_000
        if self.ai_worker and self.ai_worker.isRunning():
            self.ai_worker.wait(wait_ms)

        if self.stt_worker and self.stt_worker.isRunning():
            self.stt_worker.wait(wait_ms)

        if self.tts_worker and self.tts_worker.isRunning():
            self.tts_worker.wait(wait_ms)

        event.accept()