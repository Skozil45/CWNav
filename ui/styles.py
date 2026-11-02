from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / 'assets'
CHECK_ICON = (ASSETS_DIR / 'check.svg').as_posix()
ARROW_DOWN_ICON = (ASSETS_DIR / 'arrow_down.svg').as_posix()
ARROW_UP_ICON = (ASSETS_DIR / 'arrow_up.svg').as_posix()

ACCENT = '#00695c'

STYLE = f'''
QWidget {{
    font-family: "Segoe UI";
    font-size: 13px;
    color: #24332e;
    background: #f7f6f2;
}}
QMainWindow {{
    background: #f7f6f2;
}}
QLabel#title {{
    font-size: 28px;
    font-weight: 700;
    color: #00695c;
}}
QLabel#heading {{
    font-size: 14px;
    font-weight: 600;
    color: #1b2622;
}}
QToolButton#accordion {{
    background: #e7ede8;
    border: 1px solid #b5c2ba;
    border-radius: 4px;
    padding: 8px;
    font-weight: 600;
}}
QToolButton#accordion:hover {{
    background: #d4e7de;
}}
QToolButton#accordion:focus {{
    border: 1.5px solid #00695c;
}}

/* Form elements & buttons: cleaner, thinner outline and comfortable padding */
QPushButton, QLineEdit {{
    background: white;
    border: 1px solid #b5c2ba;
    border-radius: 4px;
    padding: 6px 12px;
    min-height: 18px;
}}
QPushButton:hover {{
    background: #e5eee9;
    border-color: #00695c;
}}
QPushButton:pressed {{
    background: #c9ded3;
}}
QPushButton:disabled {{
    color: #8c948e;
    background: #eaecea;
    border-color: #cfd4d0;
}}
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QListWidget:focus {{
    border: 1.5px solid #00695c;
}}

/* ComboBox with clean, seamless dropdown arrow */
QComboBox {{
    background: white;
    border: 1px solid #b5c2ba;
    border-radius: 4px;
    padding: 5px 28px 5px 10px;
    min-height: 20px;
}}
QComboBox:hover {{
    border-color: #00695c;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #ccd4cf;
    background: #f7f9f7;
}}
QComboBox::drop-down:hover {{
    background: #e2ede6;
}}
QComboBox::down-arrow {{
    image: url({ARROW_DOWN_ICON});
    width: 12px;
    height: 12px;
}}

/* SpinBox & DoubleSpinBox with seamless borders and up/down arrows */
QSpinBox, QDoubleSpinBox {{
    background: white;
    border: 1px solid #b5c2ba;
    border-radius: 4px;
    padding-right: 22px;
    padding-left: 8px;
    padding-top: 4px;
    padding-bottom: 4px;
    min-height: 20px;
}}
QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: #00695c;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #ccd4cf;
    border-bottom: 1px solid #ccd4cf;
    background: #f7f9f7;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
    background: #e2ede6;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url({ARROW_UP_ICON});
    width: 10px;
    height: 10px;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: padding;
    subcontrol-position: bottom right;
    width: 20px;
    border-left: 1px solid #ccd4cf;
    background: #f7f9f7;
}}
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: #e2ede6;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url({ARROW_DOWN_ICON});
    width: 10px;
    height: 10px;
}}

/* ListWidget */
QListWidget {{
    background: white;
    border: 1px solid #b5c2ba;
    border-radius: 4px;
}}
QListWidget::item {{
    padding: 7px;
    border-bottom: 1px solid #eef0ed;
}}
QListWidget::item:selected {{
    background: #d4e7de;
    color: #173b2c;
}}

/* Nearby results unified card header & list */
QLabel#near_header {{
    background: #e7ede8;
    color: #173b2c;
    font-weight: 600;
    font-size: 12px;
    padding: 6px 10px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border: 1px solid #b5c2ba;
    border-bottom: 1px solid #ccd6ce;
}}
QListWidget#nearby_list {{
    border-top: none;
    border-top-left-radius: 0;
    border-top-right-radius: 0;
}}

/* Map graphics view & scroll */
QGraphicsView {{
    background: white;
    border: 1px solid #b5c2ba;
    border-radius: 5px;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QToolTip {{
    background: #ffffff;
    color: #24332e;
    border: 1px solid #99a79f;
}}

/* Rounded Checkbox with checkmark inside */
QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
}}
QCheckBox::indicator:unchecked {{
    background: white;
    border: 1.5px solid #7d8f84;
}}
QCheckBox::indicator:unchecked:hover {{
    border-color: #00695c;
    background: #f0f6f2;
}}
QCheckBox::indicator:checked {{
    background: #00695c;
    border: 1.5px solid #00695c;
    image: url({CHECK_ICON});
}}
QCheckBox::indicator:checked:hover {{
    background: #00796b;
    border-color: #00796b;
}}
'''
