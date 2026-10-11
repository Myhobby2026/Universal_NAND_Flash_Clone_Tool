# Universal NAND Flash Clone Tool - User Manual & Operator Guide

---

## 1. Introduction

The **Universal NAND Flash Clone Tool** is an industrial-grade desktop application for Windows engineered for reading, programming, verifying, cloning, and reverse-engineering NAND Flash memory ICs. Operating in conjunction with the **Teensy 4.1** 600 MHz hardware bridge, it achieves blazing-fast throughput over High-Speed USB (480 Mbps) with support for standard Parallel NAND (TSOP-48, BGA-63) and SPI NAND (SOIC-8, WSON-8, BGA-24).

---

## 2. Quick Start

### 2.1 Starting the Application
Launch the tool from PowerShell or Command Prompt:
```powershell
python run.py
```
Or directly via the Python package entrypoint:
```powershell
python -m src.app
```

### 2.2 Selecting the Bridge Mode
At the top header bar, you can choose between two modes:
1. **Virtual Simulation Bridge (Demo)**: Emulates a high-speed Teensy 4.1 connected to a 512MB Micron ONFI SLC NAND flash preloaded with realistic U-Boot, Linux Kernel, SquashFS, and UBI partitions. Ideal for demonstrations, software testing, and partition carving without hardware.
2. **Teensy 4.1 Hardware (USB Serial)**: Connects to your physical Teensy 4.1 microcontroller. Select the corresponding COM port and click **Connect**.

---

## 3. Core Operational Workflows

### 3.1 Chip Auto-Detection
Click the green **⚡ Auto-Detect Chip** button on the toolbar. The tool will execute:
1. Reset command (`0xFF`).
2. ONFI Parameter Page read (`0xEC`).
3. If ONFI signature `'ONFI'` is detected, it validates the triple-redundant CRC-16 parameter page and extracts page size, spare size, pages/block, and timing modes.
4. If non-ONFI, it issues JEDEC Read ID (`0x90` or SPI `0x9F`), decodes the 5-byte identifier, and checks the database of over 150+ chips.

The **Chip Information Card** and **NAND Block Visualizer** immediately adjust to the chip's geometry.

---

### 3.2 Dumping Flash (Chip → File)
1. In the left sidebar, ensure **Include OOB / Spare Area** is checked if you want a complete forensic dump (recommended for data recovery, reverse-engineering, and ECC analysis).
2. Click **📥 Read / Dump Flash (Chip → File)**.
3. Select the destination file path (`.bin`).
4. The tool streams pages from the bridge. The **Throughput Speedometer** displays real-time speed in MB/s, ETA countdown, and progress.
5. In the **Block Visualizer**, blocks turn **Emerald Green** as they are read.
6. Upon completion, the tool calculates and reports the **MD5** and **SHA-256** checksums of the dumped image.

---

### 3.3 Writing / Programming Flash (File → Chip)
1. Ensure **Skip Factory Bad Blocks** is enabled to prevent overwriting factory bad block tables.
2. Click **📤 Write / Flash (File → Chip)**.
3. Select your input image file (`.bin`, `.img`, or `.raw`).
4. The tool automatically detects whether the file includes OOB spare bytes based on file size.
5. Blocks are erased if **Auto-Erase Before Writing** is enabled, programmed page-by-page, and verified via Status Register (`0x70`).
6. Blocks turn **Vibrant Cyan** on the visualizer as programming completes.

---

### 3.4 Scanning Bad Blocks (BBT)
Click **🔍 Scan Bad Block Table (BBT)**.
The tool rapidly inspects byte 0 (or byte 5 for small page chips) in the spare area of Page 0 and Page 1 of every block. Factory defective blocks are identified and highlighted in **Crimson Red** on the Block Map.

---

### 3.5 Hex & OOB Spare Inspector
Switch to the **🔬 Hex & OOB Inspector** tab:
- **Block & Page Navigation:** Select any Block (e.g. Block 4) and Page (e.g. Page 0).
- **Color Coding:**
  - **Main Data Area (0..2047)** is displayed with blue/cyan text.
  - **Spare/OOB Area (2048..2111)** is highlighted with an **amber/gold background**, allowing you to inspect bad block markers and ECC parity bytes at a glance.
- **Check ECC:** Computes SmartMedia/Samsung Hamming parity on the active sector and verifies single-bit correctability.
- **Export Page:** Saves the raw binary of the currently inspected page to disk.

---

### 3.6 Partition & Firmware Scanner
Switch to the **📦 Partition & Firmware Scanner** tab:
1. Click **Scan Dump File (.bin)...** and select a raw flash dump (or inspect a newly completed dump).
2. The scanner parses signatures across block boundaries:
   - **U-Boot uImage** headers (Image name, architecture, load address, entry point).
   - **Device Tree Blobs (DTB) / FIT images** (`0xD00DFEED`).
   - **Linux ARM zImage** kernels (`0x016F2818`).
   - **SquashFS Root Filesystems** (v3.x / v4.x, block sizes, inode counts).
   - **UBI Containers** (`UBI#` erase counter headers, volume descriptors).
   - **JFFS2** log-structured file systems.
   - **Ext2/3/4** superblocks.
3. Select any discovered partition and click **Extract Partition...** to carve the filesystem image directly to disk!

---

### 3.7 Teensy 4.1 Pinout & Live Signals
Switch to the **🔌 Teensy 4.1 Pinout & Live Signals** tab:
- Consult the complete TSOP-48 and SPI NAND wiring connection table.
- Click **Probe Live Bus Signals** to query the physical logic levels of the **R/B#**, **CE#**, **CLE**, and **ALE** pins in real-time.
- Toggle the **VCC: 3.3V** power control button or change ONFI **Timing Modes (Mode 0 to Mode 5)**.

