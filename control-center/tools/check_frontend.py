import shutil
import subprocess
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "frontend" / "index.html"


class FrontendParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.scripts = []
        self._script = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])
        if tag == "script" and not values.get("src"):
            self._script = []

    def handle_data(self, data):
        if self._script is not None:
            self._script.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            self.scripts.append("".join(self._script))
            self._script = None


def main():
    parser = FrontendParser()
    parser.feed(HTML_PATH.read_text(encoding="utf-8"))
    duplicates = [name for name, count in Counter(parser.ids).items() if count > 1]
    if duplicates:
        raise SystemExit(f"重复 ID：{', '.join(duplicates)}")
    if not parser.scripts:
        raise SystemExit("未找到内联 JavaScript")

    node = shutil.which("node")
    if node:
        result = subprocess.run(
            [node, "--check", "-"],
            input="\n".join(parser.scripts),
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            timeout=15,
        )
        if result.returncode:
            sys.stderr.write(result.stderr)
            raise SystemExit("JavaScript 语法检查失败")
        syntax = "passed"
    else:
        syntax = "skipped-no-node"

    print(f"Frontend OK: ids={len(parser.ids)}, duplicates=0, javascript={syntax}")


if __name__ == "__main__":
    main()
