"""
Universal NAND Flash Clone Tool - High-Level NAND Operations Engine
Orchestrates Auto-detection, Dumping (Chip to File), Flashing (File to Chip),
Cloning, Verifying, Erasing, and Bad Block Scanning with real-time telemetry.
"""

import os
import time
import hashlib
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Callable, Any, Tuple

from .bridge_interface import BridgeInterface
from .onfi_parser import parse_onfi_parameter_page, ONFIParameterPage
from .chip_database import lookup_chip_by_id, NANDChipInfo, BusInterface
from .ecc_engine import verify_and_correct_ecc_256, count_bitflips, ECCStatus
from .protocol import BusType

logger = logging.getLogger("NANDEngine")


class BlockState(Enum):
    UNKNOWN = "unknown"
    GOOD = "good"
    BAD = "bad"
    READ_OK = "read_ok"
    BITFLIP_CORRECTED = "bitflip"
    PROGRAMMED = "programmed"
    ERASED = "erased"
    VERIFIED = "verified"
    MISMATCH = "mismatch"


@dataclass
class ProgressUpdate:
    operation: str
    current_block: int
    total_blocks: int
    current_page: int
    total_pages: int
    bytes_processed: int
    total_bytes: int
    percent: float
    current_speed_mbps: float
    avg_speed_mbps: float
    elapsed_sec: float
    eta_sec: float
    status_message: str
    block_state_change: Optional[Tuple[int, BlockState]] = None


@dataclass
class ActiveChipConfig:
    manufacturer: str
    model: str
    chip_info: Optional[NANDChipInfo] = None
    onfi_params: Optional[ONFIParameterPage] = None
    page_size: int = 2048
    spare_size: int = 64
    pages_per_block: int = 64
    total_blocks: int = 1024
    total_capacity_bytes: int = 134217728
    col_addr_cycles: int = 2
    row_addr_cycles: int = 3
    is_onfi: bool = False
    bus_interface: str = "Parallel x8"

    @property
    def full_page_size(self) -> int:
        return self.page_size + self.spare_size

    @property
    def block_size(self) -> int:
        return self.page_size * self.pages_per_block

    @property
    def total_capacity_mb(self) -> float:
        return self.total_capacity_bytes / (1024 * 1024)


