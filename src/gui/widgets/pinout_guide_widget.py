"""
Universal NAND Flash Clone Tool - Hardware Bridge & Pinout Guide
Wiring diagram reference table, live pin state logic analyzer, and power rail controls.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QComboBox, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...core.protocol import BusType


PIN_MAP_DATA = [
    ("TSOP-48 Pin 7", "R/B# (Ready/Busy)", "Teensy 4.1 Pin 8", "Input (Pull-up 10k required)"),
    ("TSOP-48 Pin 8", "RE# (Read Enable)", "Teensy 4.1 Pin 5", "Output (Active Low)"),
    ("TSOP-48 Pin 9", "CE# (Chip Enable 1)", "Teensy 4.1 Pin 6", "Output (Active Low)"),
    ("TSOP-48 Pin 10", "CE2# (Chip Enable 2)", "Teensy 4.1 Pin 7", "Output (Dual-die chips)"),
    ("TSOP-48 Pin 12, 34", "VCC (Core & I/O 3.3V)", "Teensy 3.3V / Pin 10", "Power (0.1µF+10µF cap)"),
    ("TSOP-48 Pin 13, 35", "VSS (Ground)", "Teensy GND", "Ground return"),
    ("TSOP-48 Pin 16", "CLE (Command Latch)", "Teensy 4.1 Pin 2", "Output (High on command)"),
    ("TSOP-48 Pin 17", "ALE (Address Latch)", "Teensy 4.1 Pin 3", "Output (High on address)"),
    ("TSOP-48 Pin 18", "WE# (Write Enable)", "Teensy 4.1 Pin 4", "Output (Active Low)"),
    ("TSOP-48 Pin 19", "WP# (Write Protect)", "Teensy 4.1 Pin 9", "Output (High = Write ON)"),
    ("TSOP-48 Pin 29", "I/O 0 (Data 0)", "Teensy 4.1 Pin 14 (A0)", "Bi-directional Bus"),
    ("TSOP-48 Pin 30", "I/O 1 (Data 1)", "Teensy 4.1 Pin 15 (A1)", "Bi-directional Bus"),
    ("TSOP-48 Pin 31", "I/O 2 (Data 2)", "Teensy 4.1 Pin 16 (A2)", "Bi-directional Bus"),
    ("TSOP-48 Pin 32", "I/O 3 (Data 3)", "Teensy 4.1 Pin 17 (A3)", "Bi-directional Bus"),
    ("TSOP-48 Pin 41", "I/O 4 (Data 4)", "Teensy 4.1 Pin 18 (A4)", "Bi-directional Bus"),
    ("TSOP-48 Pin 42", "I/O 5 (Data 5)", "Teensy 4.1 Pin 19 (A5)", "Bi-directional Bus"),
    ("TSOP-48 Pin 43", "I/O 6 (Data 6)", "Teensy 4.1 Pin 20 (A6)", "Bi-directional Bus"),
    ("TSOP-48 Pin 44", "I/O 7 (Data 7)", "Teensy 4.1 Pin 21 (A7)", "Bi-directional Bus"),
    ("SPI NAND Pin 1", "CS#", "Teensy 4.1 Pin 10", "Chip Select (Active Low)"),
    ("SPI NAND Pin 2", "SO / MISO", "Teensy 4.1 Pin 12", "SPI Data Out"),
    ("SPI NAND Pin 5", "SI / MOSI", "Teensy 4.1 Pin 11", "SPI Data In"),
    ("SPI NAND Pin 6", "SCK", "Teensy 4.1 Pin 27", "SPI Clock (up to 60MHz)"),
]


class PinoutGuideWidget(QWidget):
    probe_requested = pyqtSignal()
    timing_changed = pyqtSignal(int)
    power_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.power_on = True
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Top Control Card: Live Probing & Timings
        ctrl_card = QFrame()
        ctrl_card.setObjectName("cardFrame")
        ctrl_layout = QHBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(10, 8, 10, 8)
        ctrl_layout.setSpacing(16)

        # Timing mode
        ctrl_layout.addWidget(QLabel("Timing Mode:"))
        self.combo_timing = QComboBox()
        self.combo_timing.addItems([
            "Mode 0 (Legacy 50ns)",
            "Mode 1 (35ns)",
            "Mode 2 (30ns)",
            "Mode 3 (20ns)",
            "Mode 4 (15ns)",
            "Mode 5 (Ultra Fast 10ns)",
        ])
        self.combo_timing.currentIndexChanged.connect(lambda idx: self.timing_changed.emit(idx))
        ctrl_layout.addWidget(self.combo_timing)

        # Power Toggle
        self.btn_power = QPushButton("VCC: 3.3V ON")
        self.btn_power.setStyleSheet("background-color: #238636; color: white;")
        self.btn_power.clicked.connect(self._toggle_power)
        ctrl_layout.addWidget(self.btn_power)

        ctrl_layout.addStretch()

        # Pin Probe button & indicator LEDs
        self.btn_probe = QPushButton("Probe Live Bus Signals")
        self.btn_probe.clicked.connect(lambda: self.probe_requested.emit())
        ctrl_layout.addWidget(self.btn_probe)

        self.led_rb = self._create_led("R/B# (Ready)")
        self.led_ce = self._create_led("CE#")
        self.led_cle = self._create_led("CLE")
        self.led_ale = self._create_led("ALE")

        ctrl_layout.addWidget(self.led_rb)
        ctrl_layout.addWidget(self.led_ce)
        ctrl_layout.addWidget(self.led_cle)
        ctrl_layout.addWidget(self.led_ale)

        layout.addWidget(ctrl_card)

        # Pinout Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Flash Chip Pin", "Signal Function", "Teensy 4.1 Pin", "Notes & Pull-up Rules"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self.table.setRowCount(len(PIN_MAP_DATA))
        for r, (ch_pin, sig, teensy_pin, notes) in enumerate(PIN_MAP_DATA):
            self.table.setItem(r, 0, QTableWidgetItem(ch_pin))
            self.table.setItem(r, 1, QTableWidgetItem(sig))
            item_t = QTableWidgetItem(teensy_pin)
            item_t.setForeground(Qt.GlobalColor.cyan)
            self.table.setItem(r, 2, item_t)
            self.table.setItem(r, 3, QTableWidgetItem(notes))

        layout.addWidget(self.table)

    def _create_led(self, text: str) -> QWidget:
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        swatch = QFrame()
        swatch.setFixedSize(10, 10)
        swatch.setStyleSheet("background-color: #3fb950; border-radius: 5px;")
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        h.addWidget(swatch)
        h.addWidget(lbl)
        container.swatch = swatch
        return container

    def update_probe_results(self, pin_states: dict):
        rb = pin_states.get("RB", True)
        ce = pin_states.get("CE", False)
        cle = pin_states.get("CLE", False)
        ale = pin_states.get("ALE", False)

        self.led_rb.swatch.setStyleSheet(f"background-color: {'#3fb950' if rb else '#f85149'}; border-radius: 5px;")
        self.led_ce.swatch.setStyleSheet(f"background-color: {'#3fb950' if ce else '#30363d'}; border-radius: 5px;")
        self.led_cle.swatch.setStyleSheet(f"background-color: {'#3fb950' if cle else '#30363d'}; border-radius: 5px;")
        self.led_ale.swatch.setStyleSheet(f"background-color: {'#3fb950' if ale else '#30363d'}; border-radius: 5px;")

    def _toggle_power(self):
        self.power_on = not self.power_on
        if self.power_on:
            self.btn_power.setText("VCC: 3.3V ON")
            self.btn_power.setStyleSheet("background-color: #238636; color: white;")
        else:
            self.btn_power.setText("VCC: OFF")
            self.btn_power.setStyleSheet("background-color: #da3633; color: white;")
        self.power_toggled.emit(self.power_on)

