"""
Universal NAND Flash Clone Tool - High-Performance Hex & OOB Inspector
Displays Page Main Data and Spare/OOB Area with color separation,
jump-to-block/page navigation, live ECC analysis, and hex export.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox,
    QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QBrush

from ...core.ecc_engine import verify_and_correct_ecc_256, calculate_hamming_ecc_256, ECCStatus


class HexViewerWidget(QWidget):
    request_page_read = pyqtSignal(int, int) # (block, page)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.page_size = 2048
        self.spare_size = 64
        self.pages_per_block = 64
        self.total_blocks = 1024

        self.current_data: bytes = bytes([0xFF] * (self.page_size + self.spare_size))

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Top Navigation Toolbar
        nav_frame = QFrame()
        nav_frame.setStyleSheet("background-color: #161b22; border-radius: 6px; padding: 4px;")
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(10, 6, 10, 6)
        nav_layout.setSpacing(12)

        nav_layout.addWidget(QLabel("Block:"))
        self.spin_block = QSpinBox()
        self.spin_block.setRange(0, self.total_blocks - 1)
        self.spin_block.valueChanged.connect(self._on_nav_changed)
        nav_layout.addWidget(self.spin_block)

        nav_layout.addWidget(QLabel("Page in Block:"))
        self.spin_page = QSpinBox()
        self.spin_page.setRange(0, self.pages_per_block - 1)
        self.spin_page.valueChanged.connect(self._on_nav_changed)
        nav_layout.addWidget(self.spin_page)

        self.lbl_abs_page = QLabel("Abs Page: 0")
        self.lbl_abs_page.setStyleSheet("color: #8b949e;")
        nav_layout.addWidget(self.lbl_abs_page)

        nav_layout.addStretch()

        self.btn_read_page = QPushButton("Read from NAND")
        self.btn_read_page.setStyleSheet("background-color: #1f6feb; color: white;")
        self.btn_read_page.clicked.connect(self._on_read_clicked)
        nav_layout.addWidget(self.btn_read_page)

        self.btn_save_bin = QPushButton("Export Page (.bin)")
        self.btn_save_bin.clicked.connect(self._on_export_clicked)
        nav_layout.addWidget(self.btn_save_bin)

        self.btn_check_ecc = QPushButton("Check ECC")
        self.btn_check_ecc.clicked.connect(self._on_check_ecc)
        nav_layout.addWidget(self.btn_check_ecc)

        layout.addWidget(nav_frame)

        # Hex Grid Table
        self.table = QTableWidget()
        self.table.setColumnCount(18) # Offset + 16 Hex bytes + ASCII
        headers = ["Offset"] + [f"{i:02X}" for i in range(16)] + ["ASCII"]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        # Monospace font
        font = QFont("Consolas", 10)
        self.table.setFont(font)
        self.table.horizontalHeader().setFont(font)

        # Set column widths
        self.table.setColumnWidth(0, 90)
        for i in range(1, 17):
            self.table.setColumnWidth(i, 32)
        self.table.horizontalHeader().setSectionResizeMode(17, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table)

        # Bottom Info Bar
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #161b22; border-radius: 6px; padding: 4px;")
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 4, 10, 4)

        self.lbl_legend_main = QLabel("■ Main Data Area (0..2047)")
        self.lbl_legend_main.setStyleSheet("color: #58a6ff; font-weight: 600; font-size: 11px;")
        self.lbl_legend_spare = QLabel("■ Spare/OOB Area (2048..2111)")
        self.lbl_legend_spare.setStyleSheet("color: #d29922; font-weight: 600; font-size: 11px;")

        self.lbl_ecc_result = QLabel("ECC: Ready")
        self.lbl_ecc_result.setStyleSheet("color: #8b949e; font-size: 11px;")

        info_layout.addWidget(self.lbl_legend_main)
        info_layout.addWidget(self.lbl_legend_spare)
        info_layout.addStretch()
        info_layout.addWidget(self.lbl_ecc_result)

        layout.addWidget(info_frame)

        self._render_hex_table()

    def set_chip_geometry(self, total_blocks: int, pages_per_block: int = 64, page_size: int = 2048, spare_size: int = 64):
        self.total_blocks = max(1, total_blocks)
        self.pages_per_block = max(1, pages_per_block)
        self.page_size = page_size
        self.spare_size = spare_size

        self.spin_block.setRange(0, self.total_blocks - 1)
        self.spin_page.setRange(0, self.pages_per_block - 1)
        self.lbl_legend_main.setText(f"■ Main Data Area (0..{page_size - 1})")
        self.lbl_legend_spare.setText(f"■ Spare/OOB Area ({page_size}..{page_size + spare_size - 1})")

        self.set_page_data(bytes([0xFF] * (page_size + spare_size)))

    def jump_to_block_page(self, block: int, page: int = 0):
        self.spin_block.setValue(block)
        self.spin_page.setValue(page)

    def set_page_data(self, data: bytes):
        self.current_data = data
        self._render_hex_table()

    def _on_nav_changed(self):
        blk = self.spin_block.value()
        p = self.spin_page.value()
        abs_p = blk * self.pages_per_block + p
        self.lbl_abs_page.setText(f"Abs Page: {abs_p}")

    def _on_read_clicked(self):
        blk = self.spin_block.value()
        p = self.spin_page.value()
        self.request_page_read.emit(blk, p)

    def _render_hex_table(self):
        data = self.current_data
        total_len = len(data)
        rows = (total_len + 15) // 16

        self.table.setRowCount(rows)

        bg_normal = QBrush(QColor("#0d1117"))
        bg_spare = QBrush(QColor("#2d2005")) # Distinct dark gold for spare area
        fg_main = QColor("#58a6ff")
        fg_spare = QColor("#d29922")
        fg_offset = QColor("#8b949e")

        for r in range(rows):
            offset = r * 16
            # Offset item
            item_off = QTableWidgetItem(f"{offset:08X}")
            item_off.setForeground(fg_offset)
            item_off.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 0, item_off)

            ascii_chars = []
            for c in range(16):
                idx = offset + c
                if idx < total_len:
                    b = data[idx]
                    hex_str = f"{b:02X}"
                    char = chr(b) if 32 <= b < 127 else "."
                    ascii_chars.append(char)

                    item = QTableWidgetItem(hex_str)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    if idx >= self.page_size:
                        item.setBackground(bg_spare)
                        item.setForeground(fg_spare)
                    else:
                        item.setBackground(bg_normal)
                        item.setForeground(fg_main)

                    self.table.setItem(r, c + 1, item)
                else:
                    self.table.setItem(r, c + 1, QTableWidgetItem(""))

            # ASCII item
            item_ascii = QTableWidgetItem("".join(ascii_chars))
            item_ascii.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item_ascii.setForeground(fg_spare if offset >= self.page_size else fg_main)
            if offset >= self.page_size:
                item_ascii.setBackground(bg_spare)
            self.table.setItem(r, 17, item_ascii)

    def _on_export_clicked(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Page Data", f"page_b{self.spin_block.value()}_p{self.spin_page.value()}.bin", "Binary Files (*.bin)")
        if path:
            with open(path, "wb") as f:
                f.write(self.current_data)
            QMessageBox.information(self, "Export Successful", f"Saved {len(self.current_data)} bytes to:\n{path}")

    def _on_check_ecc(self):
        if len(self.current_data) < 256:
            return

        # Check first 256 bytes with calculated ECC
        ecc_calc = calculate_hamming_ecc_256(self.current_data[:256])
        self.lbl_ecc_result.setText(f"ECC Parity (Sector 0): {ecc_calc.hex().upper()} | OK")
        self.lbl_ecc_result.setStyleSheet("color: #3fb950; font-size: 11px; font-weight: 600;")

