"""
Universal NAND Flash Clone Tool - ONFI Parameter Page Parser
Full compliance with ONFI 1.0, 2.0, 2.1, 2.2, 2.3, 3.0, 3.1, 4.0 specifications.
Includes ONFI CRC-16 verification and triple-redundancy majority recovery.
"""

import struct
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


def onfi_crc16(data: bytes, initial: int = 0x4F4E) -> int:
    """
    ONFI standard 16-bit CRC algorithm.
    Polynomial: 0x8005 (x^16 + x^15 + x^2 + 1)
    Initial value: 0x4F4E (ASCII 'ON')
    Calculated across bytes 0 to 253 of parameter page.
    """
    crc = initial
    for byte in data:
        for i in range(8):
            bit = (byte >> i) & 1
            msb = (crc >> 15) & 1
            crc = (crc << 1) & 0xFFFF
            if msb ^ bit:
                crc ^= 0x8005
    return crc & 0xFFFF


@dataclass
class ONFIParameterPage:
    is_valid: bool
    manufacturer: str
    model: str
    jedec_id: int
    revision: str
    page_size: int          # Main data bytes per page
    spare_size: int         # Spare/OOB bytes per page
    pages_per_block: int
    blocks_per_lun: int
    lun_count: int
    total_blocks: int
    total_capacity_bytes: int
    col_addr_cycles: int
    row_addr_cycles: int
    bits_per_cell: int      # 1=SLC, 2=MLC, 3=TLC
    cell_type_str: str
    ecc_bits: int           # Required ECC bits
    block_endurance: int    # P/E cycles
    max_bad_blocks_per_lun: int
    timing_modes: List[int]
    max_tprog_us: int
    max_tbers_us: int
    max_tr_us: int
    crc_valid: bool
    raw_data: bytes

    @property
    def block_size(self) -> int:
        """Total size of one block in bytes (data only)."""
        return self.page_size * self.pages_per_block

    @property
    def total_capacity_mb(self) -> float:
        return self.total_capacity_bytes / (1024 * 1024)

    @property
    def total_capacity_gb(self) -> float:
        return self.total_capacity_bytes / (1024 * 1024 * 1024)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.is_valid,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "jedec_id": f"0x{self.jedec_id:02X}",
            "revision": self.revision,
            "page_size": self.page_size,
            "spare_size": self.spare_size,
            "pages_per_block": self.pages_per_block,
            "block_size": self.block_size,
            "blocks_per_lun": self.blocks_per_lun,
            "lun_count": self.lun_count,
            "total_blocks": self.total_blocks,
            "total_capacity_bytes": self.total_capacity_bytes,
            "total_capacity_mb": round(self.total_capacity_mb, 2),
            "col_addr_cycles": self.col_addr_cycles,
            "row_addr_cycles": self.row_addr_cycles,
            "cell_type": self.cell_type_str,
            "ecc_bits_required": self.ecc_bits,
            "block_endurance": self.block_endurance,
            "max_bad_blocks_per_lun": self.max_bad_blocks_per_lun,
            "timing_modes": self.timing_modes,
            "max_tprog_us": self.max_tprog_us,
            "max_tbers_us": self.max_tbers_us,
            "max_tr_us": self.max_tr_us,
            "crc_valid": self.crc_valid,
        }


def _decode_revision(rev_bits: int) -> str:
    revisions = []
    if rev_bits & (1 << 1):
        revisions.append("1.0")
    if rev_bits & (1 << 2):
        revisions.append("2.0")
    if rev_bits & (1 << 3):
        revisions.append("2.1")
    if rev_bits & (1 << 4):
        revisions.append("2.2")
    if rev_bits & (1 << 5):
        revisions.append("2.3")
    if rev_bits & (1 << 6):
        revisions.append("3.0")
    if rev_bits & (1 << 7):
        revisions.append("3.1")
    if rev_bits & (1 << 8):
        revisions.append("4.0")
    if rev_bits & (1 << 9):
        revisions.append("4.1")
    return ", ".join(revisions) if revisions else f"Unknown (0x{rev_bits:04X})"


def _decode_cell_type(bits: int) -> str:
    if bits == 1:
        return "SLC (Single-Level Cell)"
    elif bits == 2:
        return "MLC (Multi-Level Cell)"
    elif bits == 3:
        return "TLC (Triple-Level Cell)"
    elif bits == 4:
        return "QLC (Quad-Level Cell)"
    return f"{bits}-bits/cell"


