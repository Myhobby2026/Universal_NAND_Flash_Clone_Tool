// ==============================================================================
// UNIVERSAL NAND FLASH CLONE TOOL - TEENSY 4.1 BRIDGE FIRMWARE
// Platform: Teensy 4.1 (600MHz ARM Cortex-M7, 480Mbps High-Speed USB CDC)
// Supports Parallel NAND (TSOP-48, BGA-63) & SPI NAND (WSON-8, SOIC-8/16)
// ==============================================================================

#include "config.h"
#include "protocol.h"
#include "nand_parallel.h"
#include "nand_spi.h"

// State variables
static BusType current_bus_type = BUS_PARALLEL_X8;
static uint8_t page_buffer[18432]; // Accommodates up to 16K + 2K spare pages

static bool is_spi_bus() {
    return current_bus_type == BUS_SPI_STANDARD;
}

// Serial framing state machine
enum RxState {
    WAIT_MAGIC_0,
    WAIT_MAGIC_1,
    READ_HEADER,
    READ_PAYLOAD
};

static RxState rx_state = WAIT_MAGIC_0;
static uint8_t rx_header[HEADER_SIZE];
static uint16_t rx_header_bytes = 0;
static uint16_t rx_payload_bytes = 0;
static uint8_t rx_cmd = 0;
static uint8_t rx_seq = 0;
static uint16_t rx_len = 0;
static uint16_t rx_crc = 0;

void setup() {
    pinMode(PIN_LED_STATUS, OUTPUT);
    digitalWriteFast(PIN_LED_STATUS, HIGH);

    // High Speed USB Serial setup
    Serial.begin(12000000); // Advisory rate; Teensy uses native 480Mbps High Speed

    parallelNAND.init();
    spiNAND.init();

    delay(200);
    digitalWriteFast(PIN_LED_STATUS, LOW);
}

