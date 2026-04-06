from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QComboBox,
    QFormLayout,
    QDialogButtonBox
)

class LanguageDialog(QDialog):
    """Dialog for language selection"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Language")
        self.setModal(True)
        self.setMinimumWidth(320)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #2C3E50;
                font-size: 13px;
            }
            QComboBox {
                color: #2C3E50;
                background-color: #FFFFFF;
                border: 1px solid #BDC3C7;
                border-radius: 6px;
                padding: 6px 10px;
                min-height: 28px;
            }
            QComboBox QAbstractItemView {
                color: #2C3E50;
                background-color: #FFFFFF;
                selection-background-color: #3498DB;
                selection-color: #FFFFFF;
            }
            QDialogButtonBox QPushButton {
                min-width: 72px;
                padding: 8px 16px;
            }
        """)
        self.layout = QVBoxLayout()

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("Japanese", "ja")

        if parent is not None and hasattr(parent, "current_language"):
            idx = self.lang_combo.findData(parent.current_language)
            if idx >= 0:
                self.lang_combo.setCurrentIndex(idx)

        form_layout = QFormLayout()
        form_layout.addRow("Language:", self.lang_combo)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.layout.addLayout(form_layout)
        self.layout.addWidget(button_box)
        self.setLayout(self.layout)

    def get_selected_language(self):
        return self.lang_combo.currentData()
