#ifndef NAND_SPI_H
#define NAND_SPI_H

#include <Arduino.h>
#include <SPI.h>
#include "config.h"

class SPINAND {
public:
    SPINAND();

    void init();
    bool reset();
    void read_id(uint8_t* dest, uint8_t count = 3);
    uint8_t get_feature(uint8_t reg_addr);
    void set_feature(uint8_t reg_addr, uint8_t val);
    void write_enable();

    bool read_page(uint32_t page_addr, uint16_t col_addr, uint8_t* buffer, uint16_t length);
    bool write_page(uint32_t page_addr, uint16_t col_addr, const uint8_t* buffer, uint16_t length);
    bool erase_block(uint32_t block_addr, uint32_t pages_per_block = 64);

    bool wait_busy(uint32_t timeout_us = 1000000);

private:
    SPISettings spi_settings;
};

extern SPINAND spiNAND;

#endif // NAND_SPI_H
