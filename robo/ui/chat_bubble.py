from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
    QLabel,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

class ChatBubble(QFrame):
    """Custom chat bubble widget with a more modern design"""
    def __init__(self, message, is_user=True):
        super().__init__()
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        layout = QHBoxLayout()

        layout.setContentsMargins(10, 5, 10, 5)

        bubble = QFrame()
        bubble.setMaximumWidth(400)
        bubble.setMinimumHeight(35)
        bubble.setFrameShape(QFrame.Shape.NoFrame)
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(10, 10, 10, 10)

        text = QLabel(message)
        text.setWordWrap(True)
        text.setFont(QFont("Segoe UI", 10))
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        if is_user:
            text.setAlignment(Qt.AlignmentFlag.AlignRight)
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #007ACC;
                    border-radius: 15px;
                    border-bottom-right-radius: 2px;
                }
                QLabel {
                    color: #FFFFFF;
                    background-color: transparent;
                }
            """)
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            text.setAlignment(Qt.AlignmentFlag.AlignLeft)
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #E8ECEF;
                    border-radius: 15px;
                    border-bottom-left-radius: 2px;
                }
                QLabel {
                    color: #1A1A1A;
                    background-color: transparent;
                }
            """)
            layout.addWidget(bubble)
            layout.addStretch()

        bubble_layout.addWidget(text)
        self.setLayout(layout)
