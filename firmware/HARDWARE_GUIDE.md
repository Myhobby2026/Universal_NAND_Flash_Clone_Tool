# Teensy 4.1 Universal NAND Flash Hardware Engineering Guide

This document provides complete instructions for building, wiring, and calibrating the **Teensy 4.1 NAND Flash Hardware Programmer & Bridge**.

---

## 1. System Hardware Overview

The hardware bridge utilizes the **PJRC Teensy 4.1**, powered by the **NXP i.MX RT1062** ARM Cortex-M7 microcontroller running at **600 MHz**.
Key advantages for universal NAND memory dumping and cloning:
- **High-Speed USB 2.0 (480 Mbps)**: Eliminates serial bandwidth bottlenecks, allowing sustained transfers of 15–30+ MB/s.
- **Fast Single-Cycle GPIO**: Strobe widths down to 10 ns, supporting ONFI Timing Mode 0 through Mode 5.
- **Large Memory Buffer**: 1024 KB internal RAM allows full multi-page caching and DMA transfers without buffer underruns.

---

## 2. Bill of Materials (BOM)

| Component | Quantity | Purpose | Recommended Part / Source |
|:---|:---:|:---|:---|
| **Teensy 4.1 Board** | 1 | Microcontroller Bridge | PJRC Teensy 4.1 with headers |
| **TSOP-48 ZIF Socket** | 1 | Parallel NAND Socket | 0.5mm pitch Yamaichi / Enplas TSOP48-to-DIP48 adapter |
| **SOIC-8 / WSON-8 Socket**| 1 | SPI NAND Socket | 1.27mm pitch SOIC-8 ZIF adapter |
| **Pull-up Resistor** | 2 | R/B# & WP# pull-ups | 4.7 kΩ to 10 kΩ 0805 or 1/4W axial resistor |
| **Bypass Capacitors** | 2 | VCC power rail decoupling | 0.1 µF ceramic MLCC + 10 µF tantalum or ceramic |
| **Level Shifter (Optional)**| 2 | For 1.8V NAND flash chips | TXS0108E 8-bit bidirectional translator |
| **Breadboard / Custom PCB**| 1 | Assembly | 2.54mm pitch breadboard or proto-board |

---

## 3. Circuit Schematics & Interconnections

```
   +-----------------------------------------------------------+
   |                     TEENSY 4.1 (600MHz)                   |
   |                                                           |
   |   [USB 480Mbps] <=====================> PC Host Windows   |
   |                                                           |
   |   Pin 14 (A0) -----------> I/O 0 (TSOP Pin 29)            |
   |   Pin 15 (A1) -----------> I/O 1 (TSOP Pin 30)            |
   |   Pin 16 (A2) -----------> I/O 2 (TSOP Pin 31)   8-Bit     |
   |   Pin 17 (A3) -----------> I/O 3 (TSOP Pin 32)   Parallel |
   |   Pin 18 (A4) -----------> I/O 4 (TSOP Pin 41)   Data Bus |
   |   Pin 19 (A5) -----------> I/O 5 (TSOP Pin 42)            |
   |   Pin 20 (A6) -----------> I/O 6 (TSOP Pin 43)            |
   |   Pin 21 (A7) -----------> I/O 7 (TSOP Pin 44)            |
   |                                                           |
   |   Pin 2 -----------------> CLE   (TSOP Pin 16)            |
   |   Pin 3 -----------------> ALE   (TSOP Pin 17)            |
   |   Pin 4 -----------------> WE#   (TSOP Pin 18)            |
   |   Pin 5 -----------------> RE#   (TSOP Pin 8)             |
   |   Pin 6 -----------------> CE1#  (TSOP Pin 9)             |
   |   Pin 7 -----------------> CE2#  (TSOP Pin 10)            |
   |   Pin 8 <----------------- R/B#  (TSOP Pin 7) + 10k PU    |
   |   Pin 9 -----------------> WP#   (TSOP Pin 19)            |
   |   Pin 22 ----------------> Firmware status LED            |
   |   Pin 23 ----------------> Optional VCC switch enable     |
   |   3.3V ------------------> VCC   (TSOP Pin 12, 34)        |
   |   GND -------------------> VSS   (TSOP Pin 13, 35)        |
   +-----------------------------------------------------------+
```

The optional supply switch enable must drive a suitable regulator or MOSFET gate; never power the NAND directly from GPIO 23. SPI NAND uses Teensy Pins 10 (CS#), 11 (MOSI), 12 (MISO), and 13 (SCK). Pin 10 is not shared with the supply enable.

---

## 4. Power & Decoupling Recommendations

NAND flash memory draws significant instantaneous current spikes (up to 50–100 mA) during page programming and block erase operations.
To avoid ground bounce or VCC droop:
1. Place a **0.1 µF MLCC capacitor** as close as physically possible to TSOP Pin 12 (VCC) and Pin 13 (VSS).
2. Place a second **0.1 µF MLCC capacitor** near Pin 34 (VCC) and Pin 35 (VSS).
3. Connect a bulk **10 µF tantalum or low-ESR ceramic capacitor** between the 3.3V rail and GND near the ZIF socket.

---

## 5. Firmware Flashing Guide

### Option A: Using Arduino IDE + Teensyduino
1. Install **Arduino IDE** (v2.0 or newer) and the **Teensyduino** add-on from [pjrc.com](https://www.pjrc.com/teensy/td_download.html).
2. Open `firmware/teensy41_nand_bridge/teensy41_nand_bridge.ino`.
3. In **Tools > Board**, select **Teensy 4.1**.
4. In **Tools > USB Type**, select **Serial**.
5. In **Tools > CPU Speed**, select **600 MHz**.
6. In **Tools > Optimize**, select **Fastest**.
7. Connect your Teensy 4.1 via micro-USB and click **Upload**.

### Option B: Using PlatformIO / VS Code
1. Open the `firmware/` directory in VS Code with the **PlatformIO** extension.
2. PlatformIO will automatically detect `platformio.ini`.
3. Run the PlatformIO build and upload task:
   ```powershell
   pio run --target upload
   ```
4. The Teensy Loader will automatically flash the firmware to the board.
