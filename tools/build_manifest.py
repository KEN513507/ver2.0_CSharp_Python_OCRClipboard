# -*- coding: utf-8 -*-
"""build_manifest.py

Scans .txt files in test_images/set1 and generates manifest.csv.
Filename format: NNN__LANG__tags.txt / .png

Usage:
    python tools/build_manifest.py [set_dir] [manifest_path]
"""
from __future__ import annotations

import csv
import pathlib
import re
import sys
from typing import Iterable

NAME_RX = re.compile(r"^([0-9]{3})__([A-Z]+)__([a-z0-9-]+)\.(txt|png)$")


def iter_txt_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    for txt in sorted(root.glob("*.txt")):
        if NAME_RX.match(txt.name):
            yield txt


def build_manifest(root: str, out_path: str) -> None:
    root_path = pathlib.Path(root)
    txt_files = list(iter_txt_files(root_path))
    rows = []
    for txt in txt_files:
        match = NAME_RX.match(txt.name)
        assert match is not None
        id_, lang, tags, _ = match.groups()
        text = txt.read_text(encoding="utf-8", errors="ignore")
        
        # Quality check: suspiciously short text
        if len(text.strip("\n")) <= 5:
            print(f"[WARN] Suspiciously short text: {txt.name} ({len(text)} chars)", file=sys.stderr)
        
        rows.append({
            "id": id_,
            "file": f"{id_}__{lang}__{tags}.png",
            "lang": lang,
            "tags": tags,
            "chars_expected": len(text),
            "notes": ""
        })

    manifest_path = pathlib.Path(out_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    with manifest_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=["id", "file", "lang", "tags", "chars_expected", "notes"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"[OK] Manifest: {manifest_path} ({len(rows)} rows)")


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        build_manifest(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2:
        base = sys.argv[1].rstrip('/\\')
        build_manifest(sys.argv[1], f"{base}/manifest.csv")
    else:
        build_manifest("test_images/set1", "test_images/set1/manifest.csv")
