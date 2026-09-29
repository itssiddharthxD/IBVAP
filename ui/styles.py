"""
IBVAP dark theme — pure black palette, professional desktop software chrome.
"""

BG          = "#0A0A0A"
SIDEBAR     = "#111111"
PANEL       = "#161616"
PANEL_ALT   = "#1C1C1C"
BORDER      = "#2A2A2A"
BORDER_SOFT = "#222222"
ACCENT      = "#3D9B8F"
ACCENT_DIM  = "#2A6B63"
ACCENT_SOFT = "#142422"
TEXT        = "#EAEAEA"
TEXT_MUTED  = "#9A9A9A"
TEXT_DIM    = "#6A6A6A"
DANGER      = "#E05555"
WARN        = "#D4A017"
OK          = "#3D9B8F"

APP_STYLESHEET = f"""
QMainWindow {{
    background-color: {BG};
}}
QWidget {{
    color: {TEXT};
    font-family: "Segoe UI", "Inter", "Ubuntu", "Helvetica Neue", sans-serif;
    font-size: 12.5px;
}}
QLabel {{
    background-color: transparent;
    border: none;
}}
QStackedWidget {{
    background-color: {BG};
}}
/* Content pages inherit dark surface */
QStackedWidget > QWidget {{
    background-color: {BG};
}}

/* Sidebar */
#sidebar {{
    background-color: {SIDEBAR};
    border-right: 1px solid {BORDER};
}}
#brandMark {{
    background-color: {ACCENT_SOFT};
    border: 1px solid {ACCENT_DIM};
    border-radius: 6px;
}}
#brandMarkLetter {{
    color: {ACCENT};
    font-size: 12px;
    font-weight: 800;
}}
#brandTitle {{
    color: {TEXT};
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
#brandSub {{
    color: {TEXT_DIM};
    font-size: 9px;
    letter-spacing: 1.4px;
    font-weight: 600;
}}
QPushButton#navBtn {{
    background: transparent;
    color: {TEXT_MUTED};
    border: none;
    text-align: left;
    padding: 9px 12px;
    border-radius: 4px;
    font-size: 12.5px;
    font-weight: 500;
}}
QPushButton#navBtn:hover {{
    background: {PANEL};
    color: {TEXT};
}}
QPushButton#navBtn:checked {{
    background: {ACCENT_SOFT};
    color: {ACCENT};
    font-weight: 600;
    border-left: 3px solid {ACCENT};
    padding-left: 9px;
}}

/* Top bar — flat professional navbar */
#topbar {{
    background-color: {SIDEBAR};
    border-bottom: 1px solid {BORDER};
}}
#topbarDivider {{
    background-color: {BORDER};
    max-width: 1px;
    min-width: 1px;
}}
#topItem {{
    background-color: #131313;
    border: 1px solid #1E1E1E;
    border-radius: 3px;
}}
#topTitle {{
    color: {TEXT};
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.1px;
    padding: 0;
    background: transparent;
    border: none;
}}
#topTitleBar {{
    background-color: {ACCENT};
    border: none;
    border-radius: 1px;
}}
#topStatus {{
    color: {TEXT_MUTED};
    font-size: 12px;
    font-weight: 500;
    background: transparent;
    border: none;
}}
#topStatusReady {{
    color: {ACCENT};
    font-size: 12px;
    font-weight: 500;
    background: transparent;
    border: none;
}}
#topStatusError {{
    color: {DANGER};
    font-size: 12px;
    font-weight: 500;
    background: transparent;
    border: none;
}}
#topClock {{
    color: {TEXT_MUTED};
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.2px;
    background: transparent;
    border: none;
}}

/* Panels */
#panel, #metricPanel {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 4px;
}}

/* Buttons */
QPushButton#toolBtn {{
    background-color: {PANEL};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 5px 12px;
    border-radius: 3px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton#toolBtn:hover {{
    border-color: {ACCENT_DIM};
    color: {ACCENT};
}}
QPushButton#toolBtn:pressed {{
    background-color: {PANEL_ALT};
}}
QPushButton#toolBtnPrimary {{
    background-color: {ACCENT_DIM};
    color: {TEXT};
    border: 1px solid {ACCENT};
    padding: 5px 14px;
    border-radius: 3px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#toolBtnPrimary:hover {{
    background-color: {ACCENT};
    color: #06100E;
}}

/* Tables */
QTableWidget {{
    background-color: {PANEL};
    alternate-background-color: {PANEL_ALT};
    color: {TEXT};
    border: 1px solid {BORDER};
    gridline-color: {BORDER_SOFT};
    outline: none;
    font-size: 12px;
    border-radius: 4px;
}}
QTableWidget::item {{
    padding: 5px 8px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: {ACCENT_SOFT};
    color: {TEXT};
}}
QHeaderView::section {{
    background-color: {SIDEBAR};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    border-right: 1px solid {BORDER_SOFT};
    padding: 8px;
    font-size: 11px;
    font-weight: 600;
}}
QTableCornerButton::section {{
    background: {SIDEBAR};
    border: none;
}}

/* Inputs */
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit {{
    background-color: {PANEL_ALT};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 5px 8px;
    border-radius: 3px;
    selection-background-color: {ACCENT_DIM};
}}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: #3A3A3A;
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT_DIM};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {PANEL};
    color: {TEXT};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT_SOFT};
    outline: none;
}}
QCheckBox {{
    color: {TEXT};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDER};
    border-radius: 3px;
    background: {PANEL_ALT};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT_DIM};
    border-color: {ACCENT};
}}

QGroupBox {{
    color: {TEXT_MUTED};
    border: 1px solid {BORDER};
    border-radius: 4px;
    margin-top: 14px;
    padding-top: 12px;
    font-size: 11px;
    font-weight: 600;
    background: {PANEL};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 9px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #333333;
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: #444444;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 9px;
}}
QScrollBar::handle:horizontal {{
    background: #333333;
    border-radius: 4px;
}}

QDialog {{
    background-color: {BG};
}}
QMessageBox {{
    background-color: {PANEL};
}}

QLabel#pageTitle {{
    color: {TEXT};
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 0.2px;
}}
QLabel#pageHint {{
    color: {TEXT_DIM};
    font-size: 11px;
}}

QToolTip {{
    background-color: #222222;
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 4px 8px;
    font-size: 11px;
}}
"""
