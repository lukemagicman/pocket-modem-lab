"""Print board identity and SIM/PMIC-related properties from one or more DTBs."""

import pathlib
import re
import sys
from pyfdt.pyfdt import FdtBlobParse


def value_text(obj):
    if hasattr(obj, "strings"):
        return repr(obj.strings)
    if hasattr(obj, "words"):
        return " ".join(f"0x{x:08x}" for x in obj.words)
    if hasattr(obj, "bytes"):
        return repr(obj.bytes)
    return ""


for pattern in sys.argv[1:]:
    for path in sorted(pathlib.Path().glob(pattern)):
        try:
            fdt = FdtBlobParse(path.open("rb")).to_fdt()
        except Exception as exc:
            print(f"FILE {path}\nERROR {exc}")
            continue
        print(f"FILE {path}")
        for item_path, obj in fdt.get_rootnode().walk():
            key = item_path.lower()
            if (
                item_path in ("/model", "/compatible", "/qcom,msm-id", "/qcom,board-id")
                or re.search(r"(^|[/,_-])(sim|uim)([/,_-]|$)", key)
                or re.search(r"(^|/)l6([@/_-]|$)", key)
                or "vreg" in key and ("sim" in key or "uim" in key)
            ):
                print(f"  {item_path}: {value_text(obj)}")

