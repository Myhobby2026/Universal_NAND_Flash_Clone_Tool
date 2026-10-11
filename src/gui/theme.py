"""
Universal NAND Flash Clone Tool - Modern Obsidian Dark Theme
Windows 11 Fluent / Obsidian styling with high-contrast cybernetic accents.
"""

# Palette Constants
COLOR_BG_DARK = "#0d1117"
COLOR_BG_PANEL = "#161b22"
COLOR_BG_CARD = "#21262d"
COLOR_BORDER = "#30363d"
COLOR_BORDER_FOCUS = "#58a6ff"

COLOR_TEXT_PRIMARY = "#f0f6fc"
COLOR_TEXT_SECONDARY = "#8b949e"
COLOR_TEXT_MUTED = "#6e7681"

COLOR_ACCENT_CYAN = "#00d2ff"
COLOR_ACCENT_GREEN = "#2ea043"
COLOR_ACCENT_AMBER = "#d29922"
COLOR_ACCENT_RED = "#f85149"
COLOR_ACCENT_PURPLE = "#bc8cff"

STYLESHEET = """
QMainWindow {
    background-color: #0d1117;
    color: #f0f6fc;
}

QWidget {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    color: #f0f6fc;
}

/* ToolBar & Top Header */
QToolBar {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
    padding: 6px;
    spacing: 8px;
}

/* Panels & Frames */
QFrame#cardFrame, QGroupBox {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-top: 6px;
    padding: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    color: #58a6ff;
    font-weight: 600;
    font-size: 12px;
}

/* Push Buttons */
QPushButton {
    background-color: #21262d;
    color: #f0f6fc;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 500;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
}

QPushButton:pressed {
    background-color: #161b22;
}

QPushButton:disabled {
    background-color: #161b22;
    color: #6e7681;
    border-color: #21262d;
}

QPushButton#btnPrimary {
    background-color: #1f6feb;
    border-color: #388bfd;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#btnPrimary:hover {
    background-color: #388bfd;
}

QPushButton#btnSuccess {
    background-color: #238636;
    border-color: #2ea043;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#btnSuccess:hover {
    background-color: #2ea043;
}

QPushButton#btnDanger {
    background-color: #b62324;
    border-color: #da3633;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#btnDanger:hover {
    background-color: #da3633;
}

/* Combo Box */
QComboBox {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 5px 12px;
    color: #f0f6fc;
    min-height: 22px;
}

QComboBox:hover {
    border-color: #58a6ff;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #30363d;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
    color: #f0f6fc;
    padding: 4px;
}

/* Line Edit & Spin Box */
QLineEdit, QSpinBox {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f0f6fc;
    font-family: 'Consolas', 'Courier New', monospace;
}

QLineEdit:focus, QSpinBox:focus {
    border-color: #58a6ff;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #30363d;
    border-radius: 8px;
    background-color: #161b22;
    top: -1px;
}

QTabBar::tab {
    background-color: #0d1117;
    color: #8b949e;
    border: 1px solid #30363d;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    margin-right: 3px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #161b22;
    color: #58a6ff;
    font-weight: 600;
    border-bottom: 2px solid #58a6ff;
}

QTabBar::tab:hover:!selected {
    background-color: #161b22;
    color: #f0f6fc;
}

/* Progress Bar */
QProgressBar {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    text-align: center;
    color: #f0f6fc;
    font-weight: 600;
    font-size: 11px;
    height: 18px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #1f6feb, stop:1 #00d2ff);
    border-radius: 5px;
}

/* Table View */
QTableWidget, QTableView {
    background-color: #0d1117;
    border: 1px solid #30363d;
    gridline-color: #21262d;
    color: #f0f6fc;
    border-radius: 6px;
}

QTableWidget::item {
    padding: 5px;
}

QTableWidget::item:selected {
    background-color: #1f6feb;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    font-weight: 600;
    border: none;
    border-bottom: 1px solid #30363d;
    border-right: 1px solid #21262d;
    padding: 6px;
}

/* Scroll Bars */
QScrollBar:vertical {
    background-color: #0d1117;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #30363d;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #58a6ff;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0d1117;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #30363d;
    border-radius: 5px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #58a6ff;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    height: 0px;
}

/* Status Bar */
QStatusBar {
    background-color: #161b22;
    border-top: 1px solid #30363d;
    color: #8b949e;
    font-size: 12px;
}

/* Tooltips */
QToolTip {
    background-color: #21262d;
    color: #f0f6fc;
    border: 1px solid #58a6ff;
    border-radius: 4px;
    padding: 6px;
}
"""

