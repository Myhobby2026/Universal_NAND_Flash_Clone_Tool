"""Unit tests for ONFI parameter page parsing and CRC."""
import pytest
import struct
from src.core.onfi_parser import onfi_crc16, parse_onfi_parameter_page


def test_onfi_crc16():
    # Test vector: signature 'ONFI'
    data = b"ONFI"
    crc = onfi_crc16(data)
    assert isinstance(crc, int)
    assert 0 <= crc <= 0xFFFF


def test_onfi_parameter_page_parsing():
    raw_page = bytearray(256)
    raw_page[0:4] = b"ONFI"
    struct.pack_into("<H", raw_page, 4, 0x000E)  # rev 1.0, 2.0, 2.1
    raw_page[32:44] = b"SAMSUNG     "
    raw_page[44:64] = b"K9F2G08U0A          "
    raw_page[64] = 0xEC

    struct.pack_into("<I", raw_page, 80, 2048)   # Page size 2048
    struct.pack_into("<H", raw_page, 84, 64)     # Spare size 64
    struct.pack_into("<I", raw_page, 92, 64)     # Pages per block 64
    struct.pack_into("<I", raw_page, 96, 2048)   # Blocks per LUN 2048
    raw_page[100] = 1                            # 1 LUN
    raw_page[101] = (2 << 4) | 3                 # 2 col, 3 row cycles
    raw_page[102] = 1                            # SLC
    struct.pack_into("<H", raw_page, 105, 50000) # Endurance 50k
    raw_page[112] = 1                            # 1 bit ECC

    # Calculate CRC and store at offset 254
    crc = onfi_crc16(bytes(raw_page[:254]))
    struct.pack_into("<H", raw_page, 254, crc)

    parsed = parse_onfi_parameter_page(bytes(raw_page))
    assert parsed is not None
    assert parsed.is_valid is True
    assert parsed.crc_valid is True
    assert parsed.manufacturer == "SAMSUNG"
    assert parsed.model == "K9F2G08U0A"
    assert parsed.page_size == 2048
    assert parsed.spare_size == 64
    assert parsed.pages_per_block == 64
    assert parsed.total_blocks == 2048
    assert parsed.total_capacity_mb == 256.0
    assert parsed.cell_type_str == "SLC (Single-Level Cell)"


def test_onfi_parameter_page_rejects_invalid_crc():
    raw_page = bytearray(256)
    raw_page[0:4] = b"ONFI"
    struct.pack_into("<I", raw_page, 80, 2048)
    struct.pack_into("<I", raw_page, 92, 64)
    struct.pack_into("<I", raw_page, 96, 2048)
    raw_page[100] = 1

    assert parse_onfi_parameter_page(bytes(raw_page)) is None
