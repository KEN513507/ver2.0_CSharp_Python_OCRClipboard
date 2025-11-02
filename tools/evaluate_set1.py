# -*- coding: utf-8 -*-
"""evaluate_set1.py

Evaluates OCR accuracy on test_images/set1 dataset.
Compares OCR results against ground truth TXT files.

Usage:
    python tools/evaluate_set1.py [manifest_path]

Output:
    - Per-image accuracy report
    - Summary statistics (avg accuracy, error rate)
    - JSON report file
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys
from difflib import SequenceMatcher

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    print("[WARN] PaddleOCR not installed. Install with: pip install paddleocr", file=sys.stderr)


def calc_accuracy(predicted: str, ground_truth: str) -> dict:
    """Calculate accuracy metrics between predicted and ground truth text."""
    sm = SequenceMatcher(None, predicted, ground_truth)
    ratio = sm.ratio()
    
    return {
        "accuracy": ratio,
        "error_rate": 1 - ratio,
        "predicted_len": len(predicted),
        "truth_len": len(ground_truth),
        "diff_len": abs(len(predicted) - len(ground_truth))
    }


def run_ocr(image_path: pathlib.Path, ocr_engine) -> str:
    """Run OCR on image and return recognized text."""
    if not PADDLE_AVAILABLE:
        return "[OCR_UNAVAILABLE]"
    
    result = ocr_engine.ocr(str(image_path), cls=True)
    
    # Extract text from PaddleOCR result structure
    if not result or not result[0]:
        return ""
    
    lines = []
    for line in result[0]:
        text = line[1][0]  # line[1] = (text, confidence)
        lines.append(text)
    
    return ''.join(lines)


def evaluate_dataset(manifest_path: str, root_dir: str) -> dict:
    """Evaluate all images in the dataset."""
    manifest_path = pathlib.Path(manifest_path)
    root_path = pathlib.Path(root_dir)
    
    # Initialize OCR engine
    if PADDLE_AVAILABLE:
        print("[INFO] Initializing PaddleOCR...")
        ocr = PaddleOCR(use_angle_cls=True, lang='japan', show_log=False)
    else:
        ocr = None
        print("[ERROR] Cannot evaluate without OCR engine", file=sys.stderr)
        return {"error": "OCR engine not available"}
    
    # Read manifest
    with manifest_path.open(encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))
    
    results = []
    total_accuracy = 0.0
    total_error = 0.0
    
    print(f"\n{'='*80}")
    print(f"Evaluating {len(rows)} test images...")
    print(f"{'='*80}\n")
    
    for i, row in enumerate(rows, 1):
        file_name = row["file"]
        lang = row["lang"]
        tags = row["tags"]
        
        # Load ground truth
        txt_path = root_path / file_name.replace(".png", ".txt")
        if not txt_path.exists():
            print(f"[SKIP] {file_name} - Ground truth not found")
            continue
        
        ground_truth = txt_path.read_text(encoding="utf-8").strip()
        
        # Run OCR
        image_path = root_path / file_name
        if not image_path.exists():
            print(f"[SKIP] {file_name} - Image not found")
            continue
        
        predicted = run_ocr(image_path, ocr)
        
        # Calculate metrics
        metrics = calc_accuracy(predicted, ground_truth)
        
        # Store result
        result = {
            "file": file_name,
            "lang": lang,
            "tags": tags,
            **metrics,
            "predicted": predicted[:100] + "..." if len(predicted) > 100 else predicted,
            "truth": ground_truth[:100] + "..." if len(ground_truth) > 100 else ground_truth
        }
        results.append(result)
        
        total_accuracy += metrics["accuracy"]
        total_error += metrics["error_rate"]
        
        # Print progress
        status = "✓" if metrics["accuracy"] > 0.9 else "⚠" if metrics["accuracy"] > 0.7 else "✗"
        print(f"[{i:2d}/{len(rows)}] {status} {file_name:30s} | Accuracy: {metrics['accuracy']:.2%} | Error: {metrics['error_rate']:.2%}")
    
    # Summary statistics
    count = len(results)
    summary = {
        "total_images": count,
        "avg_accuracy": total_accuracy / count if count > 0 else 0,
        "avg_error_rate": total_error / count if count > 0 else 0,
        "results": results
    }
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total images:     {summary['total_images']}")
    print(f"Average accuracy: {summary['avg_accuracy']:.2%}")
    print(f"Average error:    {summary['avg_error_rate']:.2%}")
    print(f"{'='*80}\n")
    
    return summary


def main(manifest="test_images/set1/manifest.csv", root="test_images/set1") -> None:
    """Main entry point."""
    result = evaluate_dataset(manifest, root)
    
    # Save JSON report
    output_path = pathlib.Path(root) / "evaluation_report.json"
    with output_path.open("w", encoding="utf-8") as fp:
        json.dump(result, fp, indent=2, ensure_ascii=False)
    
    print(f"[OK] Report saved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        main(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        main()
