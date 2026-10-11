"""
Universal NAND Flash Clone Tool - Helper Utilities
"""

import time
from typing import Union


def format_bytes(size_bytes: Union[int, float]) -> str:
    """Formats bytes into human-readable B, KB, MB, GB."""
    if size_bytes < 1024:
        return f"{int(size_bytes)} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_speed(speed_mbps: float) -> str:
    """Formats speed in MB/s or KB/s."""
    if speed_mbps < 1.0:
        return f"{speed_mbps * 1024:.1f} KB/s"
    return f"{speed_mbps:.2f} MB/s"


def format_duration(seconds: float) -> str:
    """Formats seconds into HH:MM:SS or MM:SS."""
    seconds = int(max(0, seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def hex_dump_line(data: bytes, offset: int = 0) -> str:
    """Formats up to 16 bytes into standard hex dump representation."""
    hex_part = " ".join(f"{b:02X}" for b in data)
    ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
    return f"{offset:08X}  {hex_part:<48}  |{ascii_part}|"

