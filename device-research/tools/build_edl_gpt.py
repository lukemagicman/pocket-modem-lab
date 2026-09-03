"""Build valid primary and backup GPT blobs for direct EDL sector writes."""

import pathlib
import struct
import zlib


SOURCE = pathlib.Path(r"D:\4G\UFI003-analysis\openstick_img\openstick\base\gpt_both0_fixed.bin")
OUTPUT = pathlib.Path(r"D:\4G\UFI003-analysis\generated_gpt_edl")
TOTAL_SECTORS = 0x760000
SECTOR_SIZE = 512
ENTRY_COUNT = 128
ENTRY_SIZE = 128
ENTRY_SECTORS = ENTRY_COUNT * ENTRY_SIZE // SECTOR_SIZE


def update_header(header: bytearray, current_lba: int, backup_lba: int, entries_lba: int, entries_crc: int) -> bytes:
    struct.pack_into("<Q", header, 24, current_lba)
    struct.pack_into("<Q", header, 32, backup_lba)
    struct.pack_into("<Q", header, 40, 34)
    struct.pack_into("<Q", header, 48, TOTAL_SECTORS - 34)
    struct.pack_into("<Q", header, 72, entries_lba)
    struct.pack_into("<I", header, 80, ENTRY_COUNT)
    struct.pack_into("<I", header, 84, ENTRY_SIZE)
    struct.pack_into("<I", header, 88, entries_crc)
    struct.pack_into("<I", header, 16, 0)
    header_size = struct.unpack_from("<I", header, 12)[0]
    struct.pack_into("<I", header, 16, zlib.crc32(header[:header_size]) & 0xFFFFFFFF)
    return bytes(header)


source = SOURCE.read_bytes()
pmbr = source[:SECTOR_SIZE]
template_header = bytearray(source[SECTOR_SIZE : 2 * SECTOR_SIZE])
entries = source[2 * SECTOR_SIZE : (2 + ENTRY_SECTORS) * SECTOR_SIZE]
assert template_header[:8] == b"EFI PART"
assert len(entries) == ENTRY_COUNT * ENTRY_SIZE

entries_crc = zlib.crc32(entries) & 0xFFFFFFFF
primary_header = update_header(bytearray(template_header), 1, TOTAL_SECTORS - 1, 2, entries_crc)
backup_header = update_header(
    bytearray(template_header), TOTAL_SECTORS - 1, 1, TOTAL_SECTORS - 1 - ENTRY_SECTORS, entries_crc
)

OUTPUT.mkdir(exist_ok=True)
(OUTPUT / "gpt_primary_34sectors.bin").write_bytes(pmbr + primary_header + entries)
(OUTPUT / "gpt_backup_33sectors.bin").write_bytes(entries + backup_header)

print(f"primary_start=0 primary_sectors={2 + ENTRY_SECTORS}")
print(f"backup_start={TOTAL_SECTORS - 1 - ENTRY_SECTORS} backup_sectors={ENTRY_SECTORS + 1}")
