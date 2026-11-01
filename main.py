"""CWNav desktop entry point. Run with python main.py."""
import sys
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox

from ui.styles import STYLE
from ui.main_window import Window


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)

    loading = QLabel('Loading CWNav maps and directory...')
    loading.setWindowTitle('CWNav')
    loading.setMargin(24)
    loading.show()
    app.processEvents()

    try:
        window = Window()
    except (OSError, ValueError, KeyError, TypeError) as error:
        loading.close()
        QMessageBox.critical(
            None,
            'CWNav could not load',
            f'Check the bundled maps and data/navigation-data.json.\n\n{error}'
        )
        return 1

    loading.close()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
