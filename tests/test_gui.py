"""GUI integration tests using offscreen Qt platform."""
import os
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication, QScrollArea
from src.gui.main_window import MainWindow
from src.core.nand_engine import BlockState


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_main_window_startup(qapp):
    win = MainWindow()
    assert win is not None
    assert not win.windowIcon().isNull()
    assert win.bridge.is_connected() is True
    assert win.engine.active_chip is not None
    assert win.engine.active_chip.manufacturer == "MICRON"


def test_sidebar_operations_do_not_overlap_at_compact_window_size(qapp):
    win = MainWindow()
    win.resize(1450, 770)
    win.show()
    qapp.processEvents()

    sidebar = win.findChild(QScrollArea)
    assert sidebar is not None
    assert sidebar.widgetResizable()
    assert sidebar.verticalScrollBar().maximum() > 0

    buttons = [win.btn_read, win.btn_write, win.btn_erase, win.btn_scan_bb, win.btn_abort]
    rects = [
        button.rect().translated(button.mapToGlobal(button.rect().topLeft()))
        for button in buttons
    ]
    for index, rect in enumerate(rects):
        assert all(not rect.intersects(other) for other in rects[index + 1:])

    win.close()


def test_main_window_hex_viewer(qapp):
    win = MainWindow()
    win._read_page_from_nand(0, 0)
    assert len(win.hex_viewer.current_data) >= 2048
    # Page 0 has U-Boot uImage header in mock bridge
    assert win.hex_viewer.current_data[0:4] == b"\x27\x05\x19\x56"


def test_main_window_pin_probe(qapp):
    win = MainWindow()
    win._probe_signals()
    # Check that status was logged
    log_text = win.log_viewer.txt_log.toPlainText()
    assert "Live bus probe" in log_text


def test_main_window_bad_block_scan(qapp):
    win = MainWindow()
    bad_blocks = win.engine.scan_bad_blocks(progress_cb=win._on_worker_progress)
    assert len(bad_blocks) >= 1
    # Check that block map state is updated
    for b in bad_blocks:
        assert win.engine.bad_block_table[b] == BlockState.BAD
        assert win.block_map_widget.canvas.block_states[b] == BlockState.BAD
