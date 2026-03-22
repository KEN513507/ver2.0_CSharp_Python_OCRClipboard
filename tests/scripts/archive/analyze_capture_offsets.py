#!/usr/bin/env python
"""
Summarize capture selection diagnostics and compute deltas against an expected rectangle.

Usage examples:
  python tests/scripts/analyze_capture_offsets.py
  python tests/scripts/analyze_capture_offsets.py --scenario primary_125pct --expected 100,50,400,80
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Optional, Tuple, Dict

Rect = Tuple[int, int, int, int]  # left, top, width, height


def parse_expected(value: str) -> Optional[Rect]:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"none", "null", ""}:
        return None
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("Expected 4 comma-separated integers: left,top,width,height")
    try:
        numbers = tuple(int(p) for p in parts)
    except ValueError as exc:  # pragma: no cover - defensive
        raise argparse.ArgumentTypeError(f"Failed to parse expected rect '{value}': {exc}") from exc
    return numbers  # type: ignore[return-value]


def load_entries(path: Path) -> Iterable[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Diagnostics log not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Malformed JSON on line {line_no}: {exc}") from exc
            yield payload


def summarize(entries: Iterable[dict], expected: Optional[Rect], scenarios: Optional[set[str]], limit: Optional[int]) -> None:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        if entry.get("event") != "selection":
            continue
        scenario = entry.get("scenario") or "unknown"
        if scenarios and scenario not in scenarios:
            continue
        grouped[scenario].append(entry)

    if not grouped:
        print("No selection diagnostics to report.")
        return

    for scenario in sorted(grouped):
        records = grouped[scenario]
        counter: Counter[Rect] = Counter()
        for rec in records:
            selection = rec.get("selection") or {}
            sel = selection.get("selectionMonitorLocalPixels")
            if not sel:
                continue
            counter[(sel.get("left", 0), sel.get("top", 0), sel.get("width", 0), sel.get("height", 0))] += 1

        print(f"\n=== Scenario: {scenario} (samples={len(records)}, uniqueRects={len(counter)}) ===")
        for rect, count in counter.most_common():
            if limit and count < limit:
                continue
            left, top, width, height = rect
            label = f"Rect monitor-local px: left={left}, top={top}, w={width}, h={height}"
            if expected:
                dx = left - expected[0]
                dy = top - expected[1]
                dw = width - expected[2]
                dh = height - expected[3]
                label += f" | delta=(dx={dx}, dy={dy}, dw={dw}, dh={dh})"
            print(f"- {label}  count={count}")
        handles = {rec.get("selection", {}).get("monitorHandle", "unknown") for rec in records if rec.get("selection")}
        print(f"- Monitor handles observed: {', '.join(sorted(handles)) if handles else 'n/a'}")


def extract_regions_from_html(html_path: Path) -> Dict[str, Rect]:
    if not html_path.exists():
        return {}
    text = html_path.read_text(encoding="utf-8")
    match = re.search(r'<script[^>]*id=["\']test-regions["\'][^>]*>(.*?)</script>', text, re.IGNORECASE | re.DOTALL)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    regions: Dict[str, Rect] = {}
    for key, value in payload.items():
        if isinstance(value, (list, tuple)) and len(value) == 4:
            try:
                rect = tuple(int(v) for v in value)
            except ValueError:
                continue
            regions[key] = rect  # type: ignore[assignment]
    return regions


def resolve_expected_rect(arg_value: str, html_path: Path, region_name: str) -> Optional[Rect]:
    lowered = arg_value.strip().lower()
    if lowered == "auto":
        regions = extract_regions_from_html(html_path)
        rect = regions.get(region_name)
        if rect:
            print(f"Loaded expected rectangle for '{region_name}' from {html_path}")
        else:
            print(f"Region '{region_name}' not found in {html_path}; falling back to manual input.")
        return rect
    return parse_expected(arg_value)


def find_latest_log(logs_dir: Path) -> Optional[Path]:
    if not logs_dir.exists():
        return None
    candidates = sorted(logs_dir.glob("capture_diagnostics_*.jsonl"))
    return candidates[-1] if candidates else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze capture diagnostics output.")
    parser.add_argument(
        "--log",
        default="auto",
        help="Path to capture diagnostics JSONL log. Use 'auto' to pick the latest capture_diagnostics_*.jsonl under logs/.",
    )
    parser.add_argument(
        "--expected",
        default="auto",
        help="Expected monitor-local rectangle 'left,top,width,height'. Use 'auto' to read from HTML or 'none' to skip.",
    )
    parser.add_argument(
        "--pattern-html",
        type=Path,
        default=Path("tests") / "assets" / "coordinate_test_pattern.html",
        help="Coordinate test HTML containing <script id=\"test-regions\"> metadata (default: tests/assets/coordinate_test_pattern.html).",
    )
    parser.add_argument(
        "--region",
        default="TEST-A1",
        help="Region key inside the HTML metadata when --expected=auto.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        help="Filter to one or more scenario names (repeatable).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional minimum count threshold before printing delta rows (helps trim noise).",
    )
    args = parser.parse_args()

    if args.log.lower() == "auto":
        log_path = find_latest_log(Path("logs"))
        if not log_path:
            print("No diagnostics logs found under logs/.")
            return
    else:
        log_path = Path(args.log)
    if not log_path.exists():
        print(f"Diagnostics log not found: {log_path}")
        return

    expected_rect = resolve_expected_rect(args.expected, args.pattern_html, args.region)
    scenario_filter = set(args.scenarios) if args.scenarios else None
    entries = list(load_entries(log_path))
    summarize(entries, expected_rect, scenario_filter, args.limit)


if __name__ == "__main__":
    main()