void process_packet(uint8_t cmd, uint8_t seq, const uint8_t* payload, uint16_t len) {
    digitalWriteFast(PIN_LED_STATUS, HIGH);

    switch (cmd) {
        case CMD_PING: {
            send_response(STATUS_OK, seq, nullptr, 0);
            break;
        }

        case CMD_GET_FW_INFO: {
            // Payload: major(1), minor(1), patch(1), mcu_freq(2), caps(2), board_name(string)
            uint8_t info[64];
            info[0] = FW_VERSION_MAJOR;
            info[1] = FW_VERSION_MINOR;
            info[2] = FW_VERSION_PATCH;
            uint16_t freq = (uint16_t)(F_CPU_ACTUAL / 1000000);
            info[3] = (uint8_t)(freq & 0xFF);
            info[4] = (uint8_t)((freq >> 8) & 0xFF);
            uint16_t caps = 0x000D; // Parallel x8, SPI, and ONFI
            info[5] = (uint8_t)(caps & 0xFF);
            info[6] = (uint8_t)((caps >> 8) & 0xFF);
            size_t name_len = strlen(FW_BOARD_NAME);
            memcpy(&info[7], FW_BOARD_NAME, name_len);
            send_response(STATUS_OK, seq, info, 7 + name_len);
            break;
        }

        case CMD_SET_BUS_CONFIG: {
            if (len >= 4) {
                BusType requested_bus = (BusType)payload[0];
                if (requested_bus == BUS_PARALLEL_X16 ||
                    requested_bus == BUS_SPI_DUAL ||
                    requested_bus == BUS_SPI_QUAD) {
                    send_response(STATUS_ERR_NOT_SUPPORTED, seq, nullptr, 0);
                    break;
                }
                if (requested_bus != BUS_PARALLEL_X8 &&
                    requested_bus != BUS_SPI_STANDARD) {
                    send_response(STATUS_ERR_INVALID_PARAM, seq, nullptr, 0);
                    break;
                }
                current_bus_type = requested_bus;
                uint8_t timing_mode = payload[1];
                uint8_t ce_idx = payload[2];
                bool vcc_en = (payload[3] != 0);

                parallelNAND.set_timing_mode(timing_mode);
                parallelNAND.set_ce(ce_idx);
                parallelNAND.set_power(vcc_en);

                send_response(STATUS_OK, seq, nullptr, 0);
            } else {
                send_response(STATUS_ERR_INVALID_PARAM, seq, nullptr, 0);
            }
            break;
        }

        case CMD_RESET_CHIP: {
            bool ok = false;
            if (is_spi_bus()) {
                ok = spiNAND.reset();
            } else {
                ok = parallelNAND.reset();
            }
            send_response(ok ? STATUS_OK : STATUS_ERR_TIMEOUT, seq, nullptr, 0);
            break;
        }

        case CMD_READ_ID: {
            uint8_t id_buf[8] = {0};
            if (is_spi_bus()) {
                spiNAND.read_id(id_buf, 3);
                send_response(STATUS_OK, seq, id_buf, 3);
            } else {
                parallelNAND.read_id(id_buf, 5);
                send_response(STATUS_OK, seq, id_buf, 5);
            }
            break;
        }

        case CMD_READ_ONFI: {
            if (current_bus_type == BUS_PARALLEL_X8) {
                bool ok = parallelNAND.read_onfi(page_buffer, 768);
                if (ok) {
                    send_response(STATUS_OK, seq, page_buffer, 768);
                } else {
                    send_response(STATUS_ERR_FAIL, seq, nullptr, 0);
                }
            } else {
                send_response(STATUS_ERR_NOT_SUPPORTED, seq, nullptr, 0);
            }
            break;
        }

        case CMD_READ_STATUS: {
            uint8_t st = 0;
            if (is_spi_bus()) {
                st = spiNAND.get_feature(0xC0);
            } else {
                st = parallelNAND.read_status();
            }
            send_response(STATUS_OK, seq, &st, 1);
            break;
        }

        case CMD_READ_PAGE: {
            if (len >= 8) {
                uint32_t page_addr = payload[0] | ((uint32_t)payload[1] << 8) |
                                     ((uint32_t)payload[2] << 16) | ((uint32_t)payload[3] << 24);
                uint16_t col_addr  = payload[4] | ((uint16_t)payload[5] << 8);
                uint16_t read_len  = payload[6] | ((uint16_t)payload[7] << 8);

                if (read_len > sizeof(page_buffer)) {
                    send_response(STATUS_ERR_INVALID_PARAM, seq, nullptr, 0);
                    break;
                }

                uint8_t col_cycles = (len >= 9) ? payload[8] : 2;
                uint8_t row_cycles = (len >= 10) ? payload[9] : 3;

                bool ok = false;
                if (is_spi_bus()) {
                    ok = spiNAND.read_page(page_addr, col_addr, page_buffer, read_len);
                } else {
                    ok = parallelNAND.read_page(page_addr, col_addr, page_buffer, read_len, col_cycles, row_cycles);
                }

                if (ok) {
                    send_response(STATUS_OK, seq, page_buffer, read_len);
                } else {
                    send_response(STATUS_ERR_TIMEOUT, seq, nullptr, 0);
                }
            } else {
                send_response(STATUS_ERR_INVALID_PARAM, seq, nullptr, 0);
            }
            break;
        }

        case CMD_WRITE_PAGE: {
            if (len >= 8) {
                uint32_t page_addr = payload[0] | ((uint32_t)payload[1] << 8) |
                                     ((uint32_t)payload[2] << 16) | ((uint32_t)payload[3] << 24);
                uint16_t col_addr  = payload[4] | ((uint16_t)payload[5] << 8);
                uint16_t data_len  = payload[6] | ((uint16_t)payload[7] << 8);

                if (len >= (8 + data_len)) {
                    const uint8_t* pdata = &payload[8];
                    uint8_t col_cycles = (len >= (8 + data_len + 1)) ? payload[8 + data_len] : 2;
                    uint8_t row_cycles = (len >= (8 + data_len + 2)) ? payload[8 + data_len + 1] : 3;
                    bool ok = false;
                    if (is_spi_bus()) {
                        ok = spiNAND.write_page(page_addr, col_addr, pdata, data_len);
                    } else {
                        ok = parallelNAND.write_page(page_addr, col_addr, pdata, data_len, col_cycles, row_cycles);
                    }
                    send_response(ok ? STATUS_OK : STATUS_ERR_FAIL, seq, nullptr, 0);
                } else {
                    send_response(STATUS_ERR_INVALID_PARAM, seq, nullptr, 0);
                }
            } else {
                send_response(STATUS_ERR_INVALID_PARAM, seq, nullptr, 0);
            }
            break;
        }

        case CMD_ERASE_BLOCK: {
            if (len >= 4) {
                uint32_t block_addr = payload[0] | ((uint32_t)payload[1] << 8) |
                                      ((uint32_t)payload[2] << 16) | ((uint32_t)payload[3] << 24);
                uint32_t pages_per_blk = 64;
                uint8_t row_cycles = 3;
                if (len >= 9) {
                    pages_per_blk = payload[4] | ((uint32_t)payload[5] << 8) |
                                    ((uint32_t)payload[6] << 16) | ((uint32_t)payload[7] << 24);
                    row_cycles = payload[8];
                } else {
                    // Retain compatibility with the original one-byte geometry payload.
                    if (len >= 5) pages_per_blk = payload[4];
                    if (len >= 6) row_cycles = payload[5];
                }
                bool ok = false;
                if (is_spi_bus()) {
                    ok = spiNAND.erase_block(block_addr, pages_per_blk);
                } else {
                    ok = parallelNAND.erase_block(block_addr, pages_per_blk, row_cycles);
                }
                send_response(ok ? STATUS_OK : STATUS_ERR_FAIL, seq, nullptr, 0);
            } else {
                send_response(STATUS_ERR_INVALID_PARAM, seq, nullptr, 0);
            }
            break;
        }

        case CMD_SCAN_BAD_BLOCKS: {
            if (len >= 10) {
                uint32_t total_blocks = payload[0] | ((uint32_t)payload[1] << 8) |
                                        ((uint32_t)payload[2] << 16) | ((uint32_t)payload[3] << 24);
                uint32_t pages_per_blk = payload[4] | ((uint32_t)payload[5] << 8) |
                                         ((uint32_t)payload[6] << 16) | ((uint32_t)payload[7] << 24);
                uint16_t oob_col = payload[8] | ((uint16_t)payload[9] << 8);
                uint8_t col_cycles = (len >= 11) ? payload[10] : 2;
                uint8_t row_cycles = (len >= 12) ? payload[11] : 3;

                if (total_blocks == 0 || pages_per_blk == 0) {
                    send_response(STATUS_ERR_INVALID_PARAM, seq, nullptr, 0);
                    break;
                }

                // Hardware-speed bad block scan
                uint32_t bad_list[sizeof(page_buffer) / sizeof(uint32_t)];
                uint16_t bad_count = 0;
                uint8_t marker_val = 0xFF;

                for (uint32_t b = 0; b < total_blocks; b++) {
                    uint64_t p_addr_wide = (uint64_t)b * pages_per_blk;
                    if (p_addr_wide > 0xFFFFFFFFUL) {
                        send_response(STATUS_ERR_INVALID_PARAM, seq, nullptr, 0);
                        digitalWriteFast(PIN_LED_STATUS, LOW);
                        return;
                    }
                    uint32_t p_addr = (uint32_t)p_addr_wide;
                    bool is_bad = false;

                    bool page_read_ok = false;
                    if (is_spi_bus()) {
                        page_read_ok = spiNAND.read_page(p_addr, oob_col, &marker_val, 1);
                    } else {
                        page_read_ok = parallelNAND.read_page(
                            p_addr, oob_col, &marker_val, 1, col_cycles, row_cycles
                        );
                    }
                    if (!page_read_ok) {
                        send_response(STATUS_ERR_TIMEOUT, seq, nullptr, 0);
                        digitalWriteFast(PIN_LED_STATUS, LOW);
                        return;
                    }
                    if (marker_val != 0xFF) is_bad = true;
                    else {
                        marker_val = 0xFF;
                        if (is_spi_bus()) {
                            page_read_ok = spiNAND.read_page(p_addr + 1, oob_col, &marker_val, 1);
                        } else {
                            page_read_ok = parallelNAND.read_page(
                                p_addr + 1, oob_col, &marker_val, 1, col_cycles, row_cycles
                            );
                        }
                        if (!page_read_ok) {
                            send_response(STATUS_ERR_TIMEOUT, seq, nullptr, 0);
                            digitalWriteFast(PIN_LED_STATUS, LOW);
                            return;
                        }
                        if (marker_val != 0xFF) is_bad = true;
                    }

                    if (is_bad && bad_count < (sizeof(bad_list) / sizeof(bad_list[0]))) {
                        bad_list[bad_count++] = b;
                    } else if (is_bad) {
                        send_response(STATUS_ERR_INVALID_PARAM, seq, nullptr, 0);
                        digitalWriteFast(PIN_LED_STATUS, LOW);
                        return;
                    }
                }

                send_response(STATUS_OK, seq, (const uint8_t*)bad_list, bad_count * 4);
            } else {
                send_response(STATUS_ERR_INVALID_PARAM, seq, nullptr, 0);
            }
            break;
        }

        case CMD_PROBE_PINS: {
            bool rb = true, ce = false, cle = false, ale = false;
            parallelNAND.probe_signals(rb, ce, cle, ale);
            uint8_t pin_states[4] = {
                (uint8_t)(rb ? 1 : 0),
                (uint8_t)(ce ? 1 : 0),
                (uint8_t)(cle ? 1 : 0),
                (uint8_t)(ale ? 1 : 0)
            };
            send_response(STATUS_OK, seq, pin_states, 4);
            break;
        }

        case CMD_POWER_CTRL: {
            if (len >= 1) {
                parallelNAND.set_power(payload[0] != 0);
                send_response(STATUS_OK, seq, nullptr, 0);
            } else {
                send_response(STATUS_ERR_INVALID_PARAM, seq, nullptr, 0);
            }
            break;
        }

        default:
            send_response(STATUS_ERR_NOT_SUPPORTED, seq, nullptr, 0);
            break;
    }

    digitalWriteFast(PIN_LED_STATUS, LOW);
}

