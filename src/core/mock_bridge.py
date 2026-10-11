"""
Universal NAND Flash Clone Tool - Virtual / Mock Hardware Bridge
Full emulation of Teensy 4.1 hardware bridge connected to an ONFI NAND Flash chip.
Enables offline UI testing, software validation, and hardware-free simulation.
"""

import time
import struct
from typing import Dict, Any, List
from .bridge_interface import BridgeInterface
from .protocol import BusType
from .onfi_parser import onfi_crc16


class MockTeensyBridge(BridgeInterface):
    """
    Virtual Teensy 4.1 hardware bridge with virtual NAND chip memory.
    """

    def __init__(self, simulate_chip: str = "Micron MT29F4G08"):
        self._connected: bool = False
        self.port_name: str = "COM_MOCK (Teensy 4.1 Virtual)"
        self.simulate_chip_name = simulate_chip

        # Virtual NAND geometry (4Gb = 512MB SLC NAND, 2048+64 page, 64 pages/block, 4096 blocks)
        self.page_size = 2048
        self.spare_size = 64
        self.full_page_size = self.page_size + self.spare_size
        self.pages_per_block = 64
        self.total_blocks = 4096
        self.total_pages = self.total_blocks * self.pages_per_block

        # Factory bad blocks
        self.bad_blocks = {7, 42, 115, 230, 399}

        # Sparse memory dictionary: page_addr -> bytes (full_page_size)
        self._memory: Dict[int, bytearray] = {}

        # Prepopulate virtual flash with realistic embedded firmware structures
        self._init_mock_flash_content()

    def _init_mock_flash_content(self):
        """Populates virtual NAND memory with realistic bootloader, kernel, UBI, and SquashFS."""
        # 1. Block 0: U-Boot bootloader
        uboot_header = bytearray(self.page_size)
        # uImage header: magic(0x27051956), hcrc, time, size, load, ep, dcrc, os, arch, type, comp, name
        struct.pack_into(">IIIIIII4B32s", uboot_header, 0,
                         0x27051956, 0x11223344, int(time.time()), 262144,
                         0x80008000, 0x80008000, 0x55667788,
                         5, 2, 2, 0, b"U-Boot 2024.10 NAND Bootloader")
        uboot_oob = bytearray([0xFF] * self.spare_size)
        self._memory[0] = uboot_header + uboot_oob

        # Some pages with U-Boot string data
        for p in range(1, 10):
            page_content = b"U-Boot SPL 2024.10 (ARMv7-A Cortex-A7) Boot sequence initialization...\n" * 30
            pdata = bytearray(page_content[: self.page_size].ljust(self.page_size, b"\xFF"))
            self._memory[p] = pdata + bytearray([0xFF] * self.spare_size)

        # 2. Block 4: Device Tree / FIT image (magic 0xD00DFEED)
        fdt_header = bytearray(self.page_size)
        struct.pack_into(">IIII", fdt_header, 0, 0xD00DFEED, 65536, 0x48, 0x28)
        self._memory[4 * self.pages_per_block] = fdt_header + bytearray([0xFF] * self.spare_size)

        # 3. Block 8: Linux ARM zImage kernel (magic 0x016F2818 at 0x24)
        zimg_header = bytearray(self.page_size)
        struct.pack_into("<II", zimg_header, 0x24, 0x016F2818, 0)
        struct.pack_into("<II", zimg_header, 0x28, 0, 0x00400000)  # 4MB image
        self._memory[8 * self.pages_per_block] = zimg_header + bytearray([0xFF] * self.spare_size)

        # 4. Block 16: SquashFS Root Filesystem (magic 'hsqs' or 'sqsh')
        sqsh_header = bytearray(self.page_size)
        sqsh_header[0:4] = b"sqsh"
        # Inodes: 1200, bytes_used: 10485760 (10MB), major: 4, minor: 0
        struct.pack_into("<II", sqsh_header, 4, 1200, int(time.time()))
        struct.pack_into("<HH", sqsh_header, 28, 4, 0)
        struct.pack_into("<Q", sqsh_header, 40, 10485760)
        self._memory[16 * self.pages_per_block] = sqsh_header + bytearray([0xFF] * self.spare_size)

        # 5. Block 32..64: UBI Volume (magic 'UBI#')
        for blk in range(32, 64):
            ubi_page = bytearray(self.page_size)
            ubi_page[0:4] = b"UBI#"
            # EC header version 1, EC count = 12
            struct.pack_into(">B", ubi_page, 4, 1)
            struct.pack_into(">Q", ubi_page, 8, 12)  # EC count
            struct.pack_into(">I", ubi_page, 16, 2048)  # VID hdr offset
            struct.pack_into(">I", ubi_page, 20, 4096)  # Data offset
            self._memory[blk * self.pages_per_block] = ubi_page + bytearray([0xFF] * self.spare_size)

        # 6. Set Factory Bad Block markers: Byte 0 of spare area in page 0 = 0x00 (not 0xFF)
        for bb in self.bad_blocks:
            bad_page_idx = bb * self.pages_per_block
            bad_data = bytearray([0xFF] * self.page_size)
            bad_oob = bytearray([0x00] + [0xFF] * (self.spare_size - 1))
            self._memory[bad_page_idx] = bad_data + bad_oob

        # 7. Inject a 1-bit flip in Block 20, Page 0, Byte 10 for ECC demonstration
        ecc_page_idx = 20 * self.pages_per_block
        ecc_data = bytearray(b"\x55\xAA\x12\x34\xFE\xDC\xBA\x98" * 256)
        # Flip 1 bit at byte 10
        ecc_data[10] ^= 0x04
        self._memory[ecc_page_idx] = ecc_data + bytearray([0xFF] * self.spare_size)

    def connect(self, port: str = "COM_MOCK", baudrate: int = 12000000) -> bool:
        time.sleep(0.05)
        self._connected = True
        self.port_name = port
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def ping(self) -> bool:
        return self._connected

    def get_firmware_info(self) -> Dict[str, Any]:
        return {
            "connected": True,
            "version": "1.4.0-SIM",
            "mcu_freq_mhz": 600,
            "capabilities": 0x003F,
            "board": "Teensy 4.1 (Simulated High-Speed Bridge)",
        }

    def set_bus_config(self, bus_type: BusType, timing_mode: int = 0, ce_idx: int = 0, vcc_en: bool = True) -> bool:
        return True

    def reset_chip(self) -> bool:
        return True

    def read_chip_id(self) -> bytes:
        # Micron MT29F4G08: MFR=0x2C, DEV=0xDC, 3rd=0x90, 4th=0x95, 5th=0x56
        return bytes([0x2C, 0xDC, 0x90, 0x95, 0x56])

    def read_onfi_parameter_page(self) -> bytes:
        """Generates realistic ONFI 256-byte parameter page with valid CRC."""
        data = bytearray(768)  # 3 copies of 256 bytes

        for copy_idx in range(3):
            base = copy_idx * 256
            data[base : base + 4] = b"ONFI"
            struct.pack_into("<H", data, base + 4, 0x001E)  # Revision bitmask (1.0, 2.0, 2.1, 2.2)
            struct.pack_into("<H", data, base + 6, 0x000F)  # Features
            struct.pack_into("<H", data, base + 8, 0x003F)  # Optional commands

            # Manufacturer (12 bytes) and Model (20 bytes)
            mfr_str = b"MICRON      "
            model_str = b"MT29F4G08ABADA      "
            data[base + 32 : base + 44] = mfr_str[:12]
            data[base + 44 : base + 64] = model_str[:20]
            data[base + 64] = 0x2C  # JEDEC ID

            # Page size = 2048, Spare = 64
            struct.pack_into("<I", data, base + 80, self.page_size)
            struct.pack_into("<H", data, base + 84, self.spare_size)
            # Pages per block = 64
            struct.pack_into("<I", data, base + 92, self.pages_per_block)
            # Blocks per LUN = 4096, LUN count = 1
            struct.pack_into("<I", data, base + 96, 4096)
            data[base + 100] = 1  # LUNs
            data[base + 101] = (2 << 4) | 3  # 2 Col cycles, 3 Row cycles
            data[base + 102] = 1  # SLC (1 bit/cell)
            struct.pack_into("<H", data, base + 103, 80)  # Max bad blocks per LUN
            struct.pack_into("<H", data, base + 105, 50000)  # Endurance (50k P/E cycles)
            data[base + 112] = 4  # 4 bits ECC required
            struct.pack_into("<H", data, base + 129, 0x003F)  # Timing modes 0..5
            struct.pack_into("<H", data, base + 133, 300)  # max tPROG 300us
            struct.pack_into("<H", data, base + 135, 2000) # max tBERS 2000us
            struct.pack_into("<H", data, base + 137, 25)   # max tR 25us

            # Compute and store ONFI CRC16
            crc = onfi_crc16(bytes(data[base : base + 254]))
            struct.pack_into("<H", data, base + 254, crc)

        return bytes(data)

    def read_status(self) -> int:
        return 0xE0  # Ready (bit 6 = 1), Write Protect high (bit 7 = 1), Pass (bit 0 = 0)

    def read_page(
        self,
        page_addr: int,
        col_addr: int = 0,
        length: int = 2112,
        col_cycles: int = 2,
        row_cycles: int = 3,
    ) -> bytes:
        # Slight simulated read delay for realistic feel (0.2 ms per page = ~10 MB/s)
        time.sleep(0.00015)

        if page_addr < 0 or page_addr >= self.total_pages:
            return b""
        if col_addr < 0 or length < 0 or col_addr + length > self.full_page_size:
            return b""

        if page_addr in self._memory:
            full_data = bytes(self._memory[page_addr])
        else:
            # Default unprogrammed erased state (all 0xFF)
            full_data = bytes([0xFF] * self.full_page_size)

        # Slice column and length
        if col_addr < len(full_data):
            return full_data[col_addr : col_addr + length]
        return bytes([0xFF] * length)

    def write_page(
        self,
        page_addr: int,
        col_addr: int = 0,
        data: bytes = b"",
        col_cycles: int = 2,
        row_cycles: int = 3,
    ) -> bool:
        time.sleep(0.0003)
        if (
            page_addr < 0
            or page_addr >= self.total_pages
            or col_addr < 0
            or col_addr + len(data) > self.full_page_size
        ):
            return False
        if page_addr not in self._memory:
            self._memory[page_addr] = bytearray([0xFF] * self.full_page_size)

        buf = self._memory[page_addr]
        end_idx = min(len(buf), col_addr + len(data))
        buf[col_addr:end_idx] = data[: end_idx - col_addr]
        return True

    def erase_block(
        self,
        block_addr: int,
        pages_per_block: int = 64,
        row_cycles: int = 3,
    ) -> bool:
        time.sleep(0.002)
        if (
            block_addr < 0
            or pages_per_block <= 0
            or (block_addr + 1) * pages_per_block > self.total_pages
        ):
            return False
        start_page = block_addr * pages_per_block
        for p in range(start_page, start_page + pages_per_block):
            if p in self._memory:
                del self._memory[p]
        return True

    def scan_bad_blocks(
        self,
        total_blocks: int,
        pages_per_block: int = 64,
        oob_offset: int = 0,
        col_cycles: int = 2,
        row_cycles: int = 3,
    ) -> List[int]:
        time.sleep(0.05)
        return sorted(block for block in self.bad_blocks if block < total_blocks)

    def probe_pins(self) -> Dict[str, Any]:
        return {
            "RB": True,    # Ready
            "CE": False,   # Active low asserted
            "CLE": False,
            "ALE": False,
            "WP": True,
            "VCC": 3.3,
        }

    def power_control(self, power_on: bool) -> bool:
        return True
