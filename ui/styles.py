"""UI styles and theme definitions for CWNav."""

ACCENT = '#00695c'

STYLE = '''
QWidget { font-family: "Segoe UI"; font-size: 13px; color: #24332e; background: #f7f6f2; }
QMainWindow { background: #f7f6f2; }
QLabel#title { font-size: 29px; font-weight: 700; color: #00695c; }
QLabel#heading { font-size: 15px; font-weight: 600; margin-top: 10px; }
QLabel#notice { background: #eee7d7; color: #604a19; padding: 8px; border-radius: 4px; }
QPushButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox { background: white; border: 1px solid #99a79f; border-radius: 4px; padding: 7px; min-height: 18px; }
QPushButton:hover { background: #e5eee9; }
QPushButton:pressed { background: #c9ded3; }
QPushButton:disabled { color: #727972; background: #eceeea; border-color: #b9c0ba; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QListWidget:focus { border: 2px solid #00695c; }
QListWidget { background: white; border: 1px solid #bdc6bf; border-radius: 4px; }
QListWidget::item { padding: 7px; border-bottom: 1px solid #eef0ed; }
QListWidget::item:selected { background: #d4e7de; color: #173b2c; }
QGraphicsView { background: white; border: 1px solid #bdc6bf; border-radius: 5px; }
QScrollArea { border: none; background: transparent; }
QToolTip { background: #ffffff; color: #24332e; border: 1px solid #99a79f; }
QCheckBox::indicator:checked { background: #00695c; border: 2px solid #00695c; }
QCheckBox::indicator:unchecked { background: white; border: 1px solid #62776b; }
'''
