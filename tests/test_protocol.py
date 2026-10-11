"""Unit tests for binary communication protocol."""
import pytest
from src.core.protocol import (
    Command,
    StatusCode,
    crc16_ccitt,
    encode_host_packet,
    decode_device_packet,
    MAGIC_HOST,
    MAGIC_DEV,
)


def test_crc16_ccitt():
    test_data = b"123456789"
    # CCITT with poly 0x1021, init 0xFFFF for "123456789" is 0x29B1
    crc = crc16_ccitt(test_data)
    assert crc == 0x29B1


def test_encode_and_decode_packet():
    payload = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    cmd = Command.CMD_READ_PAGE
    seq = 42

    pkt = encode_host_packet(cmd, seq, payload)
    assert len(pkt) == 8 + len(payload)
    assert pkt[0:2] == MAGIC_HOST


def test_decode_device_packet():
    import struct
    payload = b"Teensy 4.1 NAND OK"
    status = StatusCode.STATUS_OK
    seq = 10
    payload_len = len(payload)

    crc_data = struct.pack("<BBH", int(status), seq, payload_len) + payload
    crc = crc16_ccitt(crc_data)

    header = struct.pack("<2sBBHH", MAGIC_DEV, int(status), seq, payload_len, crc)
    raw_stream = b"junk123" + header + payload + b"trailing"

    resp, consumed = decode_device_packet(raw_stream)
    # First call will skip junk123
    assert resp is None
    assert consumed == 7

    raw_stream2 = raw_stream[consumed:]
    resp2, consumed2 = decode_device_packet(raw_stream2)
    assert resp2 is not None
    assert resp2.status == StatusCode.STATUS_OK
    assert resp2.seq == seq
    assert resp2.payload == payload
    assert consumed2 == len(header) + len(payload)

