"""
Universal NAND Flash Clone Tool - Filesystem & Partition Analyzer Widget
Scans flash dumps or buffers for embedded partitions (UBI, SquashFS, uImage, DTB)
and allows extracting filesystems directly to disk.
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QFrame, QTextEdit
)
from PyQt6.QtCore import Qt

from ...core.fs_analyzer import scan_for_signatures, DetectedPartition
from ...utils.helpers import format_bytes


class FSAnalyzerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.partitions: List[DetectedPartition] = []
        self.loaded_data: Optional[bytes] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header toolbar
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #161b22; border-radius: 6px; padding: 4px;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(10, 6, 10, 6)

        self.lbl_title = QLabel("Discovered Embedded Partitions & Filesystems")
        self.lbl_title.setStyleSheet("color: #00d2ff; font-weight: 600; font-size: 13px;")
        top_layout.addWidget(self.lbl_title)

        top_layout.addStretch()

        self.btn_load_dump = QPushButton("Scan Dump File (.bin)...")
        self.btn_load_dump.clicked.connect(self._on_load_dump_file)
        top_layout.addWidget(self.btn_load_dump)

        self.btn_extract = QPushButton("Extract Partition...")
        self.btn_extract.setStyleSheet("background-color: #238636; color: white;")
        self.btn_extract.clicked.connect(self._on_extract_selected)
        top_layout.addWidget(self.btn_extract)

        layout.addWidget(top_bar)

        # Partition Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Partition / Image Name", "Type", "Start Offset", "Size", "Confidence"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self.table)

        # Details Viewer
        self.txt_details = QTextEdit()
        self.txt_details.setReadOnly(True)
        self.txt_details.setMaximumHeight(100)
        self.txt_details.setStyleSheet("background-color: #0d1117; font-family: 'Consolas', monospace; font-size: 11px;")
        self.txt_details.setPlaceholderText("Select a partition above to view technical headers and bootloader parameters...")
        layout.addWidget(self.txt_details)

    def scan_data(self, data: bytes, page_size: int = 2048, block_size: int = 131072):
        self.loaded_data = data
        self.partitions = scan_for_signatures(data, page_size=page_size, block_size=block_size)
        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(len(self.partitions))
        for r, p in enumerate(self.partitions):
            item_name = QTableWidgetItem(p.name)
            item_name.setForeground(Qt.GlobalColor.white)

            item_type = QTableWidgetItem(p.fs_type)
            item_type.setForeground(Qt.GlobalColor.cyan)

            item_off = QTableWidgetItem(p.start_offset_hex)
            item_size = QTableWidgetItem(format_bytes(p.size_bytes))
            item_conf = QTableWidgetItem(f"{p.confidence * 100:.0f}%")

            self.table.setItem(r, 0, item_name)
            self.table.setItem(r, 1, item_type)
            self.table.setItem(r, 2, item_off)
            self.table.setItem(r, 3, item_size)
            self.table.setItem(r, 4, item_conf)

        if self.partitions:
            self.table.selectRow(0)

    def _on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            self.txt_details.clear()
            return

        idx = selected_rows[0].row()
        if 0 <= idx < len(self.partitions):
            p = self.partitions[idx]
            lines = [
                f"Partition:  {p.name}",
                f"Type:       {p.fs_type}",
                f"Offset:     {p.start_offset_hex} ({p.start_offset:,} bytes)",
                f"Length:     {p.size_bytes:,} bytes ({format_bytes(p.size_bytes)})",
                f"Metadata:   {p.details}",
            ]
            self.txt_details.setPlainText("\n".join(lines))

    def _on_load_dump_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open NAND Dump File", "", "NAND Dumps (*.bin *.raw *.img);;All Files (*.*)")
        if path:
            with open(path, "rb") as f:
                data = f.read()
            self.scan_data(data)
            QMessageBox.information(self, "Scan Complete", f"Found {len(self.partitions)} embedded partitions/images in {path}")

    def _on_extract_selected(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows or not self.loaded_data:
            QMessageBox.warning(self, "No Selection", "Please select a partition to extract.")
            return

        idx = selected_rows[0].row()
        p = self.partitions[idx]

        save_name = f"extracted_{p.fs_type.replace(' ', '_').lower()}.bin"
        path, _ = QFileDialog.getSaveFileName(self, "Extract Partition", save_name, "Binary Files (*.bin);;All Files (*.*)")
        if path:
            part_data = self.loaded_data[p.start_offset : p.start_offset + p.size_bytes]
            with open(path, "wb") as f:
                f.write(part_data)
            QMessageBox.information(self, "Extracted", f"Extracted {len(part_data)} bytes to:\n{path}")

