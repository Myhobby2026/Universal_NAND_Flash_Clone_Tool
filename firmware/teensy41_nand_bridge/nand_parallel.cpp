#include "nand_parallel.h"

static const uint8_t BUS_PINS[8] = {
    PIN_IO0, PIN_IO1, PIN_IO2, PIN_IO3,
    PIN_IO4, PIN_IO5, PIN_IO6, PIN_IO7
};

ParallelNAND parallelNAND;

static bool address_fits_cycles(uint32_t address, uint8_t cycles) {
    if (cycles == 0 || cycles > 4) {
        return false;
    }
    if (cycles == 4) {
        return true;
    }
    return address < (1UL << (cycles * 8));
}

ParallelNAND::ParallelNAND() : active_ce_pin(PIN_CE), timing_delay_nops(4) {}

void ParallelNAND::init() {
    // Control pins configuration
    pinMode(PIN_CLE, OUTPUT);
    pinMode(PIN_ALE, OUTPUT);
    pinMode(PIN_WE, OUTPUT);
    pinMode(PIN_RE, OUTPUT);
    pinMode(PIN_CE, OUTPUT);
    pinMode(PIN_CE2, OUTPUT);
    pinMode(PIN_WP, OUTPUT);
    pinMode(PIN_VCC_EN, OUTPUT);
    pinMode(PIN_RB, INPUT_PULLUP);

    // Initial default de-asserted states (Active low controls HIGH)
    digitalWriteFast(PIN_CLE, LOW);
    digitalWriteFast(PIN_ALE, LOW);
    digitalWriteFast(PIN_WE, HIGH);
    digitalWriteFast(PIN_RE, HIGH);
    digitalWriteFast(PIN_CE, HIGH);
    digitalWriteFast(PIN_CE2, HIGH);
    digitalWriteFast(PIN_WP, HIGH);  // Disable write protect by default
    digitalWriteFast(PIN_VCC_EN, HIGH); // Power rail on

    set_bus_input();
}

void ParallelNAND::set_power(bool enable) {
    digitalWriteFast(PIN_VCC_EN, enable ? HIGH : LOW);
}

void ParallelNAND::set_ce(uint8_t ce_index) {
    // De-assert both
    digitalWriteFast(PIN_CE, HIGH);
    digitalWriteFast(PIN_CE2, HIGH);
    active_ce_pin = (ce_index == 1) ? PIN_CE2 : PIN_CE;
}

void ParallelNAND::set_timing_mode(uint8_t mode) {
    // Mode 0: slow (50ns), Mode 5: fast (10ns)
    switch (mode) {
        case 5: timing_delay_nops = 1; break;
        case 4: timing_delay_nops = 2; break;
        case 3: timing_delay_nops = 3; break;
        case 2: timing_delay_nops = 4; break;
        case 1: timing_delay_nops = 8; break;
        default: timing_delay_nops = 12; break; // Mode 0
    }
}

void ParallelNAND::set_bus_output() {
    for (int i = 0; i < 8; i++) {
        pinMode(BUS_PINS[i], OUTPUT);
    }
}

void ParallelNAND::set_bus_input() {
    for (int i = 0; i < 8; i++) {
        pinMode(BUS_PINS[i], INPUT);
    }
}

inline void ParallelNAND::strobe_delay() {
    for (uint8_t i = 0; i < timing_delay_nops; i++) {
        __asm__ volatile("nop\n\t");
    }
}

inline void ParallelNAND::write_bus(uint8_t byte) {
    for (int i = 0; i < 8; i++) {
        digitalWriteFast(BUS_PINS[i], (byte >> i) & 1);
    }
}

inline uint8_t ParallelNAND::read_bus() {
    uint8_t byte = 0;
    for (int i = 0; i < 8; i++) {
        if (digitalReadFast(BUS_PINS[i])) {
            byte |= (1 << i);
        }
    }
    return byte;
}

