#include "nand_spi.h"

SPINAND spiNAND;

SPINAND::SPINAND() : spi_settings(30000000, MSBFIRST, SPI_MODE0) {}

void SPINAND::init() {
    pinMode(PIN_SPI_CS, OUTPUT);
    digitalWriteFast(PIN_SPI_CS, HIGH);

    pinMode(PIN_SPI_WP, OUTPUT);
    digitalWriteFast(PIN_SPI_WP, HIGH);

    pinMode(PIN_SPI_HOLD, OUTPUT);
    digitalWriteFast(PIN_SPI_HOLD, HIGH);

    SPI.begin();
}

bool SPINAND::reset() {
    SPI.beginTransaction(spi_settings);
    digitalWriteFast(PIN_SPI_CS, LOW);
    SPI.transfer(0xFF); // Reset command
    digitalWriteFast(PIN_SPI_CS, HIGH);
    SPI.endTransaction();

    return wait_busy(50000);
}

void SPINAND::read_id(uint8_t* dest, uint8_t count) {
    SPI.beginTransaction(spi_settings);
    digitalWriteFast(PIN_SPI_CS, LOW);

    SPI.transfer(0x9F); // Read JEDEC ID
    SPI.transfer(0x00); // Dummy byte for SPI NAND

    for (uint8_t i = 0; i < count; i++) {
        dest[i] = SPI.transfer(0x00);
    }

    digitalWriteFast(PIN_SPI_CS, HIGH);
    SPI.endTransaction();
}

uint8_t SPINAND::get_feature(uint8_t reg_addr) {
    SPI.beginTransaction(spi_settings);
    digitalWriteFast(PIN_SPI_CS, LOW);

    SPI.transfer(0x0F);
    SPI.transfer(reg_addr);
    uint8_t val = SPI.transfer(0x00);

    digitalWriteFast(PIN_SPI_CS, HIGH);
    SPI.endTransaction();
    return val;
}

void SPINAND::set_feature(uint8_t reg_addr, uint8_t val) {
    SPI.beginTransaction(spi_settings);
    digitalWriteFast(PIN_SPI_CS, LOW);

    SPI.transfer(0x1F);
    SPI.transfer(reg_addr);
    SPI.transfer(val);

    digitalWriteFast(PIN_SPI_CS, HIGH);
    SPI.endTransaction();
}

void SPINAND::write_enable() {
    SPI.beginTransaction(spi_settings);
    digitalWriteFast(PIN_SPI_CS, LOW);
    SPI.transfer(0x06); // WREN
    digitalWriteFast(PIN_SPI_CS, HIGH);
    SPI.endTransaction();
}

bool SPINAND::wait_busy(uint32_t timeout_us) {
    uint32_t start = micros();
    while (get_feature(0xC0) & 0x01) { // Status register bit 0 is OIP (Operation In Progress)
        if ((micros() - start) > timeout_us) {
            return false;
        }
    }
    return true;
}

bool SPINAND::read_page(uint32_t page_addr, uint16_t col_addr, uint8_t* buffer, uint16_t length) {
    if (page_addr > 0x00FFFFFFUL) {
        return false;
    }

    // 1. Page Read to Cache (Command 0x13)
    SPI.beginTransaction(spi_settings);
    digitalWriteFast(PIN_SPI_CS, LOW);
    SPI.transfer(0x13);
    SPI.transfer((uint8_t)((page_addr >> 16) & 0xFF));
    SPI.transfer((uint8_t)((page_addr >> 8) & 0xFF));
    SPI.transfer((uint8_t)(page_addr & 0xFF));
    digitalWriteFast(PIN_SPI_CS, HIGH);
    SPI.endTransaction();

    if (!wait_busy(100000)) {
        return false;
    }

    // 2. Read from Cache (Command 0x03 or 0x0B)
    SPI.beginTransaction(spi_settings);
    digitalWriteFast(PIN_SPI_CS, LOW);
    SPI.transfer(0x03);
    SPI.transfer((uint8_t)((col_addr >> 8) & 0xFF));
    SPI.transfer((uint8_t)(col_addr & 0xFF));
    SPI.transfer(0x00); // 1 dummy byte

    for (uint16_t i = 0; i < length; i++) {
        buffer[i] = SPI.transfer(0x00);
    }

    digitalWriteFast(PIN_SPI_CS, HIGH);
    SPI.endTransaction();
    return true;
}

bool SPINAND::write_page(uint32_t page_addr, uint16_t col_addr, const uint8_t* buffer, uint16_t length) {
    if (page_addr > 0x00FFFFFFUL) {
        return false;
    }

    write_enable();

    // 1. Program Load (Command 0x02)
    SPI.beginTransaction(spi_settings);
    digitalWriteFast(PIN_SPI_CS, LOW);
    SPI.transfer(0x02);
    SPI.transfer((uint8_t)((col_addr >> 8) & 0xFF));
    SPI.transfer((uint8_t)(col_addr & 0xFF));

    for (uint16_t i = 0; i < length; i++) {
        SPI.transfer(buffer[i]);
    }
    digitalWriteFast(PIN_SPI_CS, HIGH);
    SPI.endTransaction();

    // 2. Program Execute (Command 0x10)
    SPI.beginTransaction(spi_settings);
    digitalWriteFast(PIN_SPI_CS, LOW);
    SPI.transfer(0x10);
    SPI.transfer((uint8_t)((page_addr >> 16) & 0xFF));
    SPI.transfer((uint8_t)((page_addr >> 8) & 0xFF));
    SPI.transfer((uint8_t)(page_addr & 0xFF));
    digitalWriteFast(PIN_SPI_CS, HIGH);
    SPI.endTransaction();

    if (!wait_busy(10000)) {
        return false;
    }

    // Check Program Fail bit (bit 3 of status reg 0xC0)
    uint8_t status = get_feature(0xC0);
    return (status & 0x08) == 0;
}

bool SPINAND::erase_block(uint32_t block_addr, uint32_t pages_per_block) {
    if (pages_per_block == 0) {
        return false;
    }

    write_enable();

    uint64_t page_addr_wide = (uint64_t)block_addr * pages_per_block;
    if (page_addr_wide > 0x00FFFFFFUL) {
        return false;
    }
    uint32_t page_addr = (uint32_t)page_addr_wide;

    // Block Erase (Command 0xD8)
    SPI.beginTransaction(spi_settings);
    digitalWriteFast(PIN_SPI_CS, LOW);
    SPI.transfer(0xD8);
    SPI.transfer((uint8_t)((page_addr >> 16) & 0xFF));
    SPI.transfer((uint8_t)((page_addr >> 8) & 0xFF));
    SPI.transfer((uint8_t)(page_addr & 0xFF));
    digitalWriteFast(PIN_SPI_CS, HIGH);
    SPI.endTransaction();

    if (!wait_busy(15000)) {
        return false;
    }

    // Check Erase Fail bit (bit 2 of status reg 0xC0)
    uint8_t status = get_feature(0xC0);
    return (status & 0x04) == 0;
}
