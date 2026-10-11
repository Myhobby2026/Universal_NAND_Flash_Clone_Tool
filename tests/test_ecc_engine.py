"""Unit tests for Hamming ECC calculation, bitflip correction and diagnostics."""
import pytest
from src.core.ecc_engine import (
    calculate_hamming_ecc_256,
    verify_and_correct_ecc_256,
    ECCStatus,
    count_bitflips,
)


def test_ecc_calculation_and_no_error():
    data = (b"Antigravity Universal NAND Flash Tool 2026 Test Buffer 0123456789ABCDEF" * 4)[:256]
    assert len(data) == 256
    chunk = data

    ecc = calculate_hamming_ecc_256(chunk)
    assert len(ecc) == 3

    result = verify_and_correct_ecc_256(chunk, ecc)
    assert result.status == ECCStatus.NO_ERROR
    assert result.corrected_data == chunk
    assert result.bitflips == 0


def test_ecc_single_bit_correction():
    data = bytearray(b"Antigravity Universal NAND Flash Tool 2026 Test Buffer 0123456789ABCDEF" * 4)[:256]
    orig_data = bytes(data)
    ecc = calculate_hamming_ecc_256(orig_data)

    # Corrupt byte 42, bit 3
    data[42] ^= (1 << 3)
    corrupted_data = bytes(data)

    result = verify_and_correct_ecc_256(corrupted_data, ecc)
    assert result.status == ECCStatus.CORRECTABLE
    assert result.error_byte_offset == 42
    assert result.error_bit_offset == 3
    assert result.corrected_data == orig_data
    assert result.bitflips == 1


def test_count_bitflips():
    buf_a = b"\xFF\x00\xAA"
    buf_b = b"\xFE\x00\xAB"  # 1 bitflip in byte 0, 1 bitflip in byte 2
    assert count_bitflips(buf_a, buf_b) == 2
