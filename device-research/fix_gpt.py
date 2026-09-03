# -*- coding: utf-8 -*-
"""修复 openstick gpt_both0.bin 的磁盘大小与 rootfs 分区字段（EDL 直写需要）"""
import struct, shutil

SRC = 'D:/4G/UFI003-analysis/openstick_img/openstick/base/gpt_both0.bin'
DST = 'D:/4G/UFI003-analysis/openstick_img/openstick/base/gpt_both0_fixed.bin'
TOTAL_SECTORS = 0x760000  # 真实磁盘 sectors (7,720,960)
BACKUP_GPT_SECTORS = 33   # 备份 GPT: 1 header + 32 entries
LAST_USABLE = TOTAL_SECTORS - BACKUP_GPT_SECTORS - 1  # 7,720,926

data = bytearray(open(SRC, 'rb').read())

def fix_header(off):
    sig = data[off:off+8]
    assert sig == b'EFI PART', f'bad sig at {off}'
    first_usable = struct.unpack_from('<Q', data, off+40)[0]
    last_usable = struct.unpack_from('<Q', data, off+48)[0]
    print(f'header@{off}: first_usable={first_usable} last_usable={last_usable}')
    struct.pack_into('<Q', data, off+48, LAST_USABLE)
    print(f'  -> last_usable set to {LAST_USABLE}')

# 找两个 EFI PART 头
pos = 0
offs = []
while True:
    i = data.find(b'EFI PART', pos)
    if i < 0:
        break
    offs.append(i)
    pos = i + 8
print('EFI PART headers at:', offs)

for off in offs:
    fix_header(off)

# 修 rootfs entry（entries 数组在主头后）
main_off = offs[0]
entries_lba = struct.unpack_from('<Q', data, main_off+72)[0]
num_entries = struct.unpack_from('<I', data, main_off+80)[0]
entry_size = struct.unpack_from('<I', data, main_off+84)[0]
# entries 数组在主 GPT 区：header 512B 之后 = 文件 offset main_off 之后 512B
entries_off = main_off + 512
print(f'entries: lba={entries_lba} num={num_entries} size={entry_size} file_off={entries_off}')

fixed_rootfs = False
for i in range(num_entries):
    e = entries_off + i * entry_size
    name = data[e+56:e+128].decode('utf-16le', 'replace').rstrip('\x00')
    if name == 'rootfs':
        first = struct.unpack_from('<Q', data, e+32)[0]
        last = struct.unpack_from('<Q', data, e+40)[0]
        print(f'rootfs entry@{e}: first_lba={first} last_lba={last}')
        struct.pack_into('<Q', data, e+40, LAST_USABLE)
        print(f'  -> last_lba set to {LAST_USABLE} (size={(LAST_USABLE-first+1)*512/2**20:.0f}MB)')
        fixed_rootfs = True

if not fixed_rootfs:
    print('!! rootfs entry not found in primary entries; also scan backup entries')

# 备份 GPT entries 数组（在备份头后? 或文件尾部结构不同，先扫全部）
if not fixed_rootfs:
    for i in range(num_entries):
        e = main_off + 512 + 33 * 512 + i * entry_size  # 备份 entries 区可能在备份头后
        if e + 128 > len(data):
            break
        name = data[e+56:e+128].decode('utf-16le', 'replace').rstrip('\x00')
        if name == 'rootfs':
            first = struct.unpack_from('<Q', data, e+32)[0]
            struct.pack_into('<Q', data, e+40, LAST_USABLE)
            print(f'backup rootfs entry@{e} fixed: last->{LAST_USABLE}')
            fixed_rootfs = True

open(DST, 'wb').write(data)
print(f'written: {DST} ({len(data)} bytes)')
