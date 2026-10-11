import pytest

from src.core.mock_bridge import MockTeensyBridge
from src.core.nand_engine import ActiveChipConfig, BlockState, NANDEngine
from src.core.chip_database import BusInterface, NANDChipInfo
from src.core.protocol import BusType


def make_engine(bridge):
    engine = NANDEngine(bridge)
    engine.active_chip = ActiveChipConfig(
        manufacturer="Test",
        model="Test NAND",
        page_size=2048,
        spare_size=64,
        pages_per_block=2,
        total_blocks=1,
        total_capacity_bytes=4096,
        col_addr_cycles=2,
        row_addr_cycles=4,
    )
    engine.bad_block_table = {0: BlockState.GOOD}
    return engine


def test_scan_bad_blocks_passes_detected_address_cycles():
    bridge = MockTeensyBridge()
    engine = make_engine(bridge)
    calls = []
    original_read_page = bridge.read_page

    def record_read_page(*args, **kwargs):
        calls.append(kwargs)
        return original_read_page(*args, **kwargs)

    bridge.read_page = record_read_page

    assert engine.scan_bad_blocks() == []
    assert len(calls) == 2
    assert all(call["col_cycles"] == 2 and call["row_cycles"] == 4 for call in calls)


def test_scan_bad_blocks_honors_last_page_marker():
    bridge = MockTeensyBridge()
    engine = make_engine(bridge)
    cfg = engine.active_chip
    cfg.pages_per_block = 4
    cfg.chip_info = NANDChipInfo(
        manufacturer="Test",
        part_number="Test NAND",
        bus_interface=BusInterface.PARALLEL_X8,
        voltage="3.3V",
        cell_type="MLC",
        page_size=2048,
        spare_size=64,
        pages_per_block=4,
        total_blocks=1,
        total_capacity_mb=0,
        col_addr_cycles=2,
        row_addr_cycles=3,
        bad_block_marker_offset=0,
        bad_block_marker_page="0, last",
    )
    calls = []

    def read_marker(page_addr, **kwargs):
        calls.append(page_addr)
        return b"\x00" if page_addr == 3 else b"\xFF"

    bridge.read_page = read_marker

    assert engine.scan_bad_blocks() == [0]
    assert calls == [0, 3]


def test_dump_fails_instead_of_padding_failed_page(tmp_path):
    bridge = MockTeensyBridge()
    bridge.read_page = lambda *args, **kwargs: b""
    engine = make_engine(bridge)

    with pytest.raises(RuntimeError, match="Failed to read page"):
        engine.dump_flash(str(tmp_path / "dump.bin"), include_oob=False)


def test_write_fails_when_erase_fails(tmp_path):
    bridge = MockTeensyBridge()
    bridge.erase_block = lambda *args, **kwargs: False
    engine = make_engine(bridge)
    input_file = tmp_path / "image.bin"
    input_file.write_bytes(b"\xAA" * 2048)

    with pytest.raises(RuntimeError, match="Failed to erase block"):
        engine.write_flash(str(input_file))


def test_write_fails_when_program_fails(tmp_path):
    bridge = MockTeensyBridge()
    bridge.write_page = lambda *args, **kwargs: False
    engine = make_engine(bridge)
    input_file = tmp_path / "image.bin"
    input_file.write_bytes(b"\xAA" * 2048)

    with pytest.raises(RuntimeError, match="Failed to program page"):
        engine.write_flash(str(input_file), erase_before_write=False)


def test_write_fails_when_input_does_not_fit(tmp_path):
    bridge = MockTeensyBridge()
    engine = make_engine(bridge)
    input_file = tmp_path / "oversized.bin"
    input_file.write_bytes(b"\xAA" * 6144)

    with pytest.raises(RuntimeError, match="does not fit"):
        engine.write_flash(str(input_file), erase_before_write=False)


def test_auto_detect_selects_spi_for_known_spi_nand():
    class SPIMockBridge(MockTeensyBridge):
        def __init__(self):
            super().__init__()
            self.bus_type = BusType.PARALLEL_X8
            self.configured_buses = []

        def read_onfi_parameter_page(self):
            return b""

        def read_chip_id(self):
            if self.bus_type == BusType.SPI_STANDARD:
                return bytes((0xC8, 0xB2, 0x48))
            return b"\xFF" * 5

        def set_bus_config(self, bus_type, timing_mode=0, ce_idx=0, vcc_en=True):
            self.configured_buses.append(bus_type)
            self.bus_type = bus_type
            return True

    bridge = SPIMockBridge()
    bridge.connect()
    engine = NANDEngine(bridge)

    chip = engine.auto_detect_chip()

    assert chip is not None
    assert chip.bus_interface == BusInterface.SPI_NAND.value
    assert bridge.bus_type == BusType.SPI_STANDARD


def test_auto_detect_refuses_to_guess_unknown_geometry():
    bridge = MockTeensyBridge()
    bridge.connect()
    bridge.read_onfi_parameter_page = lambda: b""
    bridge.read_chip_id = lambda: bytes((0x2C, 0x11, 0x22, 0x33, 0x44))
    engine = NANDEngine(bridge)

    assert engine.auto_detect_chip() is None
    assert engine.active_chip is None
