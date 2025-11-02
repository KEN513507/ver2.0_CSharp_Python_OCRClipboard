# -*- coding: utf-8 -*-
"""extract_texts.py

HTML extraction utility: Extracts ground truth text from test set 1 HTML
and generates `test_images/set1/*.txt` files.

Supported patterns:
  A) Header structure: "File: 001__JP__clean.txt" "Ground Truth Text: ..."
  B) <pre data-file="...">...</pre> / <code data-file="...">...</code>
  C) <div class="groundtruth" data-file="...">...</div>

Usage:
    python tools/extract_texts.py ocr_test_set1_corpus_corrected.html [output_dir]
"""
from __future__ import annotations

import os
import pathlib
import re
import sys
from typing import Dict

from bs4 import BeautifulSoup  # type: ignore

FILE_RX = re.compile(r"^\s*(File|ファイル)\s*:\s*([0-9]{3}__([A-Z]+)__([a-z0-9-]+)\.txt)\s*$", re.IGNORECASE)
FILE_NEXT_RX = re.compile(r"^\s*([0-9]{3}__([A-Z]+)__([a-z0-9-]+)\.txt)\s*$", re.IGNORECASE)
GT_RX = re.compile(r"^\s*(Ground Truth Text|正解テキスト)\s*:\s*$", re.IGNORECASE)


def extract_blocks_from_text(text: str) -> Dict[str, str]:
    """Extract ground truth text from header + body format"""
    out: Dict[str, str] = {}
    lines = [line.rstrip("\n") for line in text.splitlines()]
    i = 0
    while i < len(lines):
        fname = None
        j = i

        match = FILE_RX.match(lines[i])
        if match:
            fname = match.group(2)
            j = i + 1
        else:
            stripped = lines[i].strip().lower()
            if stripped in {"file:", "ファイル:"}:
                j = i + 1
                while j < len(lines):
                    next_match = FILE_NEXT_RX.match(lines[j])
                    if next_match:
                        fname = next_match.group(1)
                        j += 1
                        break
                    if lines[j].strip():  # 別のテキストが出たら諦める
                        break
                    j += 1
            else:
                i += 1
                continue

        if not fname:
            i += 1
            continue

        # 探索開始位置から "正解テキスト:" 行を探す
        k = j
        while k < len(lines) and not GT_RX.match(lines[k]):
            k += 1
        if k >= len(lines):
            i = k
            continue

        # 本文
        k += 1
        buffer = []
        while k < len(lines):
            if FILE_RX.match(lines[k]):
                break
            stripped_line = lines[k].strip().lower()
            if stripped_line in {"file:", "ファイル:"}:
                break
            if FILE_NEXT_RX.match(lines[k]):
                break
            buffer.append(lines[k])
            k += 1

        text_block = "\n".join(buffer).strip("\n")
        if text_block:
            out[fname] = text_block

        i = k
    return out


def extract_blocks_from_dom(soup: BeautifulSoup) -> Dict[str, str]:
    """Extract ground truth text from data-file attributed elements"""
    out: Dict[str, str] = {}
    for tag in soup.select('[data-file]'):
        fname = tag.get('data-file', '').strip()
        if fname.endswith('.txt'):
            out[fname] = tag.get_text('\n').strip('\n')

    for tag in soup.find_all(['pre', 'code']):
        fname = (tag.get('data-file') or '').strip()
        if fname.endswith('.txt'):
            out.setdefault(fname, tag.get_text('\n').strip('\n'))
    return out


def main(html_path: str, out_dir: str = "test_images/set1") -> None:
    out_path = pathlib.Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    raw = pathlib.Path(html_path).read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(raw, "html.parser")

    blocks = extract_blocks_from_dom(soup)
    if not blocks:
        blocks = extract_blocks_from_text(soup.get_text("\n"))

    if not blocks:
        print("[ERROR] No ground truth text found. Check HTML structure.", file=sys.stderr)
        sys.exit(2)

    for fname, text in sorted(blocks.items()):
        destination = out_path / fname
        destination.write_text(text.replace("\r\n", "\n"), encoding="utf-8")
        print(f"[WRITE] {destination} ({len(text)} chars)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python tools/extract_texts.py <html> [out_dir]")
        sys.exit(1)
    target_html = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) >= 3 else "test_images/set1"
    main(target_html, output_dir)
