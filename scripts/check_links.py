#!/usr/bin/env python3
"""Prüft, dass alle relativen href/src-Ziele in dist/ existieren."""
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

root = Path(sys.argv[1] if len(sys.argv) > 1 else "dist").resolve()
bad = []
count = 0
for f in list(root.rglob("*.htm")) + list(root.rglob("*.html")):
    txt = f.read_text(encoding="utf-8")
    for m in re.finditer(r'(?:href|src)="([^"]+)"', txt):
        u = m.group(1)
        if re.match(r"(https?:|mailto:|tel:|#|data:)", u) or f.name == "404.html":
            continue
        path = unquote(urlparse(u).path)
        if not path:
            continue
        count += 1
        target = (f.parent / path).resolve()
        if not target.exists():
            bad.append(f"{f.relative_to(root)} -> {u}")
if bad:
    print("Defekte Links:\n" + "\n".join(sorted(set(bad))))
    sys.exit(1)
print(f"OK: {count} interne Verweise geprüft")
