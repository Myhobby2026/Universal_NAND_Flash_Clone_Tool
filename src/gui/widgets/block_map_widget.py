"""
Universal NAND Flash Clone Tool - Interactive 2D Visual Block Map
Renders high-performance grid visualization of all NAND blocks with live status
updates, hover tooltips, and click-to-inspect hex navigation.
"""

from typing import Dict, Optional, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QMouseEvent

from ...core.nand_engine import BlockState


STATE_COLORS = {
    BlockState.UNKNOWN: QColor("#1e2530"),
    BlockState.GOOD: QColor("#1f6feb"),
    BlockState.READ_OK: QColor("#238636"),
    BlockState.BAD: QColor("#da3633"),
    BlockState.BITFLIP_CORRECTED: QColor("#d29922"),
    BlockState.PROGRAMMED: QColor("#00d2ff"),
    BlockState.ERASED: QColor("#8957e5"),
    BlockState.VERIFIED: QColor("#3fb950"),
    BlockState.MISMATCH: QColor("#f85149"),
}


class BlockMapCanvas(QWidget):
    block_clicked = pyqtSignal(int)
    block_hovered = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_blocks = 1024
        self.pages_per_block = 64
        self.page_size = 2048
        self.block_states: Dict[int, BlockState] = {i: BlockState.UNKNOWN for i in range(self.total_blocks)}
        self.selected_block: Optional[int] = None
        self.hovered_block: Optional[int] = None

        self.cell_size = 12
        self.cell_spacing = 2
        self.columns = 32

        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._update_geometry()

    def set_chip_geometry(self, total_blocks: int, pages_per_block: int = 64, page_size: int = 2048):
        self.total_blocks = max(1, total_blocks)
        self.pages_per_block = pages_per_block
        self.page_size = page_size
        self.block_states = {i: BlockState.UNKNOWN for i in range(self.total_blocks)}
        self.selected_block = None
        self._update_geometry()
        self.update()

    def set_block_state(self, block_idx: int, state: BlockState):
        if 0 <= block_idx < self.total_blocks:
            self.block_states[block_idx] = state
            self.update()

    def set_multiple_states(self, updates: Dict[int, BlockState]):
        for b, s in updates.items():
            if 0 <= b < self.total_blocks:
                self.block_states[b] = s
        self.update()

    def _update_geometry(self):
        # Calculate rows and columns
        if self.width() > 100:
            step = self.cell_size + self.cell_spacing
            self.columns = max(16, (self.width() - 20) // step)
        else:
            self.columns = 32

        rows = (self.total_blocks + self.columns - 1) // self.columns
        total_height = rows * (self.cell_size + self.cell_spacing) + 30
        self.setMinimumHeight(max(300, total_height))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_geometry()

    def _get_block_at_pos(self, pos: QPoint) -> Optional[int]:
        x = pos.x() - 10
        y = pos.y() - 10
        if x < 0 or y < 0:
            return None

        step = self.cell_size + self.cell_spacing
        col = x // step
        row = y // step

        if col >= self.columns:
            return None

        block_idx = row * self.columns + col
        if 0 <= block_idx < self.total_blocks:
            return block_idx
        return None

    def mouseMoveEvent(self, event: QMouseEvent):
        blk = self._get_block_at_pos(event.pos())
        if blk != self.hovered_block:
            self.hovered_block = blk
            if blk is not None:
                state = self.block_states.get(blk, BlockState.UNKNOWN)
                start_p = blk * self.pages_per_block
                end_p = start_p + self.pages_per_block - 1
                start_addr = blk * self.pages_per_block * self.page_size
                info = (
                    f"Block {blk} | State: {state.value.upper()} | "
                    f"Pages: {start_p}..{end_p} | Offset: 0x{start_addr:08X}"
                )
                self.setToolTip(info)
                self.block_hovered.emit(blk, info)
            else:
                self.setToolTip("")
                self.block_hovered.emit(-1, "")
            self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            blk = self._get_block_at_pos(event.pos())
            if blk is not None:
                self.selected_block = blk
                self.block_clicked.emit(blk)
                self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        step = self.cell_size + self.cell_spacing
        border_pen = QPen(QColor("#2d333b"), 1)
        select_pen = QPen(QColor("#00d2ff"), 2)
        hover_pen = QPen(QColor("#ffffff"), 1)

        start_x = 10
        start_y = 10

        for blk in range(self.total_blocks):
            col = blk % self.columns
            row = blk // self.columns

            x = start_x + col * step
            y = start_y + row * step

            # Cull offscreen rectangles
            if y + step < event.rect().top() or y > event.rect().bottom():
                continue

            state = self.block_states.get(blk, BlockState.UNKNOWN)
            color = STATE_COLORS.get(state, STATE_COLORS[BlockState.UNKNOWN])

            rect = QRectF(x, y, self.cell_size, self.cell_size)

            painter.setBrush(QBrush(color))
            if blk == self.selected_block:
                painter.setPen(select_pen)
            elif blk == self.hovered_block:
                painter.setPen(hover_pen)
            else:
                painter.setPen(border_pen)

            painter.drawRoundedRect(rect, 2, 2)


class BlockMapWidget(QWidget):
    """Container widget with header, legend statistics, and scrollable canvas."""
    block_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Legend & Stats Bar
        self.legend_frame = QFrame()
        self.legend_frame.setStyleSheet("background-color: #161b22; border-radius: 6px; padding: 4px;")
        leg_layout = QHBoxLayout(self.legend_frame)
        leg_layout.setContentsMargins(10, 4, 10, 4)
        leg_layout.setSpacing(16)

        self.lbl_unknown = self._create_legend_item("Unread", STATE_COLORS[BlockState.UNKNOWN])
        self.lbl_read = self._create_legend_item("Read OK", STATE_COLORS[BlockState.READ_OK])
        self.lbl_prog = self._create_legend_item("Programmed", STATE_COLORS[BlockState.PROGRAMMED])
        self.lbl_erased = self._create_legend_item("Erased", STATE_COLORS[BlockState.ERASED])
        self.lbl_bitflip = self._create_legend_item("Bitflips", STATE_COLORS[BlockState.BITFLIP_CORRECTED])
        self.lbl_bad = self._create_legend_item("Bad Block", STATE_COLORS[BlockState.BAD])

        leg_layout.addWidget(self.lbl_unknown)
        leg_layout.addWidget(self.lbl_read)
        leg_layout.addWidget(self.lbl_prog)
        leg_layout.addWidget(self.lbl_erased)
        leg_layout.addWidget(self.lbl_bitflip)
        leg_layout.addWidget(self.lbl_bad)
        leg_layout.addStretch()

        self.lbl_status = QLabel("Hover over a block to inspect")
        self.lbl_status.setStyleSheet("color: #8b949e; font-size: 11px;")
        leg_layout.addWidget(self.lbl_status)

        layout.addWidget(self.legend_frame)

        # Scroll Area for Block Canvas
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #0d1117; border: 1px solid #30363d; border-radius: 6px;")

        self.canvas = BlockMapCanvas()
        self.canvas.block_clicked.connect(self._on_block_clicked)
        self.canvas.block_hovered.connect(self._on_block_hovered)
        self.scroll_area.setWidget(self.canvas)

        layout.addWidget(self.scroll_area)

    def _create_legend_item(self, label: str, color: QColor) -> QWidget:
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)

        swatch = QFrame()
        swatch.setFixedSize(12, 12)
        swatch.setStyleSheet(f"background-color: {color.name()}; border-radius: 2px;")

        text = QLabel(label)
        text.setStyleSheet("color: #f0f6fc; font-size: 11px; font-weight: 500;")

        h.addWidget(swatch)
        h.addWidget(text)
        return container

    def _on_block_clicked(self, blk: int):
        self.block_selected.emit(blk)

    def _on_block_hovered(self, blk: int, info_str: str):
        if info_str:
            self.lbl_status.setText(info_str)
        else:
            self.lbl_status.setText("Click on any block to open in Hex Viewer")

    def set_chip_geometry(self, total_blocks: int, pages_per_block: int = 64, page_size: int = 2048):
        self.canvas.set_chip_geometry(total_blocks, pages_per_block, page_size)

    def set_block_state(self, blk: int, state: BlockState):
        self.canvas.set_block_state(blk, state)

    def update_states(self, updates: Dict[int, BlockState]):
        self.canvas.set_multiple_states(updates)

