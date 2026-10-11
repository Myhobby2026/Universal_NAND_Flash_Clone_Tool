# Universal NAND Flash Memory Clone Tool (Professional Grade)

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6%20Fluent-cyan.svg)](https://riverbankcomputing.com/software/pyqt/)
[![Hardware](https://img.shields.io/badge/Hardware-Teensy%204.1%20(600MHz)-orange.svg)](https://www.pjrc.com/store/teensy41.html)
[![Protocol](https://img.shields.io/badge/USB-High--Speed%20480%20Mbps-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/tests-15%20passed-success.svg)]()

A complete, professional-grade Windows desktop application and hardware programmer for cloning, dumping, programming, verifying, and reverse-engineering **NAND Flash Memory ICs** (Parallel TSOP-48 / BGA-63 and SPI/QSPI NAND), utilizing the **PJRC Teensy 4.1** (600 MHz ARM Cortex-M7) as an ultra-fast hardware bridge.

---

## ⚡ Key Architectural Features

- **🚀 Ultra-Fast USB 2.0 High-Speed (480 Mbps)**:
  - Built for sustained multi-megabyte/second transfers (15–30+ MB/s) with double-buffered bulk streaming.
  - Sub-20ns bus strobes supporting ONFI Timing Modes 0 through 5.
- **🗺️ Interactive 2D NAND Visual Block Map**:
  - Live color-coded grid visualizing good, read, programmed, erased, bitflipped, and factory bad blocks.
  - Hover tooltips and instant click-to-inspect navigation to the Hex Viewer.
- **🔬 Dual-Zone Hex & OOB Spare Inspector**:
  - Distinct visual separation and color highlighting of **Main Page Data** vs **Spare / OOB Area** (bad block markers, ECC parity bytes).
  - Built-in SmartMedia / Samsung 1-bit Hamming ECC calculator with bitflip location and automatic correction.
- **📦 Firmware & Filesystem Signature Scanner**:
  - Auto-detects and extracts embedded partitions from raw flash dumps: **UBI / UBIFS**, **SquashFS**, **U-Boot uImage**, **Device Tree Blobs (DTB) / FIT images**, **ARM zImage**, **JFFS2**, and **Ext4**.
- **🧠 Universal ONFI & Non-ONFI Database**:
  - Full ONFI 1.0–4.0 Parameter Page parser with CRC-16 verification and triple-redundancy majority recovery.
  - 150+ chip database for Samsung, Toshiba / Kioxia, Micron, SK Hynix, Winbond, Macronix, Spansion, and GigaDevice plus dynamic 5-byte ID decoding.
- **🔌 Hardware Bridge Live Logic Analyzer**:
  - Live signal probing of `R/B#`, `CE#`, `CLE`, `ALE` logic levels, 3.3V power toggle, and pinout wiring tables.
- **🧪 Virtual Simulation Mode**:
  - Includes a full software bridge emulator with realistic flash memory, bootloader headers, kernel images, and bad blocks for immediate testing without hardware!

---

## 🏗️ Hardware Architecture & Pinout (Teensy 4.1)

```
                       TEENSY 4.1 (600 MHz Cortex-M7)
                        +----------------------------+
       USB 480Mbps <====| Native USB High-Speed Port |
                        |                            |
       TSOP-48 Pin 29 <-| Pin 14 (A0) - I/O 0        |
       TSOP-48 Pin 30 <-| Pin 15 (A1) - I/O 1        |
       TSOP-48 Pin 31 <-| Pin 16 (A2) - I/O 2  8-Bit |
       TSOP-48 Pin 32 <-| Pin 17 (A3) - I/O 3  Bus   |
       TSOP-48 Pin 41 <-| Pin 18 (A4) - I/O 4        |
       TSOP-48 Pin 42 <-| Pin 19 (A5) - I/O 5        |
       TSOP-48 Pin 43 <-| Pin 20 (A6) - I/O 6        |
       TSOP-48 Pin 44 <-| Pin 21 (A7) - I/O 7        |
                        |                            |
       TSOP-48 Pin 16 <-| Pin 2 - CLE (Command)      |
       TSOP-48 Pin 17 <-| Pin 3 - ALE (Address)      |
       TSOP-48 Pin 18 <-| Pin 4 - WE# (Write Strobe) |
       TSOP-48 Pin 8  <-| Pin 5 - RE# (Read Strobe)  |
       TSOP-48 Pin 9  <-| Pin 6 - CE1# (Chip Enable) |
       TSOP-48 Pin 10 <-| Pin 7 - CE2# (Chip Enable) |
       TSOP-48 Pin 7  ->| Pin 8 - R/B# (Ready/Busy)  | (Requires 10k pull-up)
       TSOP-48 Pin 19 <-| Pin 9 - WP# (Write Protect)|
       TSOP-48 VCC    <-| 3.3V Core / I/O Rail       | (0.1µF + 10µF bypass)
                        +----------------------------+
```

For complete wiring instructions, see [`firmware/WIRING_AND_PINOUT.md`](firmware/WIRING_AND_PINOUT.md).

---

## 🚀 Quick Start Guide

### 1. Requirements
- Windows 10 / 11 (64-bit)
- Python 3.10+
- Teensy 4.1 board (optional for simulation mode)

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Launch the Application
```powershell
python run.py
```

### 4. Build a Windows Executable
Double-click `build_exe.bat` or run it from Command Prompt. The script installs
the application and PyInstaller dependencies, then builds a single-file GUI
executable at `dist/Universal NAND Flash Clone Tool.exe`. The NAND icon asset is
embedded in the executable and bundled for the application window.

### 5. Run Automated Test Suite
```powershell
python -m pytest tests/ -v
```

---

## 🛠️ Flashing the Teensy 4.1 Firmware

The complete C++ firmware source code is located in `firmware/teensy41_nand_bridge/`.

### Via Arduino IDE:
1. Open `firmware/teensy41_nand_bridge/teensy41_nand_bridge.ino` in Arduino IDE.
2. Select **Board: Teensy 4.1**, **USB Type: Serial**, **CPU Speed: 600 MHz**, **Optimize: Fastest**.
3. Click **Upload**.

### Via PlatformIO:
```powershell
cd firmware
pio run --target upload
```

---

## 📖 Documentation Index

- **[Operator User Manual](docs/USER_MANUAL.md)**: Step-by-step dumping, writing, erasing, partition extraction, and ECC correction tutorials.
- **[Hardware Engineering Guide](firmware/HARDWARE_GUIDE.md)**: Schematics, bill of materials, ZIF sockets, level shifters for 1.8V NANDs, and decoupling capacitor rules.
- **[Binary Protocol Specification](docs/PROTOCOL_SPEC.md)**: Framed binary command packets, CRC-16 algorithms, and response codes.
- **[Pinout & Wiring Guide](firmware/WIRING_AND_PINOUT.md)**: TSOP-48 and SPI NAND socket to Teensy 4.1 pin mappings.

---

## 📄 License
MIT License. Created for industrial electronics engineering, embedded security research, and data recovery professionals.
