#include "protocol.h"

uint16_t crc16_ccitt(const uint8_t* data, size_t length, uint16_t initial) {
    uint16_t crc = initial;
    for (size_t i = 0; i < length; i++) {
        crc ^= ((uint16_t)data[i] << 8);
        for (int b = 0; b < 8; b++) {
            if (crc & 0x8000) {
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF;
            } else {
                crc = (crc << 1) & 0xFFFF;
            }
        }
    }
    return crc;
}

void send_response(StatusCode status, uint8_t seq, const uint8_t* payload, uint16_t length) {
    // Header: [0xAA, 0x55] [status: 1B] [seq: 1B] [len: 2B LE] [crc16: 2B LE]
    uint8_t header[HEADER_SIZE];
    header[0] = MAGIC_DEV_0;
    header[1] = MAGIC_DEV_1;
    header[2] = (uint8_t)status;
    header[3] = seq;
    header[4] = (uint8_t)(length & 0xFF);
    header[5] = (uint8_t)((length >> 8) & 0xFF);

    // Compute CRC over status(1), seq(1), len(2), and payload
    uint8_t crc_pre[4];
    crc_pre[0] = (uint8_t)status;
    crc_pre[1] = seq;
    crc_pre[2] = header[4];
    crc_pre[3] = header[5];

    uint16_t crc = crc16_ccitt(crc_pre, 4, 0xFFFF);
    if (payload != nullptr && length > 0) {
        crc = crc16_ccitt(payload, length, crc);
    }

    header[6] = (uint8_t)(crc & 0xFF);
    header[7] = (uint8_t)((crc >> 8) & 0xFF);

    // Write header and payload using USB High Speed CDC
    Serial.write(header, HEADER_SIZE);
    if (payload != nullptr && length > 0) {
        Serial.write(payload, length);
    }
}

