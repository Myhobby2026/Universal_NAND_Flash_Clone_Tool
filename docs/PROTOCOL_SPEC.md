# Teensy 4.1 Universal NAND Bridge - Binary Framing Protocol Specification

**Document Version:** 1.4.0  
**Transport:** USB 2.0 High-Speed CDC (480 Mbps)  
**Host Framing Sync:** `0x55, 0xAA`  
**Bridge Framing Sync:** `0xAA, 0x55`  
**Checksum:** CCITT-FALSE CRC-16 (Polynomial `0x1021`, Initial `0xFFFF`)

The current firmware implements parallel x8 and standard SPI NAND. Parallel x16
and dual/quad SPI modes are explicitly rejected; their enum values do not imply
that the hardware driver implements those bus widths.

---

## 1. Frame Structure

All packets between Host and Teensy 4.1 bridge follow strict binary framing with 8-byte fixed headers.

### 1.1 Host-to-Device Command Packet
```
+---------------+---------------+---------------+---------------+---------------+---------------+---------------+---------------+-------------------------+
| Byte 0        | Byte 1        | Byte 2        | Byte 3        | Byte 4        | Byte 5        | Byte 6        | Byte 7        | Bytes 8 .. (8 + Len - 1)|
| MAGIC_HOST_0  | MAGIC_HOST_1  | CMD           | SEQ           | LEN_LOW       | LEN_HIGH      | CRC_LOW       | CRC_HIGH      | PAYLOAD                 |
| (0x55)        | (0xAA)        | (uint8)       | (uint8)       | (uint8)       | (uint8)       | (uint8)       | (uint8)       | (Variable Length)       |
+---------------+---------------+---------------+---------------+---------------+---------------+---------------+---------------+-------------------------+
```
- **MAGIC**: Fixed sync word `[0x55, 0xAA]`.
- **CMD**: Command identifier byte (see Command Table).
- **SEQ**: Incremental rolling sequence tag `0..255` for packet tracking.
- **LEN**: 16-bit Little-Endian payload length (`0..65535`).
- **CRC**: 16-bit Little-Endian CCITT CRC-16 computed over `[CMD, SEQ, LEN_L, LEN_H]` followed by `PAYLOAD` bytes.

### 1.2 Device-to-Host Response Packet
```
+---------------+---------------+---------------+---------------+---------------+---------------+---------------+---------------+-------------------------+
| Byte 0        | Byte 1        | Byte 2        | Byte 3        | Byte 4        | Byte 5        | Byte 6        | Byte 7        | Bytes 8 .. (8 + Len - 1)|
| MAGIC_DEV_0   | MAGIC_DEV_1   | STATUS        | SEQ           | LEN_LOW       | LEN_HIGH      | CRC_LOW       | CRC_HIGH      | PAYLOAD                 |
| (0xAA)        | (0x55)        | (uint8)       | (uint8)       | (uint8)       | (uint8)       | (uint8)       | (uint8)       | (Variable Length)       |
+---------------+---------------+---------------+---------------+---------------+---------------+---------------+---------------+-------------------------+
```
- **MAGIC**: Fixed response sync word `[0xAA, 0x55]`.
- **STATUS**: Execution result code (`0x00 = OK`, etc.).
- **SEQ**: Echoed sequence tag matching the command.
- **LEN**: 16-bit Little-Endian payload length.
- **CRC**: 16-bit Little-Endian CRC-16 over `[STATUS, SEQ, LEN_L, LEN_H]` + `PAYLOAD`.

---

## 2. Status Codes

| Code | Identifier | Description |
|:---:|:---|:---|
| `0x00` | `STATUS_OK` | Command succeeded |
| `0x01` | `STATUS_ERR_GENERIC` | Generic operational fault |
| `0x02` | `STATUS_ERR_TIMEOUT` | Ready/Busy or peripheral timeout |
| `0x03` | `STATUS_ERR_BUSY` | Hardware engine currently busy |
| `0x04` | `STATUS_ERR_BAD_CRC` | Frame CRC check failed |
| `0x05` | `STATUS_ERR_INVALID_PARAM` | Invalid address, length, or parameters |
| `0x06` | `STATUS_ERR_FAIL` | Flash program or erase operation failed (Status 0x70 bit 0 != 0) |
| `0x07` | `STATUS_ERR_WRITE_PROTECTED`| Hardware write-protection is asserted |
| `0x08` | `STATUS_ERR_NOT_SUPPORTED` | Command not supported by current bus mode |

---

## 3. Command Definitions & Payloads