void loop() {
    while (Serial.available()) {
        uint8_t byte = Serial.read();

        switch (rx_state) {
            case WAIT_MAGIC_0:
                if (byte == MAGIC_HOST_0) {
                    rx_state = WAIT_MAGIC_1;
                }
                break;

            case WAIT_MAGIC_1:
                if (byte == MAGIC_HOST_1) {
                    rx_header[0] = MAGIC_HOST_0;
                    rx_header[1] = MAGIC_HOST_1;
                    rx_header_bytes = 2;
                    rx_state = READ_HEADER;
                } else if (byte != MAGIC_HOST_0) {
                    rx_state = WAIT_MAGIC_0;
                }
                break;

            case READ_HEADER:
                rx_header[rx_header_bytes++] = byte;
                if (rx_header_bytes == HEADER_SIZE) {
                    rx_cmd = rx_header[2];
                    rx_seq = rx_header[3];
                    rx_len = rx_header[4] | ((uint16_t)rx_header[5] << 8);
                    rx_crc = rx_header[6] | ((uint16_t)rx_header[7] << 8);

                    if (rx_len > sizeof(page_buffer)) {
                        // Overflow guard
                        rx_state = WAIT_MAGIC_0;
                        break;
                    }

                    if (rx_len == 0) {
                        // Verify CRC over cmd, seq, len
                        uint8_t crc_pre[4] = {rx_cmd, rx_seq, rx_header[4], rx_header[5]};
                        uint16_t calc_crc = crc16_ccitt(crc_pre, 4, 0xFFFF);
                        if (calc_crc == rx_crc) {
                            process_packet(rx_cmd, rx_seq, nullptr, 0);
                        } else {
                            send_response(STATUS_ERR_BAD_CRC, rx_seq, nullptr, 0);
                        }
                        rx_state = WAIT_MAGIC_0;
                    } else {
                        rx_payload_bytes = 0;
                        rx_state = READ_PAYLOAD;
                    }
                }
                break;

            case READ_PAYLOAD:
                page_buffer[rx_payload_bytes++] = byte;
                if (rx_payload_bytes == rx_len) {
                    // Verify CRC
                    uint8_t crc_pre[4] = {rx_cmd, rx_seq, rx_header[4], rx_header[5]};
                    uint16_t calc_crc = crc16_ccitt(crc_pre, 4, 0xFFFF);
                    calc_crc = crc16_ccitt(page_buffer, rx_len, calc_crc);

                    if (calc_crc == rx_crc) {
                        process_packet(rx_cmd, rx_seq, page_buffer, rx_len);
                    } else {
                        send_response(STATUS_ERR_BAD_CRC, rx_seq, nullptr, 0);
                    }
                    rx_state = WAIT_MAGIC_0;
                }
                break;
        }
    }
}
