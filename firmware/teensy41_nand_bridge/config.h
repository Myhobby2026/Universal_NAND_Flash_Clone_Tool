#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// ==============================================================================
// TEENSY 4.1 HARDWARE BRIDGE CONFIGURATION
// Target MCU: NXP i.MX RT1062 (600 MHz ARM Cortex-M7, 480 Mbps High Speed USB)
// ==============================================================================

#define FW_VERSION_MAJOR 1
#define FW_VERSION_MINOR 4
#define FW_VERSION_PATCH 0
#define FW_BOARD_NAME    "Teensy 4.1 Universal NAND Bridge"

// Status indicator LED
#define PIN_LED_STATUS   22

// ==============================================================================
// PARALLEL NAND FLASH PINOUT (TSOP-48 / BGA-63 / Socket)
// 8-Bit Data Bus (I/O 0 - I/O 7) mapped to fast Teensy 4.1 GPIO pins
// ==============================================================================
#define PIN_IO0          14   // A0
#define PIN_IO1          15   // A1
#define PIN_IO2          16   // A2
#define PIN_IO3          17   // A3
#define PIN_IO4          18   // A4
#define PIN_IO5          19   // A5
#define PIN_IO6          20   // A6
#define PIN_IO7          21   // A7

// Control Signals (Active-Low controls are held HIGH by default)
#define PIN_CLE          2    // Command Latch Enable (High = Command cycle)
#define PIN_ALE          3    // Address Latch Enable (High = Address cycle)
#define PIN_WE           4    // Write Enable (Active Low strobe)
#define PIN_RE           5    // Read Enable (Active Low strobe)
#define PIN_CE           6    // Chip Enable 1 (Active Low)
#define PIN_CE2          7    // Chip Enable 2 (Active Low, for dual-die chips)
#define PIN_RB           8    // Ready / Busy# (Active Low open-drain with pullup)
#define PIN_WP           9    // Write Protect# (Active Low)

// Power rail switch (MOSFET or regulator enable pin)
#define PIN_VCC_EN       23   // High = power switch/regulator enable

// ==============================================================================
// SPI / QSPI NAND FLASH PINOUT (WSON-8 / SOIC-8/16 / BGA-24)
// Hardware SPI1 / SPI0 interface on Teensy 4.1
// ==============================================================================
#define PIN_SPI_CS       10   // Chip Select (Active Low)
#define PIN_SPI_MOSI     11   // Master Out Slave In (IO0 / DI)
#define PIN_SPI_MISO     12   // Master In Slave Out (IO1 / DO)
#define PIN_SPI_SCK      13   // SPI0 clock (up to 30 MHz configured)
#define PIN_SPI_WP       9    // Write Protect / IO2
#define PIN_SPI_HOLD     8    // Hold / Reset / IO3

// Default bus timing delay in nanoseconds / loop nops (Mode 0 to Mode 5)
// Mode 0: tRP/tWP = 50ns, Mode 5: tRP/tWP = 10ns
#define DEFAULT_TIMING_MODE 0

#endif // CONFIG_H