### 3.1 `CMD_PING (0x01)`
- **Payload Sent:** None (Len = 0)
- **Response Payload:** None (Len = 0)
- **Purpose:** Verifies hardware bridge connection and sync.

### 3.2 `CMD_GET_FW_INFO (0x02)`
- **Payload Sent:** None
- **Response Payload:**
  - `uint8 major`: Major firmware version (e.g. 1)
  - `uint8 minor`: Minor firmware version (e.g. 4)
  - `uint8 patch`: Patch version (e.g. 0)
  - `uint16 mcu_freq_mhz`: Core clock in MHz (e.g. 600)
  - `uint16 capabilities`: Bitmask of supported buses and features
  - `char board_name[]`: ASCII string identifier

### 3.3 `CMD_SET_BUS_CONFIG (0x03)`
- **Payload Sent (4 bytes):**
  - `uint8 bus_type`: `0x01` = Parallel x8, `0x02` = Parallel x16, `0x03` = SPI, `0x05` = Quad SPI
  - `uint8 timing_mode`: `0` = Mode 0 (50ns), `1` = Mode 1, `2` = Mode 2, `3` = Mode 3, `4` = Mode 4, `5` = Mode 5 (10ns)
  - `uint8 ce_index`: `0` = CE1, `1` = CE2 (for dual die chips)
  - `uint8 vcc_en`: `1` = Power ON (3.3V), `0` = Power OFF
- **Response Payload:** None

### 3.4 `CMD_RESET_CHIP (0x04)`
- **Payload Sent:** None
- **Response Payload:** None
- **Hardware Action:** Sends `0xFF` reset command to Parallel or SPI NAND, awaits R/B# high.

### 3.5 `CMD_READ_ID (0x05)`
- **Payload Sent:** None
- **Response Payload:** 3 to 5 bytes containing Manufacturer ID, Device Code, and 3rd/4th/5th decode bytes.

### 3.6 `CMD_READ_ONFI (0x06)`
- **Payload Sent:** None
- **Response Payload:** 256 or 768 bytes containing the ONFI parameter page table.

### 3.7 `CMD_READ_PAGE (0x10)`
- **Payload Sent (8 or 10 bytes):**
  - `uint32 page_addr`: Physical page/row index
  - `uint16 col_addr`: Column offset inside the page (0 for start of data, or page_size for spare)
  - `uint16 read_len`: Number of bytes to transfer (e.g. 2048, 2112, 4320)
  - Optional `uint8 col_cycles`, `uint8 row_cycles`: NAND address-cycle counts; omitted legacy values default to 2 and 3.
- **Response Payload:** `read_len` bytes of raw data read directly from NAND memory.

### 3.8 `CMD_WRITE_PAGE (0x11)`
- **Payload Sent (8 + data_len or 10 + data_len bytes):**
  - `uint32 page_addr`: Physical page/row index
  - `uint16 col_addr`: Column offset (usually 0)
  - `uint16 data_len`: Number of bytes to write
  - `uint8 data[]`: Raw byte buffer to program into the flash cell
  - Optional `uint8 col_cycles`, `uint8 row_cycles`: NAND address-cycle counts; omitted legacy values default to 2 and 3.
- **Response Payload:** None (Returns `STATUS_OK` or `STATUS_ERR_FAIL`)

### 3.9 `CMD_ERASE_BLOCK (0x12)`
- **Payload Sent (4 or 9 bytes):**
  - `uint32 block_addr`: Physical block index
  - Optional `uint32 pages_per_block`, `uint8 row_cycles`: Geometry used to calculate the block's starting row address; omitted legacy values default to 64 and 3.
- **Response Payload:** None

### 3.10 `CMD_SCAN_BAD_BLOCKS (0x13)`
- **Payload Sent (10 or 12 bytes):**
  - `uint32 total_blocks`: Total blocks in the target chip
  - `uint32 pages_per_block`: Pages per block (e.g. 64)
  - `uint16 oob_col`: Column offset of bad block marker (e.g. 2048)
  - Optional `uint8 col_cycles`, `uint8 row_cycles`: Address-cycle counts; omitted legacy values default to 2 and 3.
- **Response Payload:** Array of `uint32` Little-Endian bad block indices detected at hardware speed.

### 3.11 `CMD_PROBE_PINS (0x31)`
- **Payload Sent:** None
- **Response Payload (4 bytes):**
  - `uint8 rb`: 1 if R/B# is High (Ready), 0 if Low (Busy)
  - `uint8 ce`: Logic level of CE#
  - `uint8 cle`: Logic level of CLE
  - `uint8 ale`: Logic level of ALE
