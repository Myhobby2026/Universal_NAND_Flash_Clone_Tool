"""Unit tests for virtual mock Teensy bridge."""
import pytest
from src.core.mock_bridge import MockTeensyBridge
from src.core.nand_engine import NANDEngine, BlockState


def test_mock_bridge_operations():
    bridge = MockTeensyBridge()
    assert bridge.connect() is True
    assert bridge.is_connected() is True
    assert bridge.ping() is True

    # Test firmware info
    fw = bridge.get_firmware_info()
    assert fw["connected"] is True
    assert "Teensy 4.1" in fw["board"]

    # Test read ID
    id_bytes = bridge.read_chip_id()
    assert len(id_bytes) == 5
    assert id_bytes[0] == 0x2C  # Micron

    # Test read ONFI
    onfi_data = bridge.read_onfi_parameter_page()
    assert len(onfi_data) >= 256
    assert onfi_data[0:4] == b"ONFI"
    assert bridge.total_blocks == 4096

    # Test page read & write
    read_data = bridge.read_page(0, 0, 2112)
    assert len(read_data) == 2112
    # Page 0 has U-Boot uImage header
    assert read_data[0:4] == b"\x27\x05\x19\x56"

    # Test block erase
    assert bridge.erase_block(10) is True

    # Test engine auto-detect
    engine = NANDEngine(bridge)
    chip = engine.auto_detect_chip()
    assert chip is not None
    assert chip.manufacturer == "MICRON"
    assert chip.page_size == 2048
    assert chip.spare_size == 64
    assert chip.total_blocks == 4096
