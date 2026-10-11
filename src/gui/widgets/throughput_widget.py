"""
Universal NAND Flash Clone Tool - Throughput Speedometer & Transfer Monitor
Visual speed gauge, real-time speed history chart, ETA countdown, and progress tracking.
"""

from collections import deque
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient

from ...utils.helpers import format_bytes, format_speed, format_duration


class SpeedHistoryGraph(QWidget):
    """Mini sparkline graph showing transfer speed over time."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = deque(maxlen=60)
        for _ in range(60):
            self.history.append(0.0)
        self.max_speed = 30.0 # MB/s scale ceiling
        self.setFixedHeight(48)
        self.setStyleSheet("background-color: #0d1117; border-radius: 4px; border: 1px solid #21262d;")

    def add_sample(self, speed_mbps: float):
        self.history.append(speed_mbps)
        if speed_mbps > self.max_speed:
            self.max_speed = max(30.0, speed_mbps * 1.2)
        self.update()

    def reset(self):
        for i in range(len(self.history)):
            self.history[i] = 0.0
        self.max_speed = 30.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()
        if w < 10 or h < 10:
            return

        # Draw grid line at 50%
        painter.setPen(QPen(QColor("#21262d"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(0, h // 2, w, h // 2)

        # Plot speed history
        count = len(self.history)
        step_x = w / (count - 1) if count > 1 else 1

        points = []
        for i, val in enumerate(self.history):
            clamped = min(val, self.max_speed)
            ratio = clamped / self.max_speed if self.max_speed > 0 else 0
            y = h - (ratio * (h - 6)) - 3
            x = i * step_x
            points.append((x, y))

        if len(points) > 1:
            pen = QPen(QColor("#00d2ff"), 2)
            painter.setPen(pen)
            for i in range(len(points) - 1):
                painter.drawLine(int(points[i][0]), int(points[i][1]),
                                 int(points[i+1][0]), int(points[i+1][1]))


class ThroughputWidget(QWidget):
    """Comprehensive progress monitor with speed gauge and time telemetry."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Main stats card
        card = QFrame()
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(10)

        # Top row: Speed readout + graph
        top_row = QHBoxLayout()

        # Speedometer display
        speed_box = QVBoxLayout()
        self.lbl_speed_val = QLabel("0.00")
        self.lbl_speed_val.setStyleSheet("color: #00d2ff; font-size: 28px; font-weight: 700; font-family: 'Segoe UI', monospace;")
        self.lbl_speed_unit = QLabel("MB/s Current")
        self.lbl_speed_unit.setStyleSheet("color: #8b949e; font-size: 11px; text-transform: uppercase;")
        speed_box.addWidget(self.lbl_speed_val)
        speed_box.addWidget(self.lbl_speed_unit)

        top_row.addLayout(speed_box)

        # Peak & Avg stats
        stats_sub = QVBoxLayout()
        self.lbl_peak_speed = QLabel("Peak: 0.00 MB/s")
        self.lbl_peak_speed.setStyleSheet("color: #3fb950; font-size: 11px; font-weight: 600;")
        self.lbl_avg_speed = QLabel("Avg:  0.00 MB/s")
        self.lbl_avg_speed.setStyleSheet("color: #58a6ff; font-size: 11px; font-weight: 600;")
        stats_sub.addWidget(self.lbl_peak_speed)
        stats_sub.addWidget(self.lbl_avg_speed)
        top_row.addLayout(stats_sub)

        top_row.addSpacing(20)

        # Mini History Graph
        self.graph = SpeedHistoryGraph()
        top_row.addWidget(self.graph, stretch=1)

        card_layout.addLayout(top_row)

        # Middle: Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        card_layout.addWidget(self.progress_bar)

        # Bottom row: Transfer counts and timers
        bottom_row = QHBoxLayout()

        self.lbl_data_transferred = QLabel("0 B / 0 B")
        self.lbl_data_transferred.setStyleSheet("color: #f0f6fc; font-weight: 500;")

        self.lbl_block_counter = QLabel("Block: 0 / 0")
        self.lbl_block_counter.setStyleSheet("color: #8b949e;")

        self.lbl_elapsed = QLabel("Elapsed: 00:00")
        self.lbl_elapsed.setStyleSheet("color: #8b949e;")

        self.lbl_eta = QLabel("ETA: --:--")
        self.lbl_eta.setStyleSheet("color: #d29922; font-weight: 600;")

        bottom_row.addWidget(self.lbl_data_transferred)
        bottom_row.addWidget(self.lbl_block_counter)
        bottom_row.addStretch()
        bottom_row.addWidget(self.lbl_elapsed)
        bottom_row.addSpacing(12)
        bottom_row.addWidget(self.lbl_eta)

        card_layout.addLayout(bottom_row)
        layout.addWidget(card)

        self.peak_speed: float = 0.0

    def update_progress(
        self,
        percent: float,
        current_speed_mbps: float,
        avg_speed_mbps: float,
        bytes_done: int,
        total_bytes: int,
        current_block: int,
        total_blocks: int,
        elapsed_sec: float,
        eta_sec: float,
    ):
        if current_speed_mbps > self.peak_speed:
            self.peak_speed = current_speed_mbps

        self.lbl_speed_val.setText(f"{current_speed_mbps:.2f}")
        self.lbl_peak_speed.setText(f"Peak: {self.peak_speed:.2f} MB/s")
        self.lbl_avg_speed.setText(f"Avg:  {avg_speed_mbps:.2f} MB/s")

        self.graph.add_sample(current_speed_mbps)

        # Progress bar (0..1000 for tenth-percent accuracy)
        self.progress_bar.setValue(int(min(100.0, max(0.0, percent)) * 10))
        self.progress_bar.setFormat(f"{percent:.1f}%")

        self.lbl_data_transferred.setText(f"{format_bytes(bytes_done)} / {format_bytes(total_bytes)}")
        self.lbl_block_counter.setText(f"Block: {current_block} / {total_blocks}")
        self.lbl_elapsed.setText(f"Elapsed: {format_duration(elapsed_sec)}")
        self.lbl_eta.setText(f"ETA: {format_duration(eta_sec)}")

    def reset(self):
        self.peak_speed = 0.0
        self.lbl_speed_val.setText("0.00")
        self.lbl_peak_speed.setText("Peak: 0.00 MB/s")
        self.lbl_avg_speed.setText("Avg:  0.00 MB/s")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0.0%")
        self.lbl_data_transferred.setText("0 B / 0 B")
        self.lbl_block_counter.setText("Block: 0 / 0")
        self.lbl_elapsed.setText("Elapsed: 00:00")
        self.lbl_eta.setText("ETA: --:--")
        self.graph.reset()

