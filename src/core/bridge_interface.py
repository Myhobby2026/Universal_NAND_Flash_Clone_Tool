"""
Universal NAND Flash Clone Tool - Bridge Interface
Abstract base class and pyserial implementation for Teensy 4.1 hardware bridge communication.
"""

import time
import struct
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
import serial
import serial.tools.list_ports

from .protocol import (
    Command,
    StatusCode,
    BusType,
    encode_host_packet,
    decode_device_packet,
    DeviceResponse,
)

logger = logging.getLogger("NANDBridge")


class BridgeInterface(ABC):
    """Abstract interface for NAND Flash Hardware Bridge."""

    @abstractmethod
    def connect(self, port: str, baudrate: int = 12000000) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def ping(self) -> bool:
        pass

    @abstractmethod
    def get_firmware_info(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def set_bus_config(self, bus_type: BusType, timing_mode: int = 0, ce_idx: int = 0, vcc_en: bool = True) -> bool:
        pass

    @abstractmethod
    def reset_chip(self) -> bool:
        pass

    @abstractmethod
    def read_chip_id(self) -> bytes:
        pass

    @abstractmethod
    def read_onfi_parameter_page(self) -> bytes:
        pass

    @abstractmethod
    def read_status(self) -> int:
        pass

    @abstractmethod
    def read_page(
        self,
        page_addr: int,
        col_addr: int = 0,
        length: int = 2112,
        col_cycles: int = 2,
        row_cycles: int = 3,
    ) -> bytes:
        pass

    @abstractmethod
    def write_page(
        self,
        page_addr: int,
        col_addr: int = 0,
        data: bytes = b"",
        col_cycles: int = 2,
        row_cycles: int = 3,
    ) -> bool:
        pass

    @abstractmethod
    def erase_block(
        self,
        block_addr: int,
        pages_per_block: int = 64,
        row_cycles: int = 3,
    ) -> bool:
        pass

    @abstractmethod
    def scan_bad_blocks(
        self,
        total_blocks: int,
        pages_per_block: int = 64,
        oob_offset: int = 0,
        col_cycles: int = 2,
        row_cycles: int = 3,
    ) -> List[int]:
        pass

    @abstractmethod
    def probe_pins(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def power_control(self, power_on: bool) -> bool:
        pass


class TeensyBridge(BridgeInterface):
    """
    Serial implementation communicating with Teensy 4.1 running universal NAND firmware.
    """

    def __init__(self):
        self.ser: Optional[serial.Serial] = None
        self.seq_num: int = 0
        self._rx_buffer = bytearray()
        self.port_name: str = ""

    def connect(self, port: str, baudrate: int = 12000000) -> bool:
        try:
            self.disconnect()
            # In Teensy 4.1 USB Serial, the baud rate parameter is advisory (runs at full USB 480Mbps)
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=0.2,
                write_timeout=1.0,
            )
            # Flush buffers
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self._rx_buffer.clear()
            self.port_name = port

            # Verify connection with ping
            time.sleep(0.05)
            if self.ping():
                logger.info(f"Connected to Teensy 4.1 bridge on {port}")
                return True
            else:
                logger.warning(f"Port {port} opened but bridge ping failed.")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to {port}: {e}")
            self.disconnect()
            return False

    def disconnect(self) -> None:
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self._rx_buffer.clear()
        self.port_name = ""

    def is_connected(self) -> bool:
        return self.ser is not None and self.ser.is_open

    def _next_seq(self) -> int:
        self.seq_num = (self.seq_num + 1) & 0xFF
        return self.seq_num

    def _send_command(self, cmd: Command, payload: bytes = b"", timeout_sec: float = 1.0) -> Tuple[StatusCode, bytes]:
        if not self.is_connected() or self.ser is None:
            return StatusCode.STATUS_ERR_GENERIC, b""

        seq = self._next_seq()
        pkt = encode_host_packet(int(cmd), seq, payload)

        try:
            self.ser.write(pkt)
            self.ser.flush()
        except Exception as e:
            logger.error(f"Serial write error for cmd {cmd.name}: {e}")
            return StatusCode.STATUS_ERR_GENERIC, b""

        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            try:
                waiting = self.ser.in_waiting
                if waiting > 0:
                    chunk = self.ser.read(waiting)
                    if chunk:
                        self._rx_buffer.extend(chunk)

                resp, consumed = decode_device_packet(bytes(self._rx_buffer))
                if consumed > 0:
                    del self._rx_buffer[:consumed]

                if resp is not None:
                    if resp.seq == seq:
                        return resp.status, resp.payload
                    else:
                        # Stale packet or mismatched seq, continue
                        continue
            except Exception as e:
                logger.error(f"Serial read error: {e}")
                break

            time.sleep(0.001)

        logger.warning(f"Timeout waiting for response to cmd {cmd.name} (seq {seq})")
        return StatusCode.STATUS_ERR_TIMEOUT, b""

    def ping(self) -> bool:
        status, _ = self._send_command(Command.CMD_PING, timeout_sec=0.5)
        return status == StatusCode.STATUS_OK

    def get_firmware_info(self) -> Dict[str, Any]:
        status, payload = self._send_command(Command.CMD_GET_FW_INFO, timeout_sec=0.5)
        if status != StatusCode.STATUS_OK or len(payload) < 8:
            return {"connected": False, "version": "Unknown"}

        # Payload format: major(1), minor(1), patch(1), mcu_freq_mhz(2), caps(2), board_str(variable)
        major, minor, patch, freq_mhz, caps = struct.unpack_from("<BBHHH", payload, 0)
        board_name = payload[7:].decode("ascii", errors="replace").strip() if len(payload) > 7 else "Teensy 4.1"

        return {
            "connected": True,
            "version": f"{major}.{minor}.{patch}",
            "mcu_freq_mhz": freq_mhz,
            "capabilities": caps,
            "board": board_name,
        }

    def set_bus_config(self, bus_type: BusType, timing_mode: int = 0, ce_idx: int = 0, vcc_en: bool = True) -> bool:
        payload = struct.pack("<BBBB", int(bus_type), timing_mode, ce_idx, 1 if vcc_en else 0)
        status, _ = self._send_command(Command.CMD_SET_BUS_CONFIG, payload)
        return status == StatusCode.STATUS_OK

    def reset_chip(self) -> bool:
        status, _ = self._send_command(Command.CMD_RESET_CHIP, timeout_sec=1.0)
        return status == StatusCode.STATUS_OK

    def read_chip_id(self) -> bytes:
        status, payload = self._send_command(Command.CMD_READ_ID, timeout_sec=0.5)
        if status == StatusCode.STATUS_OK:
            return payload
        return b""

    def read_onfi_parameter_page(self) -> bytes:
        status, payload = self._send_command(Command.CMD_READ_ONFI, timeout_sec=1.5)
        if status == StatusCode.STATUS_OK:
            return payload
        return b""

    def read_status(self) -> int:
        status, payload = self._send_command(Command.CMD_READ_STATUS, timeout_sec=0.5)
        if status == StatusCode.STATUS_OK and len(payload) >= 1:
            return payload[0]
        return 0x00

    def read_page(
        self,
        page_addr: int,
        col_addr: int = 0,
        length: int = 2112,
        col_cycles: int = 2,
        row_cycles: int = 3,
    ) -> bytes:
        # Payload: page_addr(4), col_addr(2), length(2), col_cycles(1), row_cycles(1)
        payload = struct.pack("<IHHBB", page_addr, col_addr, length, col_cycles, row_cycles)
        status, rx_data = self._send_command(Command.CMD_READ_PAGE, payload, timeout_sec=2.0)
        if status == StatusCode.STATUS_OK:
            return rx_data
        return b""

    def write_page(
        self,
        page_addr: int,
        col_addr: int = 0,
        data: bytes = b"",
        col_cycles: int = 2,
        row_cycles: int = 3,
    ) -> bool:
        # Payload: page_addr(4), col_addr(2), data_len(2), data(...)
        header = struct.pack("<IHH", page_addr, col_addr, len(data))
        payload = header + data + bytes((col_cycles, row_cycles))
        status, _ = self._send_command(Command.CMD_WRITE_PAGE, payload, timeout_sec=3.0)
        return status == StatusCode.STATUS_OK

    def erase_block(
        self,
        block_addr: int,
        pages_per_block: int = 64,
        row_cycles: int = 3,
    ) -> bool:
        # Payload: block_addr(4), pages_per_block(4), row_cycles(1)
        payload = struct.pack("<IIB", block_addr, pages_per_block, row_cycles)
        status, _ = self._send_command(Command.CMD_ERASE_BLOCK, payload, timeout_sec=3.0)
        return status == StatusCode.STATUS_OK

    def scan_bad_blocks(
        self,
        total_blocks: int,
        pages_per_block: int = 64,
        oob_offset: int = 0,
        col_cycles: int = 2,
        row_cycles: int = 3,
    ) -> List[int]:
        # Fast hardware assisted bad block scan
        payload = struct.pack("<IIHBB", total_blocks, pages_per_block, oob_offset, col_cycles, row_cycles)
        status, rx_data = self._send_command(Command.CMD_SCAN_BAD_BLOCKS, payload, timeout_sec=10.0)
        bad_blocks = []
        if status == StatusCode.STATUS_OK:
            # Array of uint32 bad block numbers
            count = len(rx_data) // 4
            for i in range(count):
                blk = struct.unpack_from("<I", rx_data, i * 4)[0]
                bad_blocks.append(blk)
        return bad_blocks

    def probe_pins(self) -> Dict[str, Any]:
        status, payload = self._send_command(Command.CMD_PROBE_PINS, timeout_sec=0.5)
        if status == StatusCode.STATUS_OK and len(payload) >= 4:
            rb_pin, ce_pin, cle_pin, ale_pin = struct.unpack_from("<4B", payload, 0)
            return {
                "RB": bool(rb_pin),
                "CE": bool(ce_pin),
                "CLE": bool(cle_pin),
                "ALE": bool(ale_pin),
            }
        return {"RB": True, "CE": False, "CLE": False, "ALE": False}

    def power_control(self, power_on: bool) -> bool:
        payload = bytes([1 if power_on else 0])
        status, _ = self._send_command(Command.CMD_POWER_CTRL, payload, timeout_sec=0.5)
        return status == StatusCode.STATUS_OK


def list_serial_ports() -> List[Dict[str, str]]:
    """Lists available serial ports with Teensy 4.1 identification."""
    ports = []
    for port_info in serial.tools.list_ports.comports():
        is_teensy = False
        # Teensy USB Vendor ID is 0x16C0 (PJRC), Product ID 0x0483 or 0x0486
        if port_info.vid == 0x16C0 or "teensy" in (port_info.description or "").lower():
            is_teensy = True

        ports.append({
            "device": port_info.device,
            "description": port_info.description or port_info.device,
            "is_teensy": is_teensy,
            "hwid": port_info.hwid or "",
        })
    return ports
