"""In text thô từng trang + các dòng quanh Staff ID để debug layout."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pymupdf as fitz

STAFF_RE = re.compile(r"\bVAE\s*[- ]?\d{4,8}\b", re.I)


def main(pdf_path: str):
    path = Path(pdf_path)
    if not path.exists():
        print(f"Not found: {path}")
        return

    with fitz.open(path) as doc:
        for i, page in enumerate(doc, 1):
            text = page.get_text("text")
            print("=" * 60)
            print(f"PAGE {i} | chars={len(text)}")
            print("=" * 60)
            print(text)
            print("-" * 40)
            print("Lines containing Staff ID (with neighbors):")
            lines = text.splitlines()
            for idx, line in enumerate(lines):
                if STAFF_RE.search(line):
                    prev = lines[idx - 1] if idx > 0 else ""
                    nxt = lines[idx + 1] if idx + 1 < len(lines) else ""
                    print(f"  [{idx-1}] {prev!r}")
                    print(f"  [{idx}]   {line!r}  << STAFF")
                    print(f"  [{idx+1}] {nxt!r}")
                    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m tests.stages.dump_text path/to.pdf")
        sys.exit(1)
    main(sys.argv[1])
