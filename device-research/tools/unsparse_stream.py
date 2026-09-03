"""Stream-convert an Android sparse image into a raw image."""

import struct
import sys


source_path, destination_path = sys.argv[1], sys.argv[2]

with open(source_path, "rb") as source, open(destination_path, "wb") as destination:
    header = source.read(28)
    magic, major, minor, file_header_size, chunk_header_size, block_size, total_blocks, total_chunks, checksum = struct.unpack(
        "<I4H4I", header
    )
    assert magic == 0xED26FF3A
    assert file_header_size == 28 and chunk_header_size == 12

    for _ in range(total_chunks):
        chunk_type, reserved, chunk_blocks, total_size = struct.unpack("<2H2I", source.read(12))
        output_size = chunk_blocks * block_size
        data_size = total_size - 12

        if chunk_type == 0xCAC1:  # raw
            remaining = data_size
            while remaining:
                data = source.read(min(remaining, 8 * 1024 * 1024))
                destination.write(data)
                remaining -= len(data)
        elif chunk_type == 0xCAC2:  # fill
            pattern = source.read(4)
            buffer = pattern * (min(output_size, 8 * 1024 * 1024) // 4)
            remaining = output_size
            while remaining:
                data = buffer[: min(remaining, len(buffer))]
                destination.write(data)
                remaining -= len(data)
        elif chunk_type == 0xCAC3:  # don't care
            destination.seek(output_size, 1)
        elif chunk_type == 0xCAC4:  # CRC
            source.read(data_size)
        else:
            raise ValueError(f"Unknown sparse chunk type: {chunk_type:#x}")

    destination.truncate(total_blocks * block_size)

print(total_blocks * block_size)