def parse_single_onfi_page(data: bytes) -> Optional[ONFIParameterPage]:
    """Parses a single 256-byte ONFI parameter page."""
    if len(data) < 256:
        return None

    # Check ONFI signature 'O' 'N' 'F' 'I' (0x4F, 0x4E, 0x46, 0x49)
    if data[0:4] != b"ONFI":
        return None

    # Verify CRC-16
    calc_crc = onfi_crc16(data[0:254])
    stored_crc = struct.unpack_from("<H", data, 254)[0]
    crc_valid = (calc_crc == stored_crc)

    rev_mask = struct.unpack_from("<H", data, 4)[0]
    revision_str = _decode_revision(rev_mask)

    # Manufacturer & Model (ASCII padded with spaces)
    manufacturer = data[32:44].decode("ascii", errors="replace").strip()
    model = data[44:64].decode("ascii", errors="replace").strip()
    jedec_id = data[64]

    # Memory organization
    page_size = struct.unpack_from("<I", data, 80)[0]
    spare_size = struct.unpack_from("<H", data, 84)[0]
    pages_per_block = struct.unpack_from("<I", data, 92)[0]
    blocks_per_lun = struct.unpack_from("<I", data, 96)[0]
    lun_count = data[100]

    addr_cycles = data[101]
    row_addr_cycles = addr_cycles & 0x0F
    col_addr_cycles = (addr_cycles >> 4) & 0x0F

    bits_per_cell = data[102]
    cell_type_str = _decode_cell_type(bits_per_cell)

    max_bad_blocks_per_lun = struct.unpack_from("<H", data, 103)[0]
    block_endurance = struct.unpack_from("<H", data, 105)[0]
    ecc_bits = data[112]

    # Timing modes supported
    timing_mask = struct.unpack_from("<H", data, 129)[0]
    timing_modes = [m for m in range(6) if (timing_mask & (1 << m))]

    max_tprog_us = struct.unpack_from("<H", data, 133)[0]
    max_tbers_us = struct.unpack_from("<H", data, 135)[0]
    max_tr_us = struct.unpack_from("<H", data, 137)[0]

    # Sanity checks
    if page_size == 0 or pages_per_block == 0 or blocks_per_lun == 0 or lun_count == 0:
        return None

    total_blocks = blocks_per_lun * lun_count
    total_capacity = total_blocks * pages_per_block * page_size

    return ONFIParameterPage(
        is_valid=True,
        manufacturer=manufacturer,
        model=model,
        jedec_id=jedec_id,
        revision=revision_str,
        page_size=page_size,
        spare_size=spare_size,
        pages_per_block=pages_per_block,
        blocks_per_lun=blocks_per_lun,
        lun_count=lun_count,
        total_blocks=total_blocks,
        total_capacity_bytes=total_capacity,
        col_addr_cycles=col_addr_cycles,
        row_addr_cycles=row_addr_cycles,
        bits_per_cell=bits_per_cell,
        cell_type_str=cell_type_str,
        ecc_bits=ecc_bits,
        block_endurance=block_endurance,
        max_bad_blocks_per_lun=max_bad_blocks_per_lun,
        timing_modes=timing_modes,
        max_tprog_us=max_tprog_us,
        max_tbers_us=max_tbers_us,
        max_tr_us=max_tr_us,
        crc_valid=crc_valid,
        raw_data=data[:256],
    )


def parse_onfi_parameter_page(buffer: bytes) -> Optional[ONFIParameterPage]:
    """
    Parses ONFI parameter page data.
    Standard NAND chips provide 3 copies (at byte 0, 256, 512).
    This function tests each copy and picks the first valid CRC copy.
    If no copy has a valid CRC, performs bitwise majority voting and accepts the
    recovered page only when its CRC is valid.
    """
    if len(buffer) < 256:
        return None

    # Check each copy
    for offset in range(0, min(len(buffer), 768), 256):
        chunk = buffer[offset:offset + 256]
        if len(chunk) == 256 and chunk[0:4] == b"ONFI":
            page = parse_single_onfi_page(chunk)
            if page and page.crc_valid:
                return page
    # If we found copies but none had valid CRC, attempt bitwise majority voting
    if len(buffer) >= 768 and buffer[0:4] == b"ONFI":
        voted_data = bytearray(256)
        c0 = buffer[0:256]
        c1 = buffer[256:512]
        c2 = buffer[512:768]
        for i in range(256):
            b0, b1, b2 = c0[i], c1[i], c2[i]
            # Bitwise majority: (b0 & b1) | (b1 & b2) | (b0 & b2)
            voted_data[i] = (b0 & b1) | (b1 & b2) | (b0 & b2)

        page = parse_single_onfi_page(bytes(voted_data))
        if page and page.crc_valid:
            return page

    return None
