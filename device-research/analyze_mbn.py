# -*- coding: utf-8 -*-
"""UFI003 MBN (ELF) 只读分析器：解析 ELF section 表 + 提取可打印字符串特征"""
import os, re, struct, sys

MBN_DIR = r"D:/4G/UFI003-analysis/mbn"
FILES = ["row_gen_3gpp.mbn", "att_volte.mbn", "tmo_volte_co.mbn",
         "verizon_hvolte.mbn", "cmcc_volte_co.mbn"]

def parse_elf32(data):
    if data[:4] != b"\x7fELF":
        return None
    is_le = data[5] == 1
    e = "<" if is_le else ">"
    e_type, e_machine = struct.unpack_from(e + "HH", data, 16)
    e_shoff = struct.unpack_from(e + "I", data, 32)[0]
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from(e + "HHH", data, 46)
    if not e_shoff or not e_shnum:
        return {"type": e_type, "machine": e_machine, "sections": []}
    shstr_off = None
    secs = []
    for i in range(e_shnum):
        sh = struct.unpack_from(e + "IIIIIIIIII", data, e_shoff + i * e_shentsize)
        sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size = sh[:6]
        secs.append({"name_off": sh_name, "type": sh_type, "offset": sh_offset, "size": sh_size})
    # shstrtab
    sh = secs[e_shstrndx] if e_shstrndx < len(secs) else None
    if sh:
        shstr = data[sh["offset"]:sh["offset"] + sh["size"]]
        for s in secs:
            if 0 <= s["name_off"] < len(shstr):
                end = shstr.find(b"\x00", s["name_off"])
                s["name"] = shstr[s["name_off"]:end].decode("latin-1", "replace")
            else:
                s["name"] = "?"
    return {"type": e_type, "machine": e_machine, "sections": secs}

def printable_strings(data, min_len=5):
    out = []
    cur = []
    for b in data:
        if 32 <= b < 127:
            cur.append(chr(b))
        else:
            if len(cur) >= min_len:
                out.append("".join(cur))
            cur = []
    if len(cur) >= min_len:
        out.append("".join(cur))
    return out

KEYWORDS = ["ims", "volte", "vowifi", "epdg", "att", "tmo", "verizon", "cmcc",
            "china", "apn", "pcscf", "p-cscf", "emergency", "sip", "feature",
            "mcfg", "carrier", "e911", "wifi"]

def main():
    print("=" * 70)
    for fn in FILES:
        path = os.path.join(MBN_DIR, fn)
        data = open(path, "rb").read()
        elf = parse_elf32(data)
        print(f"\n### {fn}  ({len(data)} bytes)")
        if not elf:
            print("  NOT ELF!")
            continue
        print(f"  ELF type={elf['type']} machine={elf['machine']} sections={len(elf['sections'])}")
        for s in elf["sections"]:
            print(f"    [{s.get('name','?')}] type={s['type']} off={s['offset']:#x} size={s['size']}")
        # strings + keyword hits
        strs = printable_strings(data, 6)
        low = " ".join(strs).lower()
        hits = {}
        for kw in KEYWORDS:
            c = len(re.findall(re.escape(kw), low))
            if c:
                hits[kw] = c
        print(f"  keyword hits: {hits}")
        # interesting strings
        interesting = [s for s in strs if re.search(r"ims|volte|wifi|epdg|sip|carrier|mcfg|feature|apn", s, re.I)]
        if interesting:
            print("  interesting strings (first 20):")
            for s in interesting[:20]:
                print(f"    {s[:80]}")

if __name__ == "__main__":
    main()
