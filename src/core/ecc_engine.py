"""
Universal NAND Flash Clone Tool - ECC Engine & Bitflip Diagnostics
Implements SmartMedia/YAFFS standard 1-bit Hamming ECC (256/512 bytes)
with exact bitflip location/correction, and bitflip wear diagnostics.
"""

from enum import Enum
from typing import Tuple, List, Dict, Optional, Any
from dataclasses import dataclass


class ECCStatus(Enum):
    NO_ERROR = "No Error"
    CORRECTABLE = "1-Bit Error (Corrected)"
    ECC_ERROR = "ECC Parity Error (Data OK)"
    UNCORRECTABLE = "Uncorrectable Multi-Bit Error"


@dataclass
class ECCResult:
    status: ECCStatus
    corrected_data: bytes
    error_byte_offset: Optional[int] = None
    error_bit_offset: Optional[int] = None
    bitflips: int = 0


# Precomputed parity lookup table for fast 8-bit parity calculation
PARITY_TABLE = [bin(i).count("1") % 2 for i in range(256)]


def calculate_hamming_ecc_256(data: bytes) -> bytes:
    """
    Computes 3 bytes of standard SmartMedia/Samsung Hamming ECC for 256 bytes of data.
    ECC layout:
      P1, P2, P4, P8, P16, P32, P64, P128 (Column parities)
      P256, P512, P1024, P2048, P4096, P8192, etc. (Line parities)
    Returns: 3 bytes (ecc0, ecc1, ecc2)
    """
    if len(data) != 256:
        raise ValueError(f"Data must be exactly 256 bytes, got {len(data)}")

    p_col = [0] * 6     # P1, P1', P2, P2', P4, P4'
    p_line = [0] * 16   # P8..P2048' (line parities for 256 bytes = 2^8)

    # Column and line bit masks
    for byte_idx, b in enumerate(data):
        # Column parity
        for bit_idx in range(8):
            bit = (b >> bit_idx) & 1
            if bit:
                # Column parities
                if bit_idx & 1: p_col[1] ^= 1
                else:           p_col[0] ^= 1
                if bit_idx & 2: p_col[3] ^= 1
                else:           p_col[2] ^= 1
                if bit_idx & 4: p_col[5] ^= 1
                else:           p_col[4] ^= 1

                # Line parities (for 256 bytes: 8 bits of index)
                for l in range(8):
                    if byte_idx & (1 << l):
                        p_line[l * 2 + 1] ^= 1
                    else:
                        p_line[l * 2] ^= 1

    # Format into 3 ECC bytes (SmartMedia / NAND standard)
    # ECC[0]: P64, P64', P32, P32', P16, P16', P8, P8'
    # ECC[1]: P2048, P2048', P1024, P1024', P512, P512', P256, P256'
    # ECC[2]: P4, P4', P2, P2', P1, P1', 1, 1
    ecc0 = (p_line[7] << 7) | (p_line[6] << 6) | (p_line[5] << 5) | (p_line[4] << 4) | \
           (p_line[3] << 3) | (p_line[2] << 2) | (p_line[1] << 1) | p_line[0]

    ecc1 = (p_line[15] << 7) | (p_line[14] << 6) | (p_line[13] << 5) | (p_line[12] << 4) | \
           (p_line[11] << 3) | (p_line[10] << 2) | (p_line[9] << 1) | p_line[8]

    ecc2 = (p_col[5] << 7) | (p_col[4] << 6) | (p_col[3] << 5) | (p_col[2] << 4) | \
           (p_col[1] << 3) | (p_col[0] << 2) | 0x03

    # Inverted according to NAND standard (all 0xFF data -> all 0xFF ECC)
    return bytes([~ecc0 & 0xFF, ~ecc1 & 0xFF, ~ecc2 & 0xFF])


