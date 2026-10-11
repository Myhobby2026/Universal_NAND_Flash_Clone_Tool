# Teensy 4.1 Universal NAND Bridge - Wiring & Pinout Guide

This document details the exact hardware connections between the **Teensy 4.1** board and NAND Flash memory chips (Parallel TSOP-48 and SPI NAND).

---

## 1. Parallel NAND Flash Pinout (TSOP-48 Standard)

Standard 48-pin Thin Small Outline Package (TSOP-I) used across Samsung, Kioxia/Toshiba, Micron, SK Hynix, Winbond, Macronix, Spansion:

| TSOP-48 Pin | Signal Name | Teensy 4.1 Pin | Description | Notes |
|:---:|:---:|:---:|:---|:---|
| **7** | **R/B#** | **Pin 8** | Ready / Busy Output | Requires 10kΩ pull-up to 3.3V |
| **8** | **RE#** | **Pin 5** | Read Enable Input | Active Low strobe |
| **9** | **CE#** | **Pin 6** | Chip Enable 1 Input | Active Low |
| **10** | **NC / CE2#**| **Pin 7** | Chip Enable 2 (Dual Die)| Active Low |
| **12** | **VCC** | **3.3V** | Core Power (3.3V) | Decouple with 0.1µF + 10µF |
| **13** | **VSS** | **GND** | Ground | Ground return |
| **16** | **CLE** | **Pin 2** | Command Latch Enable | High during Command cycle |
| **17** | **ALE** | **Pin 3** | Address Latch Enable | High during Address cycle |
| **18** | **WE#** | **Pin 4** | Write Enable Input | Active Low strobe |
| **19** | **WP#** | **Pin 9** | Write Protect Input | Pull HIGH to enable writing |
| **29** | **I/O 0** | **Pin 14 (A0)**| Data Bus Bit 0 | Bi-directional |
| **30** | **I/O 1** | **Pin 15 (A1)**| Data Bus Bit 1 | Bi-directional |
| **31** | **I/O 2** | **Pin 16 (A2)**| Data Bus Bit 2 | Bi-directional |
| **32** | **I/O 3** | **Pin 17 (A3)**| Data Bus Bit 3 | Bi-directional |
| **34** | **VCC** | **3.3V** | I/O Power Supply | Decouple with 0.1µF |
| **35** | **VSS** | **GND** | Ground | Ground return |
| **41** | **I/O 4** | **Pin 18 (A4)**| Data Bus Bit 4 | Bi-directional |
| **42** | **I/O 5** | **Pin 19 (A5)**| Data Bus Bit 5 | Bi-directional |
| **43** | **I/O 6** | **Pin 20 (A6)**| Data Bus Bit 6 | Bi-directional |
| **44** | **I/O 7** | **Pin 21 (A7)**| Data Bus Bit 7 | Bi-directional |

*Note: Pins marked NC (No Connect) on TSOP-48 can be left floating.*
*If a switched NAND supply is used, connect its regulator/MOSFET enable to Teensy Pin 23 (`PIN_VCC_EN`); do not connect the NAND VCC rail directly to this GPIO.*

---

## 2. SPI / Quad-SPI NAND Flash Pinout (WSON-8 / SOIC-8 / SOIC-16)

For modern SPI NAND chips (Winbond W25N, GigaDevice GD5F, Macronix MX35, Micron MT29F...SPI):

| SPI NAND Pin (8-pin) | Signal Name | Teensy 4.1 Pin | Description |
|:---:|:---:|:---:|:---|
| **1** | **CS#** | **Pin 10** | Chip Select (Active Low) |
| **2** | **SO / IO1** | **Pin 12 (MISO)** | Serial Data Output |
| **3** | **WP# / IO2** | **Pin 9** | Write Protect / Quad IO2 |
| **4** | **VSS** | **GND** | Ground |
| **5** | **SI / IO0** | **Pin 11 (MOSI)** | Serial Data Input |
| **6** | **SCK** | **Pin 13** | SPI0 Serial Clock (configured at 30MHz) |
| **7** | **HOLD# / IO3** | **Pin 8** | Hold / Reset / Quad IO3 |
| **8** | **VCC** | **3.3V** | Power Supply (3.3V) |

Pin 10 is SPI chip select and must not be used as the switched supply-enable signal. Pin 23 is reserved for that enable; Pin 22 is the firmware status LED.

---

## 3. Essential Hardware Circuit Design Rules

1. **R/B# Pull-up Resistor**:
   The R/B# pin of NAND flash is an **open-drain** output. You MUST place a **4.7kΩ to 10kΩ pull-up resistor** between TSOP-48 Pin 7 and 3.3V (even though Teensy internal pullups are enabled, an external pullup ensures sharp 10ns rise times).

2. **Decoupling Capacitors**:
   Place a **0.1µF ceramic capacitor** and a **10µF tantalum or MLCC capacitor** directly across TSOP-48 VCC (Pin 12/34) and VSS (Pin 13/35) as close to the socket pins as possible to prevent voltage droops during high-current page program cycles.

3. **1.8V NAND Chips**:
   If dumping 1.8V NAND chips (e.g. mobile devices), **DO NOT CONNECT DIRECTLY TO 3.3V**. Use bidirectional level translator ICs (such as **TXS0108E** or **74AVC8T245**) powered by 3.3V on the Teensy side and 1.8V on the NAND side.
