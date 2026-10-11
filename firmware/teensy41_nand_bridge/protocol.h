#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <Arduino.h>

#define MAGIC_HOST_0 0x55
#define MAGIC_HOST_1 0xAA

#define MAGIC_DEV_0  0xAA
#define MAGIC_DEV_1  0x55

#define HEADER_SIZE  8

enum Command : uint8_t {
    CMD_PING              = 0x01,
    CMD_GET_FW_INFO       = 0x02,
    CMD_SET_BUS_CONFIG    = 0x03,
    CMD_RESET_CHIP        = 0x04,
    CMD_READ_ID           = 0x05,
    CMD_READ_ONFI         = 0x06,
    CMD_READ_STATUS       = 0x07,
    CMD_READ_PAGE         = 0x10,
    CMD_WRITE_PAGE        = 0x11,
    CMD_ERASE_BLOCK       = 0x12,
    CMD_SCAN_BAD_BLOCKS   = 0x13,
    CMD_STREAM_READ_START = 0x14,
    CMD_STREAM_READ_CHUNK = 0x15,
    CMD_STREAM_ABORT      = 0x16,
    CMD_RAW_EXEC          = 0x20,
    CMD_POWER_CTRL        = 0x30,
    CMD_PROBE_PINS        = 0x31,
};

enum StatusCode : uint8_t {
    STATUS_OK             = 0x00,
    STATUS_ERR_GENERIC    = 0x01,
    STATUS_ERR_TIMEOUT    = 0x02,
    STATUS_ERR_BUSY       = 0x03,
    STATUS_ERR_BAD_CRC    = 0x04,
    STATUS_ERR_INVALID_PARAM = 0x05,
    STATUS_ERR_FAIL       = 0x06,
    STATUS_ERR_WRITE_PROTECTED = 0x07,
    STATUS_ERR_NOT_SUPPORTED   = 0x08,
};

enum BusType : uint8_t {
    BUS_PARALLEL_X8       = 0x01,
    BUS_PARALLEL_X16      = 0x02,
    BUS_SPI_STANDARD      = 0x03,
    BUS_SPI_DUAL          = 0x04,
    BUS_SPI_QUAD          = 0x05,
};

uint16_t crc16_ccitt(const uint8_t* data, size_t length, uint16_t initial = 0xFFFF);

void send_response(StatusCode status, uint8_t seq, const uint8_t* payload, uint16_t length);

#endif // PROTOCOL_H

