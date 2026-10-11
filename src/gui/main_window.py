"""
Universal NAND Flash Clone Tool - Master GUI Application Window
Assembles Modern Obsidian Dark Interface, Hardware Bridge Connection Manager,
Visual 2D Block Map, Hex Inspector, Filesystem Analyzer, and Progress Telemetry.
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTabWidget, QSplitter, QGroupBox, QCheckBox, QFileDialog,
    QMessageBox, QStatusBar, QFrame, QDialog, QDialogButtonBox, QSpinBox,
    QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QColor

from .theme import STYLESHEET
from ..core.bridge_interface import BridgeInterface, TeensyBridge, list_serial_ports
from ..core.mock_bridge import MockTeensyBridge
from ..core.nand_engine import NANDEngine, ActiveChipConfig, ProgressUpdate, BlockState
from ..core.protocol import BusType
from .widgets.block_map_widget import BlockMapWidget
from .widgets.hex_viewer_widget import HexViewerWidget
from .widgets.throughput_widget import ThroughputWidget
from .widgets.chip_info_widget import ChipInfoWidget
from .widgets.fs_analyzer_widget import FSAnalyzerWidget
from .widgets.pinout_guide_widget import PinoutGuideWidget
from .widgets.log_viewer_widget import LogViewerWidget
from .workers.operation_worker import OperationWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal NAND Flash Clone Tool v1.4.0 [Teensy 4.1 High-Speed Bridge]")
        icon_path = Path(__file__).resolve().parents[2] / "assets" / "nand_icon.svg"
        self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1400, 900)
        self.setMinimumSize(1080, 720)

        # Core engine and bridge
        self.bridge: BridgeInterface = MockTeensyBridge()
        self.is_mock_mode: bool = True
        self.engine: NANDEngine = NANDEngine(self.bridge)
        self.worker: Optional[OperationWorker] = None

        # Apply dark theme
        self.setStyleSheet(STYLESHEET)

        self._init_ui()
        self._refresh_ports()

        # Connect default mock bridge to allow immediate demo experience
        self._connect_bridge()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # 1. Top Header & Hardware Connection Toolbar
        top_bar = self._create_top_toolbar()
        main_layout.addWidget(top_bar)

        # 2. Central Splitter (Left Sidebar vs Right Tabbed Content)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)

        # Left Sidebar (Chip Info & Action Controls)
        left_panel = self._create_left_sidebar()
        splitter.addWidget(left_panel)

        # Right Content (Tabs: Block Map, Hex Viewer, FS Analyzer, Pinout)
        right_panel = self._create_right_content()
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([420, 980])

        main_layout.addWidget(splitter, stretch=1)

        # 3. Bottom Log Console
        self.log_viewer = LogViewerWidget()
        self.log_viewer.setMaximumHeight(150)
        main_layout.addWidget(self.log_viewer)

        # 4. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Select hardware port or Virtual Simulation mode.")

    def _create_top_toolbar(self) -> QWidget:
        bar = QFrame()
        bar.setStyleSheet("background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 4px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        # Logo / Title
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        lbl_app = QLabel("UNIVERSAL NAND TOOL")
        lbl_app.setStyleSheet("color: #00d2ff; font-weight: 800; font-size: 13px; letter-spacing: 1px;")
        lbl_sub = QLabel("Teensy 4.1 Hardware Bridge")
        lbl_sub.setStyleSheet("color: #8b949e; font-size: 10px;")
        title_box.addWidget(lbl_app)
        title_box.addWidget(lbl_sub)
        layout.addLayout(title_box)

        layout.addSpacing(4)

        # Bridge Mode Selector
        layout.addWidget(QLabel("Bridge Mode:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("Virtual Simulation Bridge (Demo)", "MOCK")
        self.combo_mode.addItem("Teensy 4.1 Hardware (USB Serial)", "HW")
        self.combo_mode.setMinimumWidth(190)
        self.combo_mode.setMaximumWidth(230)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        layout.addWidget(self.combo_mode)

        # Port Selector
        layout.addWidget(QLabel("Port:"))
        self.combo_port = QComboBox()
        self.combo_port.setMinimumWidth(110)
        self.combo_port.setMaximumWidth(130)
        layout.addWidget(self.combo_port)

        self.btn_refresh_ports = QPushButton("↻ Refresh")
        self.btn_refresh_ports.clicked.connect(self._refresh_ports)
        layout.addWidget(self.btn_refresh_ports)

        # Connect / Disconnect button
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("btnPrimary")
        self.btn_connect.clicked.connect(self._toggle_connection)
        layout.addWidget(self.btn_connect)

        # Ping Button
        self.btn_ping = QPushButton("Ping Bridge")
        self.btn_ping.clicked.connect(self._ping_bridge)
        layout.addWidget(self.btn_ping)

        layout.addStretch()

        # Prominent Auto-Detect Button
        self.btn_autodetect = QPushButton("⚡ Auto-Detect")
        self.btn_autodetect.setObjectName("btnSuccess")
        self.btn_autodetect.setStyleSheet("padding: 7px 20px; font-weight: 700;")
        self.btn_autodetect.clicked.connect(self._autodetect_chip)
        layout.addWidget(self.btn_autodetect)

        return bar

    def _create_left_sidebar(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Chip Info Card
        self.chip_info_widget = ChipInfoWidget()
        layout.addWidget(self.chip_info_widget)

        # Actions GroupBox
        box_actions = QGroupBox("Flash Operations")
        act_layout = QVBoxLayout(box_actions)
        act_layout.setSpacing(8)

        self.btn_read = QPushButton("📥 Read / Dump Flash (Chip → File)")
        self.btn_read.setObjectName("btnSuccess")
        self.btn_read.clicked.connect(self._start_dump_dialog)
        act_layout.addWidget(self.btn_read)

        self.btn_write = QPushButton("📤 Write / Flash (File → Chip)")
        self.btn_write.setObjectName("btnPrimary")
        self.btn_write.clicked.connect(self._start_write_dialog)
        act_layout.addWidget(self.btn_write)

        self.btn_erase = QPushButton("🗑️ Erase Flash (Chip / Block Range)")
        self.btn_erase.setObjectName("btnDanger")
        self.btn_erase.clicked.connect(self._start_erase_dialog)
        act_layout.addWidget(self.btn_erase)

        self.btn_scan_bb = QPushButton("🔍 Scan Bad Block Table (BBT)")
        self.btn_scan_bb.clicked.connect(self._start_bad_block_scan)
        act_layout.addWidget(self.btn_scan_bb)

        self.btn_abort = QPushButton("⛔ EMERGENCY STOP / ABORT")
        self.btn_abort.setStyleSheet("background-color: #490202; color: #ff8888; font-weight: 700; border-color: #800000;")
        self.btn_abort.setEnabled(False)
        self.btn_abort.clicked.connect(self._abort_operation)
        act_layout.addWidget(self.btn_abort)

        layout.addWidget(box_actions)

        # Options GroupBox
        box_opts = QGroupBox("Cloning & Integrity Options")
        opts_layout = QVBoxLayout(box_opts)
        opts_layout.setSpacing(6)

        self.chk_include_oob = QCheckBox("Include OOB / Spare Area (Data + OOB)")
        self.chk_include_oob.setChecked(True)
        opts_layout.addWidget(self.chk_include_oob)

        self.chk_skip_bad = QCheckBox("Skip Factory Bad Blocks (Preserve BBT)")
        self.chk_skip_bad.setChecked(True)
        opts_layout.addWidget(self.chk_skip_bad)

        self.chk_auto_erase = QCheckBox("Auto-Erase Blocks Before Writing")
        self.chk_auto_erase.setChecked(True)
        opts_layout.addWidget(self.chk_auto_erase)

        layout.addWidget(box_opts)
        layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setWidget(content)
        return scroll_area

    def _create_right_content(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Tab Widget
        self.tabs = QTabWidget()

        # Tab 1: Visual Block Map & Speedometer
        tab_map = QWidget()
        map_layout = QVBoxLayout(tab_map)
        map_layout.setContentsMargins(4, 4, 4, 4)
        map_layout.setSpacing(6)

        self.throughput_widget = ThroughputWidget()
        map_layout.addWidget(self.throughput_widget)

        self.block_map_widget = BlockMapWidget()
        self.block_map_widget.block_selected.connect(self._on_block_map_selected)
        map_layout.addWidget(self.block_map_widget, stretch=1)

        self.tabs.addTab(tab_map, "🗺️ NAND Block Visualizer")

        # Tab 2: Hex Viewer
        self.hex_viewer = HexViewerWidget()
        self.hex_viewer.request_page_read.connect(self._read_page_from_nand)
        self.tabs.addTab(self.hex_viewer, "🔬 Hex & OOB Inspector")

        # Tab 3: Filesystem & Partition Analyzer
        self.fs_analyzer = FSAnalyzerWidget()
        self.tabs.addTab(self.fs_analyzer, "📦 Partition & Firmware Scanner")

        # Tab 4: Pinout & Live Signals
        self.pinout_guide = PinoutGuideWidget()
        self.pinout_guide.probe_requested.connect(self._probe_signals)
        self.pinout_guide.timing_changed.connect(self._change_timing_mode)
        self.pinout_guide.power_toggled.connect(self._toggle_power)
        self.tabs.addTab(self.pinout_guide, "🔌 Teensy 4.1 Pinout & Live Signals")

        layout.addWidget(self.tabs)
        return container

    def _refresh_ports(self):
        self.combo_port.clear()
        if self.is_mock_mode:
            self.combo_port.addItem("COM_MOCK (Teensy 4.1 Virtual)")
            return

        ports = list_serial_ports()
        for p in ports:
            dev = p["device"]
            desc = p["description"]
            is_t = p["is_teensy"]
            label = f"{dev} - {desc}" + (" [Teensy 4.1]" if is_t else "")
            self.combo_port.addItem(label, dev)

        if not ports:
            self.combo_port.addItem("No COM ports found")

    def _on_mode_changed(self, idx: int):
        mode = self.combo_mode.currentData()
        self.is_mock_mode = (mode == "MOCK")
        self._disconnect_bridge()
        self._refresh_ports()
        self._connect_bridge()

    def _toggle_connection(self):
        if self.bridge.is_connected():
            self._disconnect_bridge()
        else:
            self._connect_bridge()

    def _connect_bridge(self):
        if self.is_mock_mode:
            self.bridge = MockTeensyBridge()
            self.bridge.connect()
            self.engine = NANDEngine(self.bridge)
            self.btn_connect.setText("Disconnect")
            self.btn_connect.setObjectName("btnDanger")
            self.btn_connect.setStyleSheet("background-color: #b62324; color: white;")
            self.log_viewer.log("INFO", "Connected to Virtual Teensy 4.1 Simulation Bridge.")
            self.status_bar.showMessage("Connected to Teensy 4.1 (Virtual Emulation Mode)")
            # Auto detect on connect
            self._autodetect_chip()
        else:
            port = self.combo_port.currentData()
            if not port:
                QMessageBox.warning(self, "No Port", "Please select a serial port.")
                return
            self.bridge = TeensyBridge()
            ok = self.bridge.connect(port)
            if ok:
                self.engine = NANDEngine(self.bridge)
                self.btn_connect.setText("Disconnect")
                self.btn_connect.setObjectName("btnDanger")
                self.btn_connect.setStyleSheet("background-color: #b62324; color: white;")
                self.log_viewer.log("SUCCESS", f"Connected to Teensy 4.1 on {port}")
                self.status_bar.showMessage(f"Connected to Teensy 4.1 on {port}")
                self._autodetect_chip()
            else:
                self.log_viewer.log("ERROR", f"Failed to connect to {port}")
                QMessageBox.critical(self, "Connection Error", f"Could not connect to {port}. Verify Teensy 4.1 is plugged in.")

    def _disconnect_bridge(self):
        self.bridge.disconnect()
        self.btn_connect.setText("Connect")
        self.btn_connect.setObjectName("btnPrimary")
        self.btn_connect.setStyleSheet("background-color: #1f6feb; color: white;")
        self.log_viewer.log("INFO", "Bridge disconnected.")
        self.status_bar.showMessage("Bridge disconnected.")

    def _ping_bridge(self):
        if self.bridge.ping():
            fw = self.bridge.get_firmware_info()
            msg = f"Bridge Alive! Board: {fw.get('board')}, Version: {fw.get('version')}, Clock: {fw.get('mcu_freq_mhz', 600)} MHz"
            self.log_viewer.log("SUCCESS", msg)
            QMessageBox.information(self, "Ping Success", msg)
        else:
            self.log_viewer.log("ERROR", "Bridge ping failed - no response.")
            QMessageBox.critical(self, "Ping Failed", "No response from Teensy 4.1 bridge.")

    def _autodetect_chip(self):
        self.log_viewer.log("INFO", "Executing Auto-Detection sequence (Reset -> ONFI 0xEC -> JEDEC 0x90)...")
        chip = self.engine.auto_detect_chip()
        if chip:
            self.chip_info_widget.update_chip_info(chip)
            self.block_map_widget.set_chip_geometry(chip.total_blocks, chip.pages_per_block, chip.page_size)
            self.hex_viewer.set_chip_geometry(chip.total_blocks, chip.pages_per_block, chip.page_size, chip.spare_size)
            self.log_viewer.log("SUCCESS", f"Identified Chip: {chip.manufacturer} {chip.model} ({chip.total_capacity_mb:.1f} MB, {chip.total_blocks} Blocks)")
            self.status_bar.showMessage(f"NAND Ready: {chip.manufacturer} {chip.model} ({chip.total_capacity_mb:.1f} MB)")
            # Automatically read page 0 into hex viewer
            self._read_page_from_nand(0, 0)
        else:
            self.log_viewer.log("ERROR", "Auto-detection failed. No response from NAND chip.")
            QMessageBox.warning(self, "Auto-Detect Failed", "Could not detect NAND flash chip. Check socket and connections.")

    def _on_block_map_selected(self, blk: int):
        self.hex_viewer.jump_to_block_page(blk, 0)
        self.tabs.setCurrentIndex(1) # Switch to Hex Viewer tab
        self._read_page_from_nand(blk, 0)

    def _read_page_from_nand(self, blk: int, page: int):
        if not self.engine.active_chip:
            return
        cfg = self.engine.active_chip
        abs_page = blk * cfg.pages_per_block + page
        data = self.bridge.read_page(
            abs_page,
            col_addr=0,
            length=cfg.full_page_size,
            col_cycles=cfg.chip_info.col_addr_cycles if cfg.chip_info else cfg.col_addr_cycles,
            row_cycles=cfg.row_addr_cycles,
        )
        if data:
            self.hex_viewer.set_page_data(data)
            self.log_viewer.log("DEBUG", f"Read Page {abs_page} (Block {blk}, Page {page}) OK")

    def _start_bad_block_scan(self):
        if not self.engine.active_chip:
            QMessageBox.warning(self, "No Chip", "Please Auto-Detect chip first.")
            return

        self._start_worker("SCAN_BAD_BLOCKS", {})

    def _start_dump_dialog(self):
        if not self.engine.active_chip:
            QMessageBox.warning(self, "No Chip", "Please Auto-Detect chip first.")
            return

        cfg = self.engine.active_chip
        default_name = f"dump_{cfg.manufacturer}_{cfg.model.replace(' ', '_')}_{int(time.time())}.bin"
        path, _ = QFileDialog.getSaveFileName(self, "Save NAND Flash Dump", default_name, "Binary Files (*.bin);;All Files (*.*)")
        if not path:
            return

        params = {
            "filepath": path,
            "include_oob": self.chk_include_oob.isChecked(),
            "start_block": 0,
            "end_block": cfg.total_blocks - 1,
        }
        self.throughput_widget.reset()
        self._start_worker("DUMP", params)

    def _start_write_dialog(self):
        if not self.engine.active_chip:
            QMessageBox.warning(self, "No Chip", "Please Auto-Detect chip first.")
            return

        path, _ = QFileDialog.getOpenFileName(self, "Select Image File to Flash", "", "Binary Files (*.bin *.img *.raw);;All Files (*.*)")
        if not path:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Flash Write",
            f"Are you sure you want to write to {self.engine.active_chip.model}?\n"
            f"Input file: {path}\n\n"
            "This will erase existing data on target blocks!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        params = {
            "filepath": path,
            "skip_bad": self.chk_skip_bad.isChecked(),
            "erase_before": self.chk_auto_erase.isChecked(),
            "start_block": 0,
        }
        self.throughput_widget.reset()
        self._start_worker("WRITE", params)

    def _start_erase_dialog(self):
        if not self.engine.active_chip:
            QMessageBox.warning(self, "No Chip", "Please Auto-Detect chip first.")
            return

        reply = QMessageBox.warning(
            self,
            "Confirm Full Chip Erase",
            f"WARNING: This will ERASE ALL BLOCKS of the NAND Flash Memory ({self.engine.active_chip.model})!\n"
            "Factory bad blocks will be preserved.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        params = {
            "start_block": 0,
            "end_block": self.engine.active_chip.total_blocks - 1,
        }
        self._start_worker("ERASE", params)

    def _start_worker(self, task_name: str, params: dict):
        self._set_ui_busy(True)
        self.worker = OperationWorker(self.engine, task_name, params)
        self.worker.progress_updated.connect(self._on_worker_progress)
        self.worker.log_emitted.connect(self.log_viewer.log)
        self.worker.operation_finished.connect(self._on_worker_finished)
        self.worker.operation_failed.connect(self._on_worker_failed)
        self.worker.start()

    def _set_ui_busy(self, busy: bool):
        self.btn_read.setEnabled(not busy)
        self.btn_write.setEnabled(not busy)
        self.btn_erase.setEnabled(not busy)
        self.btn_scan_bb.setEnabled(not busy)
        self.btn_autodetect.setEnabled(not busy)
        self.btn_abort.setEnabled(busy)

    def _abort_operation(self):
        if self.worker and self.worker.isRunning():
            self.worker.request_abort()
            self.log_viewer.log("WARN", "Aborting operation...")

    def _on_worker_progress(self, u: ProgressUpdate):
        self.throughput_widget.update_progress(
            percent=u.percent,
            current_speed_mbps=u.current_speed_mbps,
            avg_speed_mbps=u.avg_speed_mbps,
            bytes_done=u.bytes_processed,
            total_bytes=u.total_bytes,
            current_block=u.current_block,
            total_blocks=u.total_blocks,
            elapsed_sec=u.elapsed_sec,
            eta_sec=u.eta_sec,
        )
        if u.block_state_change:
            blk, state = u.block_state_change
            self.block_map_widget.set_block_state(blk, state)

        self.status_bar.showMessage(u.status_message)

    def _on_worker_finished(self, result: dict):
        self._set_ui_busy(False)
        self.block_map_widget.update_states(self.engine.bad_block_table)
        self.log_viewer.log("SUCCESS", f"Operation completed successfully. Result: {result}")
        self.status_bar.showMessage("Operation completed successfully.")

        if "output_file" in result:
            out_file = result["output_file"]
            # Trigger filesystem analysis on dumped file
            try:
                with open(out_file, "rb") as f:
                    data = f.read(min(32 * 1024 * 1024, os.path.getsize(out_file))) # Sample first 32MB
                self.fs_analyzer.scan_data(data)
                self.log_viewer.log("INFO", f"Scanned dump file for firmware partitions.")
            except Exception:
                pass

            QMessageBox.information(
                self,
                "Dump Complete",
                f"Flash Dump Completed Successfully!\n"
                f"File: {out_file}\n"
                f"MD5: {result.get('md5')}\n"
                f"SHA-256: {result.get('sha256')}\n"
                f"Duration: {result.get('time_sec', 0):.1f}s"
            )

    def _on_worker_failed(self, error_msg: str):
        self._set_ui_busy(False)
        self.log_viewer.log("ERROR", f"Operation aborted / failed: {error_msg}")
        self.status_bar.showMessage("Operation failed.")
        QMessageBox.critical(self, "Operation Error", f"Operation encountered an error:\n{error_msg}")

    def _probe_signals(self):
        pins = self.bridge.probe_pins()
        self.pinout_guide.update_probe_results(pins)
        self.log_viewer.log("INFO", f"Live bus probe: R/B#={pins.get('RB')}, CE#={pins.get('CE')}, CLE={pins.get('CLE')}, ALE={pins.get('ALE')}")

    def _change_timing_mode(self, mode: int):
        self.bridge.set_bus_config(bus_type=BusType.PARALLEL_X8, timing_mode=mode)
        self.log_viewer.log("INFO", f"Updated bridge timing mode: Mode {mode}")

    def _toggle_power(self, power_on: bool):
        self.bridge.power_control(power_on)
        self.log_viewer.log("INFO", f"Power rail VCC: {'3.3V ON' if power_on else 'OFF'}")
