#!/usr/bin/env python3
"""
Analyze OCR error patterns from test results.
Reads the OCR accuracy test results and provides insights into common error patterns.
"""

import json
import os
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
import sys

# Add src/python to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'python'))

from ocr_worker.handler import levenshtein_distance

def analyze_error_patterns(results_file: str) -> Dict:
    """
    Analyze OCR error patterns from test results.
    """
    if not os.path.exists(results_file):
        print(f"Results file not found: {results_file}")
        return {}

    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)

    analysis = {
        'total_tests': len(results),
        'passed_tests': sum(1 for r in results if r['quality_ok']),
        'failed_tests': sum(1 for r in results if not r['quality_ok']),
        'error_patterns': [],
        'scale_performance': {},
        'common_errors': defaultdict(int)
    }

    # Analyze by scale
    scale_results = defaultdict(list)
    for result in results:
        scale = result['scale']
        scale_results[scale].append(result)

    for scale, scale_data in scale_results.items():
        passed = sum(1 for r in scale_data if r['quality_ok'])
        total = len(scale_data)
        avg_error = sum(r['error_distance'] for r in scale_data) / total
        avg_confidence = sum(r['confidence'] for r in scale_data) / total

        analysis['scale_performance'][f"{scale}x"] = {
            'passed': passed,
            'total': total,
            'success_rate': passed / total if total > 0 else 0,
            'avg_error_distance': avg_error,
            'avg_confidence': avg_confidence
        }

    # Analyze error patterns for failed tests
    for result in results:
        if not result['quality_ok']:
            expected = result.get('expected_text', '').replace('...', '')
            actual = result.get('actual_text', '').replace('...', '')

            # Find character-level differences
            expected_chars = list(expected)
            actual_chars = list(actual)

            # Enhanced character error analysis
            char_errors = []
            false_negatives = []  # Characters that should exist but don't
            false_positives = []  # Characters that exist but shouldn't

            # Detect missing characters (false negatives)
            for i, exp in enumerate(expected_chars):
                if i >= len(actual_chars) or exp != actual_chars[i]:
                    false_negatives.append({
                        'position': i,
                        'expected': exp,
                        'context': expected[max(0, i-2):min(len(expected), i+3)]
                    })

            # Detect extra characters (false positives)
            for i, act in enumerate(actual_chars):
                if i >= len(expected_chars) or act != expected_chars[i]:
                    false_positives.append({
                        'position': i,
                        'actual': act,
                        'context': actual[max(0, i-2):min(len(actual), i+3)]
                    })

            # Character substitution errors
            min_len = min(len(expected_chars), len(actual_chars))
            for i in range(min_len):
                if expected_chars[i] != actual_chars[i]:
                    char_errors.append({
                        'position': i,
                        'expected': expected_chars[i],
                        'actual': actual_chars[i],
                        'context': expected[max(0, i-2):i+3]
                    })

            analysis['error_patterns'].append({
                'scale': result['scale'],
                'confidence': result['confidence'],
                'error_distance': result['error_distance'],
                'expected_length': len(expected),
                'actual_length': len(actual),
                'character_errors': char_errors[:10],  # Limit to first 10 errors
                'false_negatives': false_negatives[:5],  # Missing characters
                'false_positives': false_positives[:5],  # Extra characters
                'text_similarity': 1 - (result['error_distance'] / max(len(expected), len(actual)))
            })

            # Count common error types
            for error in char_errors:
                error_type = f"{error['expected']}->{error['actual']}"
                analysis['common_errors'][error_type] += 1

            # Count false negative/positive patterns
            analysis.setdefault('false_negative_patterns', defaultdict(int))
            for fn in false_negatives:
                analysis['false_negative_patterns'][fn['expected']] += 1

            analysis.setdefault('false_positive_patterns', defaultdict(int))
            for fp in false_positives:
                analysis['false_positive_patterns'][fp['actual']] += 1

    # Sort common errors by frequency
    analysis['common_errors'] = dict(sorted(analysis['common_errors'].items(),
                                          key=lambda x: x[1], reverse=True))

    return analysis

def print_analysis_report(analysis: Dict):
    """
    Print a formatted analysis report.
    """
    if not analysis:
        print("No analysis data available.")
        return

    print("=" * 60)
    print("OCR ERROR ANALYSIS REPORT")
    print("=" * 60)

    print(f"\nOverall Performance:")
    print(f"  Total Tests: {analysis['total_tests']}")
    print(f"  Passed: {analysis['passed_tests']}")
    print(f"  Failed: {analysis['failed_tests']}")
    print(".1f")

    print(f"\nScale Performance:")
    for scale, perf in analysis['scale_performance'].items():
        print(f"  {scale}: {perf['passed']}/{perf['total']} passed "
              ".1f"
              ".1f")

    if analysis['common_errors']:
        print(f"\nMost Common Character Errors:")
        for error_type, count in list(analysis['common_errors'].items())[:10]:
            print(f"  {error_type}: {count} times")

    if analysis['error_patterns']:
        print(f"\nDetailed Error Patterns (Failed Tests):")
        for i, pattern in enumerate(analysis['error_patterns'][:5]):  # Show first 5
            print(f"\n  Test {i+1} (Scale {pattern['scale']}x):")
            print(f"    Confidence: {pattern['confidence']:.3f}")
            print(f"    Error Distance: {pattern['error_distance']}")
            print(f"    Text Length: {pattern['actual_length']}/{pattern['expected_length']}")
            if pattern['character_errors']:
                print("    Character Errors:")
                for error in pattern['character_errors'][:5]:
                    print(f"      Pos {error['position']}: '{error['expected']}' -> '{error['actual']}' "
                          f"(context: '{error['context']}')")

def main():
    """Main function."""
    results_file = os.path.join(os.path.dirname(__file__), '..', 'outputs', 'ocr_accuracy_test.json')

    analysis = analyze_error_patterns(results_file)
    print_analysis_report(analysis)

    # Save detailed analysis
    analysis_file = os.path.join(os.path.dirname(__file__), '..', 'outputs', 'ocr_error_analysis.json')
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    print(f"\nDetailed analysis saved to: {analysis_file}")

if __name__ == '__main__':
    main()
