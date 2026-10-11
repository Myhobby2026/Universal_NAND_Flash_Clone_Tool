"""Unit tests for embedded filesystem and partition signature scanner."""
import pytest
import struct
from src.core.fs_analyzer import scan_for_signatures


def test_scan_uboot_image():
    buffer = bytearray(65536)
    # Put uImage at offset 2048
    offset = 2048
    struct.pack_into(">IIIIIII4B32s", buffer, offset,
                     0x27051956, 0x12345678, 1700000000, 4096,
                     0x80008000, 0x80008000, 0x87654321,
                     5, 2, 2, 0, b"uImage-Kernel-Test")

    partitions = scan_for_signatures(bytes(buffer))
    assert len(partitions) >= 1
    p = partitions[0]
    assert "U-Boot" in p.fs_type or "uImage" in p.name
    assert p.start_offset == offset
    assert p.details["name"] == "uImage-Kernel-Test"


def test_scan_squashfs():
    buffer = bytearray(65536)
    offset = 4096
    buffer[offset : offset + 4] = b"sqsh"
    struct.pack_into("<HH", buffer, offset + 28, 4, 0)      # v4.0
    struct.pack_into("<Q", buffer, offset + 40, 32768)     # 32KB

    partitions = scan_for_signatures(bytes(buffer))
    assert any("SquashFS" in p.fs_type and p.start_offset == offset for p in partitions)
