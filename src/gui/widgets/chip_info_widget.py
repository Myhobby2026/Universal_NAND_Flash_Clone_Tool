"""
Universal NAND Flash Clone Tool - Chip Information & Geometry Card
Displays parsed ONFI parameter attributes, database matching, and hardware geometry.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QFrame, QHBoxLayout
)
from PyQt6.QtCore import Qt

from ...core.nand_engine import ActiveChipConfig
from ...utils.helpers import format_bytes


class ChipInfoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        card = QFrame()
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(8)

        # Header: Chip Name + ONFI badge
        header_row = QHBoxLayout()
        self.lbl_chip_name = QLabel("No Chip Detected")
        self.lbl_chip_name.setStyleSheet("color: #00d2ff; font-size: 16px; font-weight: 700;")
        header_row.addWidget(self.lbl_chip_name)

        header_row.addStretch()

        self.lbl_badge = QLabel("NOT DETECTED")
        self.lbl_badge.setStyleSheet(
            "background-color: #30363d; color: #8b949e; font-size: 10px; font-weight: 700; "
            "padding: 2px 6px; border-radius: 4px;"
        )
        header_row.addWidget(self.lbl_badge)

        card_layout.addLayout(header_row)

        # Sub-header: Manufacturer + Interface
        self.lbl_mfr = QLabel("Connect hardware and click Auto-Detect")
        self.lbl_mfr.setStyleSheet("color: #8b949e; font-size: 12px;")
        card_layout.addWidget(self.lbl_mfr)

        # Geometry Grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)

        self.lbl_capacity = self._add_field(grid, 0, 0, "Capacity:", "-- MB")
        self.lbl_cell_type = self._add_field(grid, 0, 1, "Cell Type:", "--")
        self.lbl_page_size = self._add_field(grid, 1, 0, "Page Size:", "-- Bytes")
        self.lbl_spare_size = self._add_field(grid, 1, 1, "Spare (OOB):", "-- Bytes")
        self.lbl_block_size = self._add_field(grid, 2, 0, "Block Size:", "-- KB")
        self.lbl_pages_block = self._add_field(grid, 2, 1, "Pages / Block:", "--")
        self.lbl_total_blocks = self._add_field(grid, 3, 0, "Total Blocks:", "--")
        self.lbl_bus = self._add_field(grid, 3, 1, "Bus Interface:", "--")

        card_layout.addLayout(grid)
        layout.addWidget(card)

    def _add_field(self, grid: QGridLayout, row: int, col: int, label_text: str, default_val: str) -> QLabel:
        h = QHBoxLayout()
        h.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        val = QLabel(default_val)
        val.setStyleSheet("color: #f0f6fc; font-weight: 600; font-size: 11px;")
        h.addWidget(lbl)
        h.addWidget(val)
        h.addStretch()

        container = QWidget()
        container.setLayout(h)
        grid.addWidget(container, row, col)
        return val

    def update_chip_info(self, chip: Optional[ActiveChipConfig]):
        if not chip:
            self.lbl_chip_name.setText("No Chip Detected")
            self.lbl_mfr.setText("Connect hardware and click Auto-Detect")
            self.lbl_badge.setText("NOT DETECTED")
            self.lbl_badge.setStyleSheet("background-color: #30363d; color: #8b949e; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;")
            self.lbl_capacity.setText("--")
            self.lbl_cell_type.setText("--")
            self.lbl_page_size.setText("--")
            self.lbl_spare_size.setText("--")
            self.lbl_block_size.setText("--")
            self.lbl_pages_block.setText("--")
            self.lbl_total_blocks.setText("--")
            self.lbl_bus.setText("--")
            return

        self.lbl_chip_name.setText(chip.model)
        self.lbl_mfr.setText(f"{chip.manufacturer} • {chip.bus_interface}")

        if chip.is_onfi:
            self.lbl_badge.setText("ONFI CERTIFIED")
            self.lbl_badge.setStyleSheet("background-color: #1f6feb; color: white; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;")
        else:
            self.lbl_badge.setText("JEDEC / DB")
            self.lbl_badge.setStyleSheet("background-color: #238636; color: white; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;")

        self.lbl_capacity.setText(f"{format_bytes(chip.total_capacity_bytes)}")
        cell = "SLC"
        if chip.onfi_params:
            cell = chip.onfi_params.cell_type_str
        elif chip.chip_info:
            cell = chip.chip_info.cell_type
        self.lbl_cell_type.setText(cell)

        self.lbl_page_size.setText(f"{chip.page_size} B")
        self.lbl_spare_size.setText(f"{chip.spare_size} B")
        self.lbl_block_size.setText(f"{chip.block_size // 1024} KB")
        self.lbl_pages_block.setText(f"{chip.pages_per_block}")
        self.lbl_total_blocks.setText(f"{chip.total_blocks:,}")
        self.lbl_bus.setText(chip.bus_interface)

