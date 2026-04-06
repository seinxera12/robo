import sys

from core.logging_setup import configure_logging

configure_logging()

from PyQt6.QtWidgets import QApplication
from ui.main_window import PersonalAssistantUI


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AI Personal Assistant")
    app.setOrganizationName("Personal Assistant")
    
    window = PersonalAssistantUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