def verify_and_correct_ecc_256(data: bytes, read_ecc: bytes) -> ECCResult:
    """
    Verifies 256 bytes of data against 3 bytes of read ECC.
    If a 1-bit error is detected, repairs it and returns corrected data.
    """
    if len(data) != 256:
        raise ValueError("Data must be exactly 256 bytes")
    if len(read_ecc) != 3:
        raise ValueError("Read ECC must be exactly 3 bytes")

    calc_ecc = calculate_hamming_ecc_256(data)

    diff0 = calc_ecc[0] ^ read_ecc[0]
    diff1 = calc_ecc[1] ^ read_ecc[1]
    diff2 = calc_ecc[2] ^ read_ecc[2]

    # No error if diffs are all 0
    if diff0 == 0 and diff1 == 0 and diff2 == 0:
        return ECCResult(status=ECCStatus.NO_ERROR, corrected_data=data, bitflips=0)

    # Count number of 1-bits in diff
    total_diff_bits = bin(diff0).count("1") + bin(diff1).count("1") + bin(diff2).count("1")

    if total_diff_bits == 1:
        # Exactly one bit in ECC parity is wrong, data itself is intact
        return ECCResult(status=ECCStatus.ECC_ERROR, corrected_data=data, bitflips=1)

    # In SmartMedia Hamming: 11 pairs of parity bits. For a single bit error in data,
    # exactly 11 bits in diff will be 1 (one of each pair: P and P').
    if total_diff_bits == 11:
        # Recover byte offset and bit offset
        # Bit offset from diff2:
        bit_off = 0
        if (diff2 & 0x80) and not (diff2 & 0x40): bit_off |= 4
        if (diff2 & 0x20) and not (diff2 & 0x10): bit_off |= 2
        if (diff2 & 0x08) and not (diff2 & 0x04): bit_off |= 1

        # Byte offset from diff0 and diff1:
        byte_off = 0
        if (diff0 & 0x80) and not (diff0 & 0x40): byte_off |= (1 << 3)
        if (diff0 & 0x20) and not (diff0 & 0x10): byte_off |= (1 << 2)
        if (diff0 & 0x08) and not (diff0 & 0x04): byte_off |= (1 << 1)
        if (diff0 & 0x02) and not (diff0 & 0x01): byte_off |= (1 << 0)

        if (diff1 & 0x80) and not (diff1 & 0x40): byte_off |= (1 << 7)
        if (diff1 & 0x20) and not (diff1 & 0x10): byte_off |= (1 << 6)
        if (diff1 & 0x08) and not (diff1 & 0x04): byte_off |= (1 << 5)
        if (diff1 & 0x02) and not (diff1 & 0x01): byte_off |= (1 << 4)

        if byte_off < len(data):
            # Correct the single bit
            buf = bytearray(data)
            buf[byte_off] ^= (1 << bit_off)
            return ECCResult(
                status=ECCStatus.CORRECTABLE,
                corrected_data=bytes(buf),
                error_byte_offset=byte_off,
                error_bit_offset=bit_off,
                bitflips=1
            )

    return ECCResult(status=ECCStatus.UNCORRECTABLE, corrected_data=data, bitflips=total_diff_bits)


def count_bitflips(buf_a: bytes, buf_b: bytes) -> int:
    """Calculates hamming distance (number of bitflips) between two buffers."""
    flips = 0
    min_len = min(len(buf_a), len(buf_b))
    for i in range(min_len):
        xor = buf_a[i] ^ buf_b[i]
        flips += bin(xor).count("1")
    # Add trailing length differences as full bit differences
    flips += abs(len(buf_a) - len(buf_b)) * 8
    return flips


def analyze_block_wear(page_datas: List[bytes]) -> Dict[str, Any]:
    """
    Analyzes bitflips and wear statistics across pages in a block.
    Returns metrics useful for flash wear diagnostics and forensic reports.
    """
    total_bytes = sum(len(p) for p in page_datas)
    ones = 0
    zeros = 0
    for p in page_datas:
        for b in p:
            cnt1 = bin(b).count("1")
            ones += cnt1
            zeros += (8 - cnt1)

    total_bits = total_bytes * 8
    percent_ones = (ones / total_bits * 100.0) if total_bits > 0 else 0.0

    return {
        "total_bytes": total_bytes,
        "total_bits": total_bits,
        "one_bits": ones,
        "zero_bits": zeros,
        "percent_erased_state": round(percent_ones, 2),
        "is_erased": (ones == total_bits),
    }