class NANDEngine:
    """Core NAND Engine executing operations across the bridge."""

    def __init__(self, bridge: BridgeInterface):
        self.bridge = bridge
        self.active_chip: Optional[ActiveChipConfig] = None
        self.bad_block_table: Dict[int, BlockState] = {}
        self.abort_requested: bool = False

    def abort(self) -> None:
        """Requests cancellation of ongoing operation."""
        self.abort_requested = True
        logger.info("Abort requested by user.")

    def auto_detect_chip(self) -> Optional[ActiveChipConfig]:
        """
        Attempts ONFI detection first, then falls back to JEDEC/Database lookup.
        """
        if not self.bridge.is_connected():
            logger.error("Bridge is not connected.")
            return None

        # Reset chip
        self.bridge.reset_chip()
        time.sleep(0.01)

        # 1. Try ONFI Parameter Page Read (Command 0xEC)
        onfi_raw = self.bridge.read_onfi_parameter_page()
        onfi_page = parse_onfi_parameter_page(onfi_raw) if onfi_raw else None

        if onfi_page and onfi_page.is_valid:
            if not self.bridge.set_bus_config(BusType.PARALLEL_X8):
                raise RuntimeError("Failed to configure bridge for parallel NAND.")
            logger.info(f"Detected ONFI NAND: {onfi_page.manufacturer} {onfi_page.model}")
            chip_cfg = ActiveChipConfig(
                manufacturer=onfi_page.manufacturer,
                model=onfi_page.model,
                onfi_params=onfi_page,
                page_size=onfi_page.page_size,
                spare_size=onfi_page.spare_size,
                pages_per_block=onfi_page.pages_per_block,
                total_blocks=onfi_page.total_blocks,
                total_capacity_bytes=onfi_page.total_capacity_bytes,
                col_addr_cycles=onfi_page.col_addr_cycles,
                row_addr_cycles=onfi_page.row_addr_cycles,
                is_onfi=True,
                bus_interface="Parallel x8",
            )
            self.active_chip = chip_cfg
            self._init_block_table(chip_cfg.total_blocks)
            return chip_cfg

        # Try the parallel ID before switching the bridge to SPI mode.
        id_bytes = self.bridge.read_chip_id()
        chip_info = lookup_chip_by_id(id_bytes) if self._valid_chip_id(id_bytes) else None
        if chip_info and self._is_verified_chip_info(chip_info) and chip_info.bus_interface == BusInterface.PARALLEL_X8:
            return self._activate_chip(chip_info)
        if chip_info and chip_info.bus_interface == BusInterface.PARALLEL_X16:
            logger.error("Parallel x16 NAND is not supported by this bridge.")
            return None

        # SPI NAND does not expose the parallel ONFI parameter-page command.
        if not self.bridge.set_bus_config(BusType.SPI_STANDARD):
            logger.error("Could not configure the bridge for SPI NAND detection.")
            return None
        self.bridge.reset_chip()
        spi_id = self.bridge.read_chip_id()
        spi_info = lookup_chip_by_id(spi_id) if self._valid_chip_id(spi_id) else None
        if (
            spi_info
            and self._is_verified_chip_info(spi_info)
            and spi_info.bus_interface == BusInterface.SPI_NAND
        ):
            return self._activate_chip(spi_info)

        # Do not guess geometry: a false geometry makes destructive writes unsafe.
        self.bridge.set_bus_config(BusType.PARALLEL_X8)
        logger.warning("NAND geometry could not be identified; refusing to use guessed geometry.")
        self.active_chip = None
        self.bad_block_table.clear()
        return None

    @staticmethod
    def _valid_chip_id(chip_id: bytes) -> bool:
        return len(chip_id) >= 2 and chip_id[:2] not in (b"\x00\x00", b"\xFF\xFF")

    @staticmethod
    def _is_verified_chip_info(chip_info: NANDChipInfo) -> bool:
        return not chip_info.part_number.startswith(("Generic NAND", "Unrecognized NAND"))

    def _activate_chip(self, chip_info: NANDChipInfo) -> ActiveChipConfig:
        bus_type = (
            BusType.SPI_STANDARD
            if chip_info.bus_interface == BusInterface.SPI_NAND
            else BusType.PARALLEL_X8
        )
        if not self.bridge.set_bus_config(bus_type):
            raise RuntimeError(f"Failed to configure bridge for {chip_info.bus_interface.value}.")

        logger.info(f"Identified NAND from Database: {chip_info.manufacturer} {chip_info.part_number}")
        chip_cfg = ActiveChipConfig(
            manufacturer=chip_info.manufacturer,
            model=chip_info.part_number,
            chip_info=chip_info,
            page_size=chip_info.page_size,
            spare_size=chip_info.spare_size,
            pages_per_block=chip_info.pages_per_block,
            total_blocks=chip_info.total_blocks,
            total_capacity_bytes=chip_info.total_capacity_bytes,
            col_addr_cycles=chip_info.col_addr_cycles,
            row_addr_cycles=chip_info.row_addr_cycles,
            is_onfi=False,
            bus_interface=chip_info.bus_interface.value,
        )
        self.active_chip = chip_cfg
        self._init_block_table(chip_cfg.total_blocks)
        return chip_cfg

    def _init_block_table(self, count: int) -> None:
        self.bad_block_table = {b: BlockState.UNKNOWN for b in range(count)}

    def scan_bad_blocks(
        self,
        progress_cb: Optional[Callable[[ProgressUpdate], None]] = None
    ) -> List[int]:
        """
        Scans flash memory for factory bad block markers.
        Checks byte 0 (or 5 for small page) in spare area of page 0 and 1 of each block.
        """
        if not self.active_chip:
            raise RuntimeError("No active chip detected or configured.")

        self.abort_requested = False
        cfg = self.active_chip
        bad_blocks: List[int] = []

        marker_offset = cfg.chip_info.bad_block_marker_offset if cfg.chip_info else (0 if cfg.page_size >= 2048 else 5)
        check_col = cfg.page_size + marker_offset
        marker_pages = [0, min(1, cfg.pages_per_block - 1)]
        if cfg.chip_info:
            marker_pages = [
                cfg.pages_per_block - 1 if marker.strip().lower() == "last" else int(marker.strip())
                for marker in cfg.chip_info.bad_block_marker_page.split(",")
            ]
        marker_pages = list(dict.fromkeys(marker_pages))
        if any(page < 0 or page >= cfg.pages_per_block for page in marker_pages):
            raise ValueError("Chip database contains an invalid bad-block marker page.")

        start_time = time.time()
        for blk in range(cfg.total_blocks):
            if self.abort_requested:
                break

            is_bad = False
            for marker_page in marker_pages:
                page_addr = blk * cfg.pages_per_block + marker_page
                marker_byte = self.bridge.read_page(
                    page_addr,
                    col_addr=check_col,
                    length=1,
                    col_cycles=cfg.chip_info.col_addr_cycles if cfg.chip_info else cfg.col_addr_cycles,
                    row_cycles=cfg.row_addr_cycles,
                )
                if len(marker_byte) != 1:
                    raise RuntimeError(f"Failed to read bad-block marker for block {blk}.")
                if marker_byte[0] != 0xFF:
                    is_bad = True
                    break

            state = BlockState.BAD if is_bad else BlockState.GOOD
            self.bad_block_table[blk] = state
            if is_bad:
                bad_blocks.append(blk)

            if progress_cb and (is_bad or blk % 16 == 0 or blk == cfg.total_blocks - 1):
                elapsed = max(0.001, time.time() - start_time)
                progress_cb(ProgressUpdate(
                    operation="Scan Bad Blocks",
                    current_block=blk + 1,
                    total_blocks=cfg.total_blocks,
                    current_page=(blk + 1) * cfg.pages_per_block,
                    total_pages=cfg.total_blocks * cfg.pages_per_block,
                    bytes_processed=(blk + 1) * cfg.block_size,
                    total_bytes=cfg.total_capacity_bytes,
                    percent=((blk + 1) / cfg.total_blocks) * 100.0,
                    current_speed_mbps=0.0,
                    avg_speed_mbps=0.0,
                    elapsed_sec=elapsed,
                    eta_sec=0.0,
                    status_message=f"Scanned Block {blk + 1}/{cfg.total_blocks} (Found {len(bad_blocks)} bad)",
                    block_state_change=(blk, state),
                ))

        logger.info(f"Bad block scan finished. Found {len(bad_blocks)} bad blocks.")
        return bad_blocks

    def dump_flash(
        self,
        output_filepath: str,
        include_oob: bool = True,
        start_block: int = 0,
        end_block: Optional[int] = None,
        progress_cb: Optional[Callable[[ProgressUpdate], None]] = None,
    ) -> Dict[str, Any]:
        """
        Reads flash memory to file with real-time throughput metrics and live hash calculation.
        """
        if not self.active_chip:
            raise RuntimeError("No active chip detected.")

        self.abort_requested = False
        cfg = self.active_chip
        if start_block < 0 or start_block >= cfg.total_blocks:
            raise ValueError(f"start_block must be between 0 and {cfg.total_blocks - 1}.")
        if end_block is None or end_block >= cfg.total_blocks:
            end_block = cfg.total_blocks - 1
        if end_block < start_block:
            raise ValueError("end_block must be greater than or equal to start_block.")

        blocks_to_read = end_block - start_block + 1
        page_read_len = cfg.full_page_size if include_oob else cfg.page_size
        total_bytes = blocks_to_read * cfg.pages_per_block * page_read_len

        md5 = hashlib.md5()
        sha256 = hashlib.sha256()

        bytes_done = 0
        start_time = time.time()
        last_calc_time = start_time
        last_calc_bytes = 0
        current_speed = 0.0

        os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
        with open(output_filepath, "wb") as f_out:
            for blk in range(start_block, end_block + 1):
                if self.abort_requested:
                    break

                block_has_flips = False
                for p_rel in range(cfg.pages_per_block):
                    if self.abort_requested:
                        break

                    page_addr = blk * cfg.pages_per_block + p_rel
                    page_data = self.bridge.read_page(
                        page_addr,
                        col_addr=0,
                        length=page_read_len,
                        col_cycles=cfg.chip_info.col_addr_cycles if cfg.chip_info else cfg.col_addr_cycles,
                        row_cycles=cfg.row_addr_cycles,
                    )
                    if len(page_data) != page_read_len:
                        raise RuntimeError(
                            f"Failed to read page {page_addr}: expected {page_read_len} bytes, "
                            f"received {len(page_data)}."
                        )

                    f_out.write(page_data)
                    md5.update(page_data)
                    sha256.update(page_data)

                    bytes_done += len(page_data)

                # Update speed calculations
                now = time.time()
                elapsed = max(0.001, now - start_time)
                dt = now - last_calc_time
                if dt >= 0.25 or blk == end_block:
                    db = bytes_done - last_calc_bytes
                    current_speed = (db / dt) / (1024 * 1024)
                    last_calc_time = now
                    last_calc_bytes = bytes_done

                avg_speed = (bytes_done / elapsed) / (1024 * 1024)
                rem_bytes = max(0, total_bytes - bytes_done)
                eta = (rem_bytes / (avg_speed * 1024 * 1024)) if avg_speed > 0 else 0.0

                state = BlockState.READ_OK
                self.bad_block_table[blk] = state

                if progress_cb:
                    progress_cb(ProgressUpdate(
                        operation="Dump Flash",
                        current_block=blk + 1,
                        total_blocks=cfg.total_blocks,
                        current_page=(blk + 1) * cfg.pages_per_block,
                        total_pages=cfg.total_blocks * cfg.pages_per_block,
                        bytes_processed=bytes_done,
                        total_bytes=total_bytes,
                        percent=(bytes_done / total_bytes) * 100.0,
                        current_speed_mbps=current_speed,
                        avg_speed_mbps=avg_speed,
                        elapsed_sec=elapsed,
                        eta_sec=eta,
                        status_message=f"Dumping Block {blk} ({bytes_done // (1024*1024)} MB)",
                        block_state_change=(blk, state),
                    ))

        return {
            "completed": not self.abort_requested,
            "bytes_dumped": bytes_done,
            "md5": md5.hexdigest(),
            "sha256": sha256.hexdigest(),
            "output_file": output_filepath,
            "time_sec": time.time() - start_time,
        }

    def write_flash(
        self,
        input_filepath: str,
        skip_bad_blocks: bool = True,
        erase_before_write: bool = True,
        start_block: int = 0,
        progress_cb: Optional[Callable[[ProgressUpdate], None]] = None,
    ) -> Dict[str, Any]:
        """
        Programs file into flash memory with bad-block skipping and optional automatic block erase.
        """
        if not self.active_chip:
            raise RuntimeError("No active chip detected.")

        self.abort_requested = False
        cfg = self.active_chip
        file_size = os.path.getsize(input_filepath)
        if file_size == 0:
            raise ValueError("Input file is empty.")
        if start_block < 0 or start_block >= cfg.total_blocks:
            raise ValueError(f"start_block must be between 0 and {cfg.total_blocks - 1}.")

        # Detect whether input file contains OOB
        contains_oob = False
        if file_size % cfg.full_page_size == 0 and (file_size % cfg.page_size != 0 or file_size > cfg.total_capacity_bytes):
            contains_oob = True

        write_page_len = cfg.full_page_size if contains_oob else cfg.page_size
        total_pages = (file_size + write_page_len - 1) // write_page_len

        bytes_written = 0
        start_time = time.time()
        last_calc_time = start_time
        last_calc_bytes = 0
        current_speed = 0.0

        with open(input_filepath, "rb") as f_in:
            current_chip_block = start_block
            pages_written_in_block = 0

            while bytes_written < file_size and current_chip_block < cfg.total_blocks:
                if self.abort_requested:
                    break

                # Check bad block
                if skip_bad_blocks and self.bad_block_table.get(current_chip_block) == BlockState.BAD:
                    logger.warning(f"Skipping bad block {current_chip_block}")
                    current_chip_block += 1
                    continue

                # Erase block first if needed
                if erase_before_write and pages_written_in_block == 0:
                    if not self.bridge.erase_block(
                        current_chip_block,
                        cfg.pages_per_block,
                        cfg.row_addr_cycles,
                    ):
                        raise RuntimeError(f"Failed to erase block {current_chip_block}.")

                page_chunk = f_in.read(write_page_len)
                if not page_chunk:
                    break

                page_addr = current_chip_block * cfg.pages_per_block + pages_written_in_block
                if not self.bridge.write_page(
                    page_addr,
                    col_addr=0,
                    data=page_chunk,
                    col_cycles=cfg.chip_info.col_addr_cycles if cfg.chip_info else cfg.col_addr_cycles,
                    row_cycles=cfg.row_addr_cycles,
                ):
                    raise RuntimeError(f"Failed to program page {page_addr}.")

                bytes_written += len(page_chunk)
                pages_written_in_block += 1

                if pages_written_in_block >= cfg.pages_per_block:
                    self.bad_block_table[current_chip_block] = BlockState.PROGRAMMED
                    state_change = (current_chip_block, BlockState.PROGRAMMED)
                    current_chip_block += 1
                    pages_written_in_block = 0
                else:
                    state_change = None

                now = time.time()
                elapsed = max(0.001, now - start_time)
                dt = now - last_calc_time
                if dt >= 0.25:
                    db = bytes_written - last_calc_bytes
                    current_speed = (db / dt) / (1024 * 1024)
                    last_calc_time = now
                    last_calc_bytes = bytes_written

                avg_speed = (bytes_written / elapsed) / (1024 * 1024)
                eta = ((file_size - bytes_written) / (avg_speed * 1024 * 1024)) if avg_speed > 0 else 0.0

                if progress_cb:
                    progress_cb(ProgressUpdate(
                        operation="Flash Write",
                        current_block=current_chip_block,
                        total_blocks=cfg.total_blocks,
                        current_page=page_addr + 1,
                        total_pages=total_pages,
                        bytes_processed=bytes_written,
                        total_bytes=file_size,
                        percent=(bytes_written / file_size) * 100.0,
                        current_speed_mbps=current_speed,
                        avg_speed_mbps=avg_speed,
                        elapsed_sec=elapsed,
                        eta_sec=eta,
                        status_message=f"Flashing Block {current_chip_block} ({bytes_written // (1024*1024)} MB)",
                        block_state_change=state_change,
                    ))

        if not self.abort_requested and bytes_written != file_size:
            raise RuntimeError(
                f"Input file does not fit in the available good blocks: "
                f"wrote {bytes_written} of {file_size} bytes."
            )

        return {
            "completed": not self.abort_requested and bytes_written == file_size,
            "bytes_written": bytes_written,
            "time_sec": time.time() - start_time,
        }

    def erase_chip(
        self,
        start_block: int = 0,
        end_block: Optional[int] = None,
        progress_cb: Optional[Callable[[ProgressUpdate], None]] = None,
    ) -> bool:
        """Erases a range of blocks or full chip."""
        if not self.active_chip:
            raise RuntimeError("No active chip detected.")

        self.abort_requested = False
        cfg = self.active_chip
        if start_block < 0 or start_block >= cfg.total_blocks:
            raise ValueError(f"start_block must be between 0 and {cfg.total_blocks - 1}.")
        if end_block is None or end_block >= cfg.total_blocks:
            end_block = cfg.total_blocks - 1
        if end_block < start_block:
            raise ValueError("end_block must be greater than or equal to start_block.")

        total_to_erase = end_block - start_block + 1
        start_time = time.time()

        for idx, blk in enumerate(range(start_block, end_block + 1)):
            if self.abort_requested:
                break

            # Skip known bad blocks to preserve factory bad block markers
            if self.bad_block_table.get(blk) == BlockState.BAD:
                continue

            if not self.bridge.erase_block(blk, cfg.pages_per_block, cfg.row_addr_cycles):
                raise RuntimeError(f"Failed to erase block {blk}.")
            self.bad_block_table[blk] = BlockState.ERASED

            if progress_cb and (idx % 16 == 0 or idx == total_to_erase - 1):
                elapsed = max(0.001, time.time() - start_time)
                progress_cb(ProgressUpdate(
                    operation="Erase Chip",
                    current_block=blk + 1,
                    total_blocks=cfg.total_blocks,
                    current_page=0,
                    total_pages=0,
                    bytes_processed=idx * cfg.block_size,
                    total_bytes=total_to_erase * cfg.block_size,
                    percent=((idx + 1) / total_to_erase) * 100.0,
                    current_speed_mbps=0.0,
                    avg_speed_mbps=0.0,
                    elapsed_sec=elapsed,
                    eta_sec=0.0,
                    status_message=f"Erased Block {blk}/{end_block}",
                    block_state_change=(blk, BlockState.ERASED),
                ))

        return not self.abort_requested