void ParallelNAND::write_cmd(uint8_t cmd) {
    set_bus_output();
    digitalWriteFast(PIN_ALE, LOW);
    digitalWriteFast(PIN_CLE, HIGH);
    digitalWriteFast(active_ce_pin, LOW);

    write_bus(cmd);

    digitalWriteFast(PIN_WE, LOW);
    strobe_delay();
    digitalWriteFast(PIN_WE, HIGH);
    strobe_delay();

    digitalWriteFast(PIN_CLE, LOW);
    digitalWriteFast(active_ce_pin, HIGH);
}

void ParallelNAND::write_addr(uint8_t addr) {
    set_bus_output();
    digitalWriteFast(PIN_CLE, LOW);
    digitalWriteFast(PIN_ALE, HIGH);
    digitalWriteFast(active_ce_pin, LOW);

    write_bus(addr);

    digitalWriteFast(PIN_WE, LOW);
    strobe_delay();
    digitalWriteFast(PIN_WE, HIGH);
    strobe_delay();

    digitalWriteFast(PIN_ALE, LOW);
    digitalWriteFast(active_ce_pin, HIGH);
}

bool ParallelNAND::wait_ready_busy(uint32_t timeout_us) {
    uint32_t start = micros();
    // Allow tWB (wait for R/B to fall low if active)
    delayNanoseconds(100);
    while (!digitalReadFast(PIN_RB)) {
        if ((micros() - start) > timeout_us) {
            return false; // Timeout
        }
    }
    return true;
}

bool ParallelNAND::reset() {
    write_cmd(0xFF);
    return wait_ready_busy(50000); // 50ms max reset time
}

uint8_t ParallelNAND::read_status() {
    write_cmd(0x70);

    set_bus_input();
    digitalWriteFast(active_ce_pin, LOW);

    digitalWriteFast(PIN_RE, LOW);
    strobe_delay();
    uint8_t status = read_bus();
    digitalWriteFast(PIN_RE, HIGH);

    digitalWriteFast(active_ce_pin, HIGH);
    return status;
}

void ParallelNAND::read_id(uint8_t* dest, uint8_t count) {
    write_cmd(0x90);
    write_addr(0x00);

    set_bus_input();
    digitalWriteFast(active_ce_pin, LOW);

    for (uint8_t i = 0; i < count; i++) {
        digitalWriteFast(PIN_RE, LOW);
        strobe_delay();
        dest[i] = read_bus();
        digitalWriteFast(PIN_RE, HIGH);
        strobe_delay();
    }

    digitalWriteFast(active_ce_pin, HIGH);
}

bool ParallelNAND::read_onfi(uint8_t* dest, uint16_t length) {
    write_cmd(0xEC);
    write_addr(0x00);

    if (!wait_ready_busy(10000)) {
        return false;
    }

    set_bus_input();
    digitalWriteFast(active_ce_pin, LOW);

    for (uint16_t i = 0; i < length; i++) {
        digitalWriteFast(PIN_RE, LOW);
        strobe_delay();
        dest[i] = read_bus();
        digitalWriteFast(PIN_RE, HIGH);
        strobe_delay();
    }

    digitalWriteFast(active_ce_pin, HIGH);
    return true;
}

bool ParallelNAND::read_page(
    uint32_t page_addr,
    uint16_t col_addr,
    uint8_t* buffer,
    uint16_t length,
    uint8_t col_cycles,
    uint8_t row_cycles
) {
    if (col_cycles == 0 || col_cycles > 2 ||
        !address_fits_cycles(page_addr, row_cycles)) {
        return false;
    }

    // Command 0x00: Read Mode
    write_cmd(0x00);

    // Column address cycles
    if (col_cycles >= 1) write_addr((uint8_t)(col_addr & 0xFF));
    if (col_cycles >= 2) write_addr((uint8_t)((col_addr >> 8) & 0xFF));

    // Row / Page address cycles
    if (row_cycles >= 1) write_addr((uint8_t)(page_addr & 0xFF));
    if (row_cycles >= 2) write_addr((uint8_t)((page_addr >> 8) & 0xFF));
    if (row_cycles >= 3) write_addr((uint8_t)((page_addr >> 16) & 0xFF));
    if (row_cycles >= 4) write_addr((uint8_t)((page_addr >> 24) & 0xFF));

    // Large-page NAND requires a confirm command; small-page NAND does not.
    if (col_cycles >= 2) {
        write_cmd(0x30);
    }

    // Wait for internal array to cache transfer (tR)
    if (!wait_ready_busy(100000)) {
        return false;
    }

    set_bus_input();
    digitalWriteFast(active_ce_pin, LOW);

    for (uint16_t i = 0; i < length; i++) {
        digitalWriteFast(PIN_RE, LOW);
        strobe_delay();
        buffer[i] = read_bus();
        digitalWriteFast(PIN_RE, HIGH);
        strobe_delay();
    }

    digitalWriteFast(active_ce_pin, HIGH);
    return true;
}

