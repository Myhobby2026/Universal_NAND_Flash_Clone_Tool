#ifndef NAND_PARALLEL_H
#define NAND_PARALLEL_H

#include <Arduino.h>
#include "config.h"

class ParallelNAND {
public:
    ParallelNAND();

    void init();
    void set_timing_mode(uint8_t mode);
    void set_ce(uint8_t ce_index);
    void set_power(bool enable);

    bool reset();
    uint8_t read_status();
    void read_id(uint8_t* dest, uint8_t count = 5);
    bool read_onfi(uint8_t* dest, uint16_t length = 256);

    bool read_page(
        uint32_t page_addr,
        uint16_t col_addr,
        uint8_t* buffer,
        uint16_t length,
        uint8_t col_cycles = 2,
        uint8_t row_cycles = 3
    );

    bool write_page(
        uint32_t page_addr,
        uint16_t col_addr,
        const uint8_t* buffer,
        uint16_t length,
        uint8_t col_cycles = 2,
        uint8_t row_cycles = 3
    );

    bool erase_block(
        uint32_t block_addr,
        uint32_t pages_per_block = 64,
        uint8_t row_cycles = 3
    );

    bool wait_ready_busy(uint32_t timeout_us = 1000000);

    // Pin probe for diagnostics
    void probe_signals(bool& rb, bool& ce, bool& cle, bool& ale);

private:
    uint8_t active_ce_pin;
    uint8_t timing_delay_nops;

    void set_bus_output();
    void set_bus_input();
    inline void write_bus(uint8_t byte);
    inline uint8_t read_bus();
    inline void strobe_delay();

    void write_cmd(uint8_t cmd);
    void write_addr(uint8_t addr);
};

extern ParallelNAND parallelNAND;

#endif // NAND_PARALLEL_H
