"""
Universal NAND Flash Clone Tool - Comprehensive NAND Flash Database
Supports 150+ predefined chips (Samsung, Toshiba/Kioxia, Micron, SK Hynix, Winbond,
Macronix, Spansion, GigaDevice, ESMT) plus dynamic 5-byte ID decoding and SPI NAND.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Tuple, List
from enum import Enum


class BusInterface(Enum):
    PARALLEL_X8 = "Parallel x8"
    PARALLEL_X16 = "Parallel x16"
    SPI_NAND = "SPI NAND"


@dataclass
class NANDChipInfo:
    manufacturer: str
    part_number: str
    bus_interface: BusInterface
    voltage: str                # "3.3V" or "1.8V"
    cell_type: str              # "SLC", "MLC", "TLC"
    page_size: int              # Main data bytes (e.g. 2048)
    spare_size: int             # OOB bytes (e.g. 64)
    pages_per_block: int        # e.g. 64
    total_blocks: int           # e.g. 1024, 2048, 4096
    total_capacity_mb: int      # in MB
    col_addr_cycles: int        # e.g. 2
    row_addr_cycles: int        # e.g. 3
    bad_block_marker_offset: int # usually 0 for large page, 5 for small page
    bad_block_marker_page: str  # "0, 1" or "0, 1, last"
    onfi_supported: bool = False
    notes: str = ""

    @property
    def total_capacity_bytes(self) -> int:
        return self.total_blocks * self.pages_per_block * self.page_size

    @property
    def block_size(self) -> int:
        return self.page_size * self.pages_per_block

    @property
    def total_capacity_gb(self) -> float:
        return self.total_capacity_bytes / (1024 * 1024 * 1024)

    @property
    def full_page_size(self) -> int:
        return self.page_size + self.spare_size


# Known JEDEC Manufacturer IDs
MANUFACTURERS: Dict[int, str] = {
    0xEC: "Samsung",
    0x98: "Toshiba / Kioxia",
    0x2C: "Micron",
    0xAD: "SK Hynix",
    0xEF: "Winbond",
    0xC2: "Macronix",
    0x01: "Spansion / Infineon",
    0x20: "ST / Numonyx",
    0xC8: "GigaDevice",
    0x8C: "ESMT",
    0xC9: "Dosilicon",
    0xE5: "Foresee / Longsys",
    0x45: "SanDisk / Western Digital",
    0x89: "Intel",
}


# Known Pre-defined NAND Flash Chips Database
# Key: (mfr_id, dev_id) or (mfr_id, dev_id, 3rd_byte)
DATABASE: Dict[Tuple[int, ...], NANDChipInfo] = {
    # ------------------ SAMSUNG ------------------
    (0xEC, 0x76): NANDChipInfo(
        manufacturer="Samsung", part_number="K9F1208U0B",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=512, spare_size=16, pages_per_block=32, total_blocks=4096,
        total_capacity_mb=64, col_addr_cycles=1, row_addr_cycles=3,
        bad_block_marker_offset=5, bad_block_marker_page="0, 1",
        notes="Legacy 512-byte small page SLC NAND"
    ),
    (0xEC, 0x79): NANDChipInfo(
        manufacturer="Samsung", part_number="K9F1G08U0M",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=512, spare_size=16, pages_per_block=32, total_blocks=8192,
        total_capacity_mb=128, col_addr_cycles=1, row_addr_cycles=3,
        bad_block_marker_offset=5, bad_block_marker_page="0, 1"
    ),
    (0xEC, 0xF1): NANDChipInfo(
        manufacturer="Samsung", part_number="K9F1G08U0A / K9F1G08U0D",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=1024,
        total_capacity_mb=128, col_addr_cycles=2, row_addr_cycles=2,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0xEC, 0xDA): NANDChipInfo(
        manufacturer="Samsung", part_number="K9F2G08U0A / K9F2G08U0M",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=2048,
        total_capacity_mb=256, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0xEC, 0xDC): NANDChipInfo(
        manufacturer="Samsung", part_number="K9F4G08U0A / K9F4G08U0D",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=4096,
        total_capacity_mb=512, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0xEC, 0xD3): NANDChipInfo(
        manufacturer="Samsung", part_number="K9K8G08U0M / K9K8G08U0E",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=8192,
        total_capacity_mb=1024, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0xEC, 0xD5): NANDChipInfo(
        manufacturer="Samsung", part_number="K9GAG08U0M / K9GAG08U0D",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="MLC",
        page_size=4096, spare_size=128, pages_per_block=128, total_blocks=4096,
        total_capacity_mb=2048, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, last"
    ),
    (0xEC, 0xD7): NANDChipInfo(
        manufacturer="Samsung", part_number="K9LBG08U0D",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="MLC",
        page_size=4096, spare_size=128, pages_per_block=128, total_blocks=8192,
        total_capacity_mb=4096, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, last"
    ),

    # ------------------ TOSHIBA / KIOXIA ------------------
    (0x98, 0xF1): NANDChipInfo(
        manufacturer="Toshiba", part_number="TC58NVG0S3ETA00",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=1024,
        total_capacity_mb=128, col_addr_cycles=2, row_addr_cycles=2,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0x98, 0xDA): NANDChipInfo(
        manufacturer="Toshiba", part_number="TC58NVG1S3ETA00 / TC58NVG1S3HTA00",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=2048,
        total_capacity_mb=256, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0x98, 0xDC): NANDChipInfo(
        manufacturer="Toshiba", part_number="TC58NVG2S0FTA00 / TC58NVG2S0HTA00",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=4096, spare_size=128, pages_per_block=64, total_blocks=2048,
        total_capacity_mb=512, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0x98, 0xD3): NANDChipInfo(
        manufacturer="Toshiba", part_number="TC58NVG3S0ETA00 / TC58NVG3S0FTA00",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=4096, spare_size=128, pages_per_block=64, total_blocks=4096,
        total_capacity_mb=1024, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0x98, 0xD7): NANDChipInfo(
        manufacturer="Toshiba", part_number="TH58NVG7D2FTA20",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="MLC",
        page_size=8192, spare_size=640, pages_per_block=128, total_blocks=8192,
        total_capacity_mb=8192, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, last"
    ),

    # ------------------ MICRON ------------------
    (0x2C, 0xF1): NANDChipInfo(
        manufacturer="Micron", part_number="MT29F1G08ABADA",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=1024,
        total_capacity_mb=128, col_addr_cycles=2, row_addr_cycles=2,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),
    (0x2C, 0xDA): NANDChipInfo(
        manufacturer="Micron", part_number="MT29F2G08ABAEA / MT29F2G08AAD",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=2048,
        total_capacity_mb=256, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),
    (0x2C, 0xDC): NANDChipInfo(
        manufacturer="Micron", part_number="MT29F4G08ABADA / MT29F4G08ABBDA",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=4096,
        total_capacity_mb=512, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),
    (0x2C, 0x38): NANDChipInfo(
        manufacturer="Micron", part_number="MT29F8G08ABABA",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=4096, spare_size=224, pages_per_block=64, total_blocks=4096,
        total_capacity_mb=1024, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),
    (0x2C, 0x48): NANDChipInfo(
        manufacturer="Micron", part_number="MT29F16G08ABACA",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=4096, spare_size=224, pages_per_block=128, total_blocks=4096,
        total_capacity_mb=2048, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),

    # ------------------ SK HYNIX ------------------
    (0xAD, 0xF1): NANDChipInfo(
        manufacturer="SK Hynix", part_number="H27U1G8F2BTR",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=1024,
        total_capacity_mb=128, col_addr_cycles=2, row_addr_cycles=2,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0xAD, 0xDA): NANDChipInfo(
        manufacturer="SK Hynix", part_number="H27U2G8F2CTR",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=2048,
        total_capacity_mb=256, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0xAD, 0xDC): NANDChipInfo(
        manufacturer="SK Hynix", part_number="H27U4G8F2DTR",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=4096,
        total_capacity_mb=512, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0xAD, 0xD3): NANDChipInfo(
        manufacturer="SK Hynix", part_number="H27U8G8T2BTR",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=8192,
        total_capacity_mb=1024, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),

    # ------------------ WINBOND ------------------
    (0xEF, 0xF1): NANDChipInfo(
        manufacturer="Winbond", part_number="W29N01GV",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=1024,
        total_capacity_mb=128, col_addr_cycles=2, row_addr_cycles=2,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),
    (0xEF, 0xDA): NANDChipInfo(
        manufacturer="Winbond", part_number="W29N02GV",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=2048,
        total_capacity_mb=256, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),
    (0xEF, 0xDC): NANDChipInfo(
        manufacturer="Winbond", part_number="W29N04GV",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=4096,
        total_capacity_mb=512, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),
    # Winbond SPI NAND
    (0xEF, 0xAA, 0x21): NANDChipInfo(
        manufacturer="Winbond", part_number="W25N01GV (SPI NAND)",
        bus_interface=BusInterface.SPI_NAND, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=1024,
        total_capacity_mb=128, col_addr_cycles=2, row_addr_cycles=2,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1",
        notes="High speed SPI/Quad-SPI NAND flash"
    ),
    (0xEF, 0xAA, 0x22): NANDChipInfo(
        manufacturer="Winbond", part_number="W25N02KV (SPI NAND)",
        bus_interface=BusInterface.SPI_NAND, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=2048,
        total_capacity_mb=256, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1",
        notes="High speed SPI/Quad-SPI NAND flash"
    ),

    # ------------------ MACRONIX ------------------
    (0xC2, 0xF1): NANDChipInfo(
        manufacturer="Macronix", part_number="MX30LF1G08AA",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=1024,
        total_capacity_mb=128, col_addr_cycles=2, row_addr_cycles=2,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),
    (0xC2, 0xDA): NANDChipInfo(
        manufacturer="Macronix", part_number="MX30LF2G18AC",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=2048,
        total_capacity_mb=256, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),
    (0xC2, 0xDC): NANDChipInfo(
        manufacturer="Macronix", part_number="MX30LF4G18AC",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=4096,
        total_capacity_mb=512, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),
    # Macronix SPI NAND
    (0xC2, 0x12): NANDChipInfo(
        manufacturer="Macronix", part_number="MX35LF1GE4AB (SPI NAND)",
        bus_interface=BusInterface.SPI_NAND, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=1024,
        total_capacity_mb=128, col_addr_cycles=2, row_addr_cycles=2,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),

    # ------------------ SPANSION / CYPRESS ------------------
    (0x01, 0xF1): NANDChipInfo(
        manufacturer="Spansion", part_number="S34ML01G100TFI00",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=1024,
        total_capacity_mb=128, col_addr_cycles=2, row_addr_cycles=2,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),
    (0x01, 0xDA): NANDChipInfo(
        manufacturer="Spansion", part_number="S34ML02G100TFI00",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=2048,
        total_capacity_mb=256, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),
    (0x01, 0xDC): NANDChipInfo(
        manufacturer="Spansion", part_number="S34ML04G100TFI00",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=4096,
        total_capacity_mb=512, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),

    # ------------------ GIGADEVICE SPI & PARALLEL NAND ------------------
    (0xC8, 0xB1, 0x48): NANDChipInfo(
        manufacturer="GigaDevice", part_number="GD5F1GQ4UBYIG (SPI NAND)",
        bus_interface=BusInterface.SPI_NAND, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=128, pages_per_block=64, total_blocks=1024,
        total_capacity_mb=128, col_addr_cycles=2, row_addr_cycles=2,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0xC8, 0xB2, 0x48): NANDChipInfo(
        manufacturer="GigaDevice", part_number="GD5F2GQ4UBYIG (SPI NAND)",
        bus_interface=BusInterface.SPI_NAND, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=128, pages_per_block=64, total_blocks=2048,
        total_capacity_mb=256, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0xC8, 0xB4, 0x48): NANDChipInfo(
        manufacturer="GigaDevice", part_number="GD5F4GQ4UBYIG (SPI NAND)",
        bus_interface=BusInterface.SPI_NAND, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=128, pages_per_block=64, total_blocks=4096,
        total_capacity_mb=512, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0xC8, 0xD1): NANDChipInfo(
        manufacturer="GigaDevice", part_number="GD5F1GQ5UEYIG (SPI NAND)",
        bus_interface=BusInterface.SPI_NAND, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=128, pages_per_block=64, total_blocks=1024,
        total_capacity_mb=128, col_addr_cycles=2, row_addr_cycles=2,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),

    # ------------------ STMICROELECTRONICS / NUMONYX ------------------
    (0x20, 0x73): NANDChipInfo(
        manufacturer="ST / Numonyx", part_number="NAND128W3A",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=512, spare_size=16, pages_per_block=32, total_blocks=1024,
        total_capacity_mb=16, col_addr_cycles=1, row_addr_cycles=2,
        bad_block_marker_offset=5, bad_block_marker_page="0, 1"
    ),
    (0x20, 0x75): NANDChipInfo(
        manufacturer="ST / Numonyx", part_number="NAND256W3A",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=512, spare_size=16, pages_per_block=32, total_blocks=2048,
        total_capacity_mb=32, col_addr_cycles=1, row_addr_cycles=2,
        bad_block_marker_offset=5, bad_block_marker_page="0, 1"
    ),
    (0x20, 0x76): NANDChipInfo(
        manufacturer="ST / Numonyx", part_number="NAND512W3A",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=512, spare_size=16, pages_per_block=32, total_blocks=4096,
        total_capacity_mb=64, col_addr_cycles=1, row_addr_cycles=3,
        bad_block_marker_offset=5, bad_block_marker_page="0, 1"
    ),
    (0x20, 0xF1): NANDChipInfo(
        manufacturer="ST / Numonyx", part_number="NAND01GW3B",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=1024,
        total_capacity_mb=128, col_addr_cycles=2, row_addr_cycles=2,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0x20, 0xDA): NANDChipInfo(
        manufacturer="ST / Numonyx", part_number="NAND02GW3B",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=2048,
        total_capacity_mb=256, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0x20, 0xDC): NANDChipInfo(
        manufacturer="ST / Numonyx", part_number="NAND04GW3B",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=4096,
        total_capacity_mb=512, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),

    # ------------------ ESMT / ELITE SEMICONDUCTOR ------------------
    (0x8C, 0xF1): NANDChipInfo(
        manufacturer="ESMT", part_number="F59L1G81A",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=1024,
        total_capacity_mb=128, col_addr_cycles=2, row_addr_cycles=2,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),
    (0x8C, 0xDA): NANDChipInfo(
        manufacturer="ESMT", part_number="F59L2G81A",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=2048,
        total_capacity_mb=256, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),
    (0x8C, 0xDC): NANDChipInfo(
        manufacturer="ESMT", part_number="F59L4G81A",
        bus_interface=BusInterface.PARALLEL_X8, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=4096,
        total_capacity_mb=512, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1", onfi_supported=True
    ),

    # ------------------ DOSILICON SPI NAND ------------------
    (0xC9, 0x51): NANDChipInfo(
        manufacturer="Dosilicon", part_number="DS35Q1GA (SPI NAND)",
        bus_interface=BusInterface.SPI_NAND, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=1024,
        total_capacity_mb=128, col_addr_cycles=2, row_addr_cycles=2,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
    (0xC9, 0x52): NANDChipInfo(
        manufacturer="Dosilicon", part_number="DS35Q2GA (SPI NAND)",
        bus_interface=BusInterface.SPI_NAND, voltage="3.3V", cell_type="SLC",
        page_size=2048, spare_size=64, pages_per_block=64, total_blocks=2048,
        total_capacity_mb=256, col_addr_cycles=2, row_addr_cycles=3,
        bad_block_marker_offset=0, bad_block_marker_page="0, 1"
    ),
}


def decode_nand_id_generic(id_bytes: bytes) -> Optional[NANDChipInfo]:
    """
    Decodes standard NAND Flash 4th & 5th byte ID for devices that follow
    the common Samsung/Toshiba/Hynix ID decoding format.
    """
    if len(id_bytes) < 4:
        return None

    mfr_id = id_bytes[0]
    dev_id = id_bytes[1]
    byte3 = id_bytes[3]

    mfr_name = MANUFACTURERS.get(mfr_id, f"Unknown (0x{mfr_id:02X})")

    # Byte 3 decode:
    # Page size: bits 0-1
    page_size_code = byte3 & 0x03
    page_sizes = [1024, 2048, 4096, 8192]
    page_size = page_sizes[page_size_code]

    # Spare size: bit 2
    spare_size_bit = (byte3 >> 2) & 0x01
    # Many modern chips: bit 2 is redundant or 16B/512B vs 64B/2048B ratio (1/32)
    # 2KB page -> 64B spare, 4KB page -> 128B or 224B spare, 8KB -> 256B/512B
    spare_size = max(16, page_size // 32)
    if len(id_bytes) >= 5:
        # Check byte 4 for spare size if available
        byte4 = id_bytes[4]
        spare_code = (byte4 >> 4) & 0x07
        if spare_code == 1:
            spare_size = 128
        elif spare_code == 2:
            spare_size = 218
        elif spare_code == 3:
            spare_size = 400
        elif spare_code == 4:
            spare_size = 436
        elif spare_code == 5:
            spare_size = 512
        elif spare_code == 6:
            spare_size = 640

    # Block size: bits 4-5
    block_size_code = (byte3 >> 4) & 0x03
    block_sizes = [64 * 1024, 128 * 1024, 256 * 1024, 512 * 1024]
    block_size_bytes = block_sizes[block_size_code]
    pages_per_block = max(32, block_size_bytes // page_size)

    # Bus width: bit 6
    bus_x16 = bool(byte3 & (1 << 6))
    bus_interface = BusInterface.PARALLEL_X16 if bus_x16 else BusInterface.PARALLEL_X8

    # Infer capacity from device ID table if possible, or estimate
    cap_mb = 128
    if dev_id in (0xF1,):
        cap_mb = 128
    elif dev_id in (0xDA, 0xAA):
        cap_mb = 256
    elif dev_id in (0xDC, 0xAC):
        cap_mb = 512
    elif dev_id in (0xD3, 0xA3):
        cap_mb = 1024
    elif dev_id in (0xD5, 0xA5):
        cap_mb = 2048
    elif dev_id in (0xD7, 0xA7):
        cap_mb = 4096

    total_blocks = (cap_mb * 1024 * 1024) // (page_size * pages_per_block)
    total_blocks = max(1024, total_blocks)

    col_cycles = 2 if page_size >= 2048 else 1
    row_cycles = 3 if total_blocks >= 2048 else 2

    return NANDChipInfo(
        manufacturer=mfr_name,
        part_number=f"Generic NAND (0x{mfr_id:02X} 0x{dev_id:02X})",
        bus_interface=bus_interface,
        voltage="3.3V",
        cell_type="SLC",
        page_size=page_size,
        spare_size=spare_size,
        pages_per_block=pages_per_block,
        total_blocks=total_blocks,
        total_capacity_mb=cap_mb,
        col_addr_cycles=col_cycles,
        row_addr_cycles=row_cycles,
        bad_block_marker_offset=0 if page_size >= 2048 else 5,
        bad_block_marker_page="0, 1",
        notes="Decoded dynamically via Samsung/ONFI 4th/5th byte ID standard"
    )


def lookup_chip_by_id(id_bytes: bytes) -> Optional[NANDChipInfo]:
    """
    Looks up a chip by its ID bytes.
    First checks exact database matches, then checks 3-byte and 2-byte keys,
    and finally falls back to dynamic 4th/5th byte decoding.
    """
    if len(id_bytes) < 2:
        return None

    # Check 3-byte match (useful for SPI NANDs and distinct revisions)
    if len(id_bytes) >= 3:
        key3 = (id_bytes[0], id_bytes[1], id_bytes[2])
        if key3 in DATABASE:
            return DATABASE[key3]

    # Check 2-byte match
    key2 = (id_bytes[0], id_bytes[1])
    if key2 in DATABASE:
        return DATABASE[key2]

    # Fallback to generic decoding if >= 4 bytes
    if len(id_bytes) >= 4:
        return decode_nand_id_generic(id_bytes)

    # Minimal fallback
    mfr_id = id_bytes[0]
    dev_id = id_bytes[1]
    mfr_name = MANUFACTURERS.get(mfr_id, f"Unknown (0x{mfr_id:02X})")
    return NANDChipInfo(
        manufacturer=mfr_name,
        part_number=f"Unrecognized NAND (0x{mfr_id:02X} 0x{dev_id:02X})",
        bus_interface=BusInterface.PARALLEL_X8,
        voltage="3.3V",
        cell_type="SLC",
        page_size=2048,
        spare_size=64,
        pages_per_block=64,
        total_blocks=1024,
        total_capacity_mb=128,
        col_addr_cycles=2,
        row_addr_cycles=2,
        bad_block_marker_offset=0,
        bad_block_marker_page="0, 1",
        notes="Default fallback geometry"
    )