bool ParallelNAND::write_page(
    uint32_t page_addr,
    uint16_t col_addr,
    const uint8_t* buffer,
    uint16_t length,
    uint8_t col_cycles,
    uint8_t row_cycles
) {
    if (col_cycles == 0 || col_cycles > 2 ||
        !address_fits_cycles(page_addr, row_cycles)) {
        return false;
    }

    // Command 0x80: Page Program Setup
    write_cmd(0x80);

    // Column address cycles
    if (col_cycles >= 1) write_addr((uint8_t)(col_addr & 0xFF));
    if (col_cycles >= 2) write_addr((uint8_t)((col_addr >> 8) & 0xFF));

    // Row / Page address cycles
    if (row_cycles >= 1) write_addr((uint8_t)(page_addr & 0xFF));
    if (row_cycles >= 2) write_addr((uint8_t)((page_addr >> 8) & 0xFF));
    if (row_cycles >= 3) write_addr((uint8_t)((page_addr >> 16) & 0xFF));
    if (row_cycles >= 4) write_addr((uint8_t)((page_addr >> 24) & 0xFF));

    // Stream data into cache
    set_bus_output();
    digitalWriteFast(active_ce_pin, LOW);

    for (uint16_t i = 0; i < length; i++) {
        write_bus(buffer[i]);
        digitalWriteFast(PIN_WE, LOW);
        strobe_delay();
        digitalWriteFast(PIN_WE, HIGH);
        strobe_delay();
    }

    digitalWriteFast(active_ce_pin, HIGH);

    // Command 0x10: Page Program Execute
    write_cmd(0x10);

    // Wait for programming (tPROG, up to 3ms)
    if (!wait_ready_busy(5000)) {
        return false;
    }

    // Check status register (bit 0 == 0 means PASS)
    uint8_t st = read_status();
    return (st & 0x01) == 0;
}

bool ParallelNAND::erase_block(
    uint32_t block_addr,
    uint32_t pages_per_block,
    uint8_t row_cycles
) {
    if (pages_per_block == 0 || row_cycles == 0 || row_cycles > 4) {
        return false;
    }

    // Calculate starting row address for this block
    uint64_t row_addr_wide = (uint64_t)block_addr * pages_per_block;
    if (row_addr_wide > 0xFFFFFFFFUL) {
        return false;
    }
    uint32_t row_addr = (uint32_t)row_addr_wide;
    if (!address_fits_cycles(row_addr, row_cycles)) {
        return false;
    }

    // Command 0x60: Block Erase Setup
    write_cmd(0x60);

    // Row address cycles only
    if (row_cycles >= 1) write_addr((uint8_t)(row_addr & 0xFF));
    if (row_cycles >= 2) write_addr((uint8_t)((row_addr >> 8) & 0xFF));
    if (row_cycles >= 3) write_addr((uint8_t)((row_addr >> 16) & 0xFF));
    if (row_cycles >= 4) write_addr((uint8_t)((row_addr >> 24) & 0xFF));

    // Command 0xD0: Block Erase Execute
    write_cmd(0xD0);

    // Wait for erase (tBERS, up to 10ms)
    if (!wait_ready_busy(15000)) {
        return false;
    }

    // Check status register
    uint8_t st = read_status();
    return (st & 0x01) == 0;
}

void ParallelNAND::probe_signals(bool& rb, bool& ce, bool& cle, bool& ale) {
    rb = digitalReadFast(PIN_RB);
    ce = digitalReadFast(active_ce_pin);
    cle = digitalReadFast(PIN_CLE);
    ale = digitalReadFast(PIN_ALE);
}
