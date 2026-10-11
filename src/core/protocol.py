"""
Universal NAND Flash Clone Tool - Binary Protocol Definition
High-performance framed binary protocol between Host (PC) and Teensy 4.1 hardware bridge.
"""

import struct
from enum import IntEnum
from typing import Tuple, Optional, NamedTuple


class Command(IntEnum):
    CMD_PING = 0x01
    CMD_GET_FW_INFO = 0x02
    CMD_SET_BUS_CONFIG = 0x03
    CMD_RESET_CHIP = 0x04
    CMD_READ_ID = 0x05
    CMD_READ_ONFI = 0x06
    CMD_READ_STATUS = 0x07
    CMD_READ_PAGE = 0x10
    CMD_WRITE_PAGE = 0x11
    CMD_ERASE_BLOCK = 0x12
    CMD_SCAN_BAD_BLOCKS = 0x13
    CMD_STREAM_READ_START = 0x14
    CMD_STREAM_READ_CHUNK = 0x15
    CMD_STREAM_ABORT = 0x16
    CMD_RAW_EXEC = 0x20
    CMD_POWER_CTRL = 0x30
    CMD_PROBE_PINS = 0x31


class StatusCode(IntEnum):
    STATUS_OK = 0x00
    STATUS_ERR_GENERIC = 0x01
    STATUS_ERR_TIMEOUT = 0x02
    STATUS_ERR_BUSY = 0x03
    STATUS_ERR_BAD_CRC = 0x04
    STATUS_ERR_INVALID_PARAM = 0x05
    STATUS_ERR_FAIL = 0x06
    STATUS_ERR_WRITE_PROTECTED = 0x07
    STATUS_ERR_NOT_SUPPORTED = 0x08


class BusType(IntEnum):
    PARALLEL_X8 = 0x01
    PARALLEL_X16 = 0x02
    SPI_STANDARD = 0x03
    SPI_DUAL = 0x04
    SPI_QUAD = 0x05


MAGIC_HOST = bytes([0x55, 0xAA])
MAGIC_DEV = bytes([0xAA, 0x55])

HEADER_HOST_FORMAT = "<2sBBHH"  # magic(2), cmd(1), seq(1), len(2), crc16(2) = 8 bytes
HEADER_DEV_FORMAT = "<2sBBHH"   # magic(2), status(1), seq(1), len(2), crc16(2) = 8 bytes
HEADER_SIZE = 8


def crc16_ccitt(data: bytes, initial: int = 0xFFFF) -> int:
    """
    Standard CCITT CRC-16 (Polynomial 0x1021, Initial 0xFFFF).
    """
    crc = initial
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


class HostPacket(NamedTuple):
    cmd: int
    seq: int
    payload: bytes


class DeviceResponse(NamedTuple):
    status: StatusCode
    seq: int
    payload: bytes


def encode_host_packet(cmd: int, seq: int = 0, payload: bytes = b"") -> bytes:
    """
    Encodes a command packet from Host to Teensy 4.1 bridge.
    Header: [0x55, 0xAA] [cmd: 1B] [seq: 1B] [len: 2B LE] [crc16: 2B LE]
    """
    payload_len = len(payload)
    if payload_len > 65535:
        raise ValueError(f"Payload exceeds maximum 65535 bytes: {payload_len}")

    # Compute CRC over cmd, seq, payload_len, and payload bytes
    crc_data = struct.pack("<BBH", cmd, seq, payload_len) + payload
    crc = crc16_ccitt(crc_data)

    header = struct.pack(HEADER_HOST_FORMAT, MAGIC_HOST, cmd, seq, payload_len, crc)
    return header + payload


def decode_device_packet(buffer: bytes) -> Tuple[Optional[DeviceResponse], int]:
    """
    Parses a response from Teensy 4.1 bridge out of a byte stream buffer.
    Returns (DeviceResponse or None, bytes_consumed).
    """
    buf_len = len(buffer)
    if buf_len < HEADER_SIZE:
        return None, 0

    # Search for magic if out of sync
    sync_idx = buffer.find(MAGIC_DEV)
    if sync_idx == -1:
        # No magic found, consume all but the last byte (which could be the start of magic)
        return None, max(0, buf_len - 1)

    if sync_idx > 0:
        # Discard junk before magic
        return None, sync_idx

    # We are at magic
    magic, status_val, seq, payload_len, received_crc = struct.unpack_from(HEADER_DEV_FORMAT, buffer, 0)
    total_pkt_len = HEADER_SIZE + payload_len

    if buf_len < total_pkt_len:
        # Incomplete packet, wait for more data
        return None, 0

    payload = buffer[HEADER_SIZE:total_pkt_len]

    # Verify CRC
    crc_data = struct.pack("<BBH", status_val, seq, payload_len) + payload
    computed_crc = crc16_ccitt(crc_data)

    if computed_crc != received_crc:
        # CRC mismatch, skip 2 bytes (magic) and resync
        return None, 2

    try:
        status = StatusCode(status_val)
    except ValueError:
        status = StatusCode.STATUS_ERR_GENERIC

    response = DeviceResponse(status=status, seq=seq, payload=payload)
    return response, total_pkt_len

