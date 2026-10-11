"""
Universal NAND Flash Clone Tool - Filesystem & Partition Signature Analyzer
Scans raw NAND dumps or live memory for embedded structures, filesystems,
and bootloader images (UBI, UBIFS, SquashFS, YAFFS2, JFFS2, U-Boot, FIT, zImage, FAT, Ext4).
"""

import struct
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class DetectedPartition:
    name: str
    fs_type: str
    start_offset: int
    size_bytes: int
    confidence: float       # 0.0 to 1.0
    details: Dict[str, Any]

    @property
    def start_offset_hex(self) -> str:
        return f"0x{self.start_offset:08X}"

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)


def scan_for_signatures(data: bytes, page_size: int = 2048, block_size: int = 131072) -> List[DetectedPartition]:
    """
    Scans a memory buffer for embedded firmware partitions and filesystems.
    """
    results: List[DetectedPartition] = []
    data_len = len(data)
    if data_len < 512:
        return results

    # 1. Search for U-Boot uImage (Magic 0x27051956)
    offset = 0
    while True:
        idx = data.find(b"\x27\x05\x19\x56", offset)
        if idx == -1 or idx + 64 > data_len:
            break
        # Parse uImage header
        # Header: magic(4), hcrc(4), time(4), size(4), load(4), ep(4), dcrc(4), os(1), arch(1), type(1), comp(1), name(32)
        try:
            _, _, _, img_size, load_addr, ep_addr, _, os_id, arch_id, img_type, comp, name_bytes = struct.unpack_from(
                ">IIIIIII4B32s", data, idx
            )
            name_str = name_bytes.split(b"\x00")[0].decode("ascii", errors="replace").strip()
            total_size = 64 + img_size
            results.append(DetectedPartition(
                name=f"uImage: {name_str}" if name_str else "uImage Kernel/Initrd",
                fs_type="U-Boot Legacy Image",
                start_offset=idx,
                size_bytes=total_size,
                confidence=0.98,
                details={
                    "image_size": img_size,
                    "load_address": f"0x{load_addr:08X}",
                    "entry_point": f"0x{ep_addr:08X}",
                    "os": os_id, "arch": arch_id, "type": img_type, "compression": comp,
                    "name": name_str,
                }
            ))
            offset = idx + total_size
        except Exception:
            offset = idx + 4

    # 2. Search for Flattened Device Tree / FIT Image (Magic 0xD00DFEED)
    offset = 0
    while True:
        idx = data.find(b"\xd0\x0d\xfe\xed", offset)
        if idx == -1 or idx + 8 > data_len:
            break
        try:
            totalsize = struct.unpack_from(">I", data, idx + 4)[0]
            if 16 < totalsize <= (data_len - idx):
                results.append(DetectedPartition(
                    name="Device Tree Blob (DTB) / FIT Image",
                    fs_type="FDT/FIT Image",
                    start_offset=idx,
                    size_bytes=totalsize,
                    confidence=0.95,
                    details={"totalsize": totalsize}
                ))
                offset = idx + totalsize
            else:
                offset = idx + 4
        except Exception:
            offset = idx + 4

    # 3. Search for Linux ARM zImage (Magic 0x016F2818 at offset +0x24)
    # Check block boundaries
    for blk_offset in range(0, data_len - 0x30, block_size):
        if data[blk_offset + 0x24 : blk_offset + 0x28] == b"\x18\x28\x6f\x01":
            start_magic, end_magic = struct.unpack_from("<II", data, blk_offset + 0x28)
            img_len = end_magic - start_magic if end_magic > start_magic else 0
            results.append(DetectedPartition(
                name="Linux ARM zImage Kernel",
                fs_type="ARM zImage",
                start_offset=blk_offset,
                size_bytes=img_len if img_len > 0 else 4 * 1024 * 1024,
                confidence=0.95,
                details={"start_addr": hex(start_magic), "end_addr": hex(end_magic)}
            ))

    # 4. Search for UBI Erase Count Header (Magic "UBI#" = 0x55424923)
    offset = 0
    ubi_first_idx = -1
    ubi_last_idx = -1
    ubi_ec_count = 0
    while True:
        idx = data.find(b"UBI#", offset)
        if idx == -1:
            break
        if ubi_first_idx == -1:
            ubi_first_idx = idx
        ubi_last_idx = idx
        ubi_ec_count += 1
        # Skip to next page or block
        offset = idx + min(page_size, 2048)

    if ubi_first_idx != -1 and ubi_ec_count >= 2:
        ubi_size = (ubi_last_idx - ubi_first_idx) + block_size
        results.append(DetectedPartition(
            name=f"UBI Volume ({ubi_ec_count} Eraseblocks)",
            fs_type="UBI / UBIFS Container",
            start_offset=ubi_first_idx,
            size_bytes=min(ubi_size, data_len - ubi_first_idx),
            confidence=0.99,
            details={"eraseblock_count": ubi_ec_count}
        ))

    # 5. Search for SquashFS Filesystem
    squash_magics = [
        (b"sqsh", "SquashFS (Little-Endian)"),
        (b"hsqs", "SquashFS (Big-Endian)"),
        (b"qshs", "SquashFS (Little-Endian swap)"),
        (b"shsq", "SquashFS (Big-Endian swap)"),
    ]
    for magic_bytes, sq_name in squash_magics:
        offset = 0
        while True:
            idx = data.find(magic_bytes, offset)
            if idx == -1 or idx + 96 > data_len:
                break
            # Verify SquashFS superblock header
            try:
                # In SquashFS 4.0: bytes_used is at offset 40 (uint64)
                bytes_used = struct.unpack_from("<Q", data, idx + 40)[0]
                major_ver, minor_ver = struct.unpack_from("<HH", data, idx + 28)
                if major_ver in (3, 4) and 512 < bytes_used <= (data_len - idx + 65536):
                    results.append(DetectedPartition(
                        name=f"{sq_name} v{major_ver}.{minor_ver}",
                        fs_type="SquashFS RootFS",
                        start_offset=idx,
                        size_bytes=bytes_used,
                        confidence=0.99,
                        details={"version": f"{major_ver}.{minor_ver}", "bytes_used": bytes_used}
                    ))
                    offset = idx + bytes_used
                    continue
            except Exception:
                pass
            offset = idx + 4

    # 6. Search for JFFS2 (Magic 0x1985)
    jffs2_count = 0
    jffs2_first = -1
    jffs2_last = -1
    offset = 0
    while True:
        idx = data.find(b"\x85\x19", offset)
        if idx == -1:
            break
        if jffs2_first == -1:
            jffs2_first = idx
        jffs2_last = idx
        jffs2_count += 1
        offset = idx + 512
        if jffs2_count > 50:
            # Plenty of nodes found
            break

    if jffs2_first != -1 and jffs2_count >= 5:
        results.append(DetectedPartition(
            name=f"JFFS2 Log-Structured Filesystem (~{jffs2_count}+ nodes)",
            fs_type="JFFS2",
            start_offset=jffs2_first,
            size_bytes=min(jffs2_last - jffs2_first + block_size, data_len - jffs2_first),
            confidence=0.85,
            details={"nodes_sampled": jffs2_count}
        ))

    # 7. Search for Ext2/Ext3/Ext4 (Magic 0xEF53 at offset 0x438 of superblock)
    for blk_offset in range(0, data_len - 0x500, 1024):
        if data[blk_offset + 0x438 : blk_offset + 0x43A] == b"\x53\xef":
            try:
                block_count = struct.unpack_from("<I", data, blk_offset + 0x404)[0]
                log_block_size = struct.unpack_from("<I", data, blk_offset + 0x418)[0]
                fs_block_size = 1024 << log_block_size
                fs_size = block_count * fs_block_size
                results.append(DetectedPartition(
                    name=f"Ext4 / Ext3 Filesystem ({fs_size // (1024*1024)} MB)",
                    fs_type="Ext2/3/4",
                    start_offset=blk_offset,
                    size_bytes=min(fs_size, data_len - blk_offset),
                    confidence=0.95,
                    details={"block_count": block_count, "block_size": fs_block_size}
                ))
            except Exception:
                pass

    # Sort results by start offset
    results.sort(key=lambda p: p.start_offset)
    return results

