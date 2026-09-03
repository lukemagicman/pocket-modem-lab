# -*- coding: utf-8 -*-
import struct

def parse_gpt(data):
    idx = data.find(b'EFI PART')
    if idx < 0:
        return []
    parts = []
    # 分区表 entries 通常紧跟 header 之后（GPT header 512B, entries 从 LBA2 开始）
    off = idx + 512
    esize = 128
    for i in range(128):
        e = data[off + i * esize: off + (i + 1) * esize]
        if len(e) < 128:
            break
        name = e[56:128].decode('utf-16le', 'replace').rstrip('\x00')
        first = struct.unpack_from('<Q', e, 32)[0]
        last = struct.unpack_from('<Q', e, 40)[0]
        if name and first > 0:
            parts.append((name, first, (last - first + 1) * 512))
    return parts

for label, path in [('openstick gpt_both0', 'D:/4G/UFI003-analysis/openstick_img/openstick/base/gpt_both0.bin'),
                    ('factory android gpt_main0', 'D:/4G/UFI003-analysis/backup/second_stick/gpt_main0.bin')]:
    data = open(path, 'rb').read()
    print(f'=== {label} ===')
    for name, first, size in parse_gpt(data):
        print(f'  {name:16s} start_byte={first*512:>13,}  size={size/2**20:>8.1f}MB')
    print()
