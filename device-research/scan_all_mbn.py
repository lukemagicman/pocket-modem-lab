# -*- coding: utf-8 -*-
"""全量扫描 58 个 MBN：新西兰运营商痕迹 + IMS/VoLTE/VoWiFi 特征统计"""
import os, re, glob

ROOT = r"D:/4G/UFI003-analysis/mcfg_all"

def strings_of(data, min_len=5):
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

NZ = ["2degree", "spark", "vodafone", "one nz", "one_nz", "mnc024", "mcc530",
      "nz ", "new zealand", "telecom nz"]
FEATURES = {
    "IMS_enable": r"/nv/item_files/ims/IMS_enable",
    "volte": r"volte",
    "epdg": r"epdg",
    "wifi_config": r"wifi_config",
    "qti-wlan": r"qti-wlan",
    "smsip": r"smsip",
    "mmtel": r"mmtel",
    "pcscf": r"[Pp]-?[Cc][Ss][Cc][Ff]",
    "icsi-ref": r"icsi-ref",
}

rows = []
nz_hits = []
for path in sorted(glob.glob(os.path.join(ROOT, "**", "mcfg_sw.mbn"), recursive=True)):
    rel = os.path.relpath(path, ROOT).replace("\\", "/")
    data = open(path, "rb").read()
    low = data.decode("latin-1", "replace").lower()
    text = " ".join(strings_of(data))
    row = {"file": rel, "size": len(data)}
    for feat, pat in FEATURES.items():
        row[feat] = 1 if re.search(pat, low) else 0
    # NZ hits
    nz = [k for k in NZ if re.search(re.escape(k), low)]
    if nz:
        nz_hits.append((rel, nz))
    rows.append(row)

print("=== NZ / 2degrees 痕迹 ===")
if nz_hits:
    for r, k in nz_hits:
        print(f"  {r}: {k}")
else:
    print("  无任何新西兰运营商痕迹 ✓")

print("\n=== VoLTE/VoWiFi 能力 MBN 清单（含 epdg 或 wifi_config 或 qti-wlan 或 pcscf）===")
for r in rows:
    if r["epdg"] or r["wifi_config"] or r["qti-wlan"] or r["pcscf"]:
        flags = "".join(f"{k} " for k in ["IMS_enable","volte","epdg","wifi_config","qti-wlan","smsip","mmtel","pcscf"] if r[k])
        print(f"  {r['file']}  ({r['size']}B)  [{flags.strip()}]")

print(f"\n=== 统计 ===")
total = len(rows)
print(f"总 MBN 数: {total}")
for feat in FEATURES:
    n = sum(1 for r in rows if r[feat])
    print(f"  {feat}: {n}/{total}")
