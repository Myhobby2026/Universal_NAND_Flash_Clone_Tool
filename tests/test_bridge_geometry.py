import struct

from src.core.bridge_interface import TeensyBridge
from src.core.protocol import StatusCode


def test_page_and_erase_commands_include_geometry(monkeypatch):
    bridge = TeensyBridge()
    commands = []

    def send_command(command, payload=b"", timeout_sec=1.0):
        commands.append((command, payload))
        return StatusCode.STATUS_OK, b"\xFF"

    monkeypatch.setattr(bridge, "_send_command", send_command)

    assert bridge.read_page(0x123456, 0x200, 2048, col_cycles=2, row_cycles=4) == b"\xFF"
    assert bridge.write_page(0x123456, 0, b"\xAA", col_cycles=2, row_cycles=4)
    assert bridge.erase_block(0x1234, pages_per_block=256, row_cycles=4)
    assert bridge.scan_bad_blocks(0x12345, pages_per_block=256, oob_offset=4096, row_cycles=4) == []

    assert commands[0][1] == struct.pack("<IHHBB", 0x123456, 0x200, 2048, 2, 4)
    assert commands[1][1] == struct.pack("<IHH", 0x123456, 0, 1) + b"\xAA\x02\x04"
    assert commands[2][1] == struct.pack("<IIB", 0x1234, 256, 4)
    assert commands[3][1] == struct.pack("<IIHBB", 0x12345, 256, 4096, 2, 4)
