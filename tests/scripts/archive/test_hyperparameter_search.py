#!/usr/bin/env python3
"""
ハイパーパラメータ探索: 失敗した3ケース (002, 008, 012) の改善

実験:
1. Baseline (現在の設定)
2. Dense優先 (002対策)
3. 記号優先 (008対策)
4. LowContrast優先 (012対策)
5. 統合最適化
"""
import subprocess
import json
import sys
from pathlib import Path

# 実験パラメータ
EXPERIMENTS = {
    "baseline": {
        "name": "Baseline (デフォルト)",
        "env": {},
        "description": "現在の設定（比較用）"
    },

    "dense_optimized": {
        "name": "Dense優先 (002対策)",
        "env": {
            "OCR_PADDLE_DET_DB_THRESH": "0.25",        # 0.3 → 0.25
            "OCR_PADDLE_DET_BOX_THRESH": "0.55",       # 0.6 → 0.55
            "OCR_PADDLE_DET_UNCLIP_RATIO": "2.0",      # 1.5 → 2.0
            "OCR_PADDLE_USE_CLS": "1",                 # False → True
        },
        "description": "高密度テキスト検出を強化"
    },

    "symbol_optimized": {
        "name": "記号優先 (008対策)",
        "env": {
            "OCR_PADDLE_REC_BATCH_NUM": "1",           # 6 → 1 (精度優先)
            "OCR_PADDLE_DROP_SCORE": "0.3",            # 0.5 → 0.3 (低信頼度も拾う)
        },
        "description": "記号・罫線認識を強化"
    },

    "lowcontrast_optimized": {
        "name": "LowContrast優先 (012対策)",
        "env": {
            "OCR_PADDLE_DET_LIMIT_SIDE": "1536",       # 960 → 1536
            "OCR_PADDLE_DET_DB_THRESH": "0.2",         # 0.3 → 0.2
            "OCR_PADDLE_DET_UNCLIP_RATIO": "2.5",      # 1.5 → 2.5
        },
        "description": "低コントラスト検出を強化"
    },

    "integrated_best": {
        "name": "統合最適化 (全対策)",
        "env": {
            "OCR_PADDLE_DET_DB_THRESH": "0.25",
            "OCR_PADDLE_DET_BOX_THRESH": "0.55",
            "OCR_PADDLE_DET_UNCLIP_RATIO": "2.0",
            "OCR_PADDLE_DET_LIMIT_SIDE": "1280",
            "OCR_PADDLE_USE_CLS": "1",
            "OCR_PADDLE_REC_BATCH_NUM": "1",
            "OCR_PADDLE_DROP_SCORE": "0.35",
        },
        "description": "バランス型: 全ケースを考慮"
    }
}

# 重点評価対象
FOCUS_CASES = ["002", "008", "012"]

def run_test(experiment_name, env_vars):
    """テストを実行してJSONL結果を返す"""
    import os

    # 環境変数を設定
    test_env = os.environ.copy()
    test_env.update(env_vars)

    # テスト実行
    cmd = [
        "python",
        "tests/scripts/test_ocr_accuracy.py",
        "--dataset",
        "--root", "test_images/set1",
        "--manifest", "manifest.csv",
        "--threshold", "0.30"
    ]

    print(f"\n{'='*80}")
    print(f"実験: {experiment_name}")
    print(f"環境変数: {env_vars}")
    print(f"{'='*80}")

    result = subprocess.run(
        cmd,
        env=test_env,
        capture_output=True,
        text=True
    )

    # 結果JSONLを読み込み
    jsonl_path = Path("tests/outputs/ocr_dataset_eval.jsonl")
    if not jsonl_path.exists():
        print(f"❌ 結果ファイルが見つかりません: {jsonl_path}")
        return []

    results = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            results.append(json.loads(line))

    return results

def analyze_results(experiment_name, results):
    """結果を分析してスコアを計算"""
    total_cases = len(results)
    passed = sum(1 for r in results if r["quality_ok"])

    # 重点ケースの改善度
    focus_improvements = {}
    for case_id in FOCUS_CASES:
        case_result = next((r for r in results if r["id"] == case_id), None)
        if case_result:
            focus_improvements[case_id] = {
                "cer": case_result["cer"],
                "passed": case_result["quality_ok"],
                "engine": case_result["engine"]
            }

    return {
        "experiment": experiment_name,
        "total_passed": passed,
        "total_cases": total_cases,
        "pass_rate": passed / total_cases,
        "focus_improvements": focus_improvements
    }

def main():
    """ハイパーパラメータ探索を実行"""
    print("=" * 80)
    print("ハイパーパラメータ探索: PaddleOCR 設定最適化")
    print("=" * 80)
    print("\n目標:")
    print("  - 002 (clean-dense): CER 0.935 → < 0.30")
    print("  - 008 (mono-code):   CER 0.497 → < 0.30")
    print("  - 012 (lowcontrast): CER 1.000 → < 0.30")
    print("=" * 80)

    all_results = {}

    for exp_id, exp_config in EXPERIMENTS.items():
        results = run_test(exp_config["name"], exp_config["env"])
        analysis = analyze_results(exp_config["name"], results)
        all_results[exp_id] = analysis

        # 即座に結果を表示
        print(f"\n結果: {exp_config['name']}")
        print(f"  合格率: {analysis['pass_rate']:.1%} ({analysis['total_passed']}/{analysis['total_cases']})")
        print(f"  重点ケース:")
        for case_id, improvement in analysis['focus_improvements'].items():
            status = "✅" if improvement["passed"] else "❌"
            print(f"    {status} {case_id}: CER={improvement['cer']:.3f}, engine={improvement['engine']}")

    # 最終サマリー
    print("\n" + "=" * 80)
    print("実験サマリー")
    print("=" * 80)

    # ベストを選出
    best_exp = max(all_results.items(), key=lambda x: x[1]["pass_rate"])
    print(f"\n🏆 ベスト設定: {EXPERIMENTS[best_exp[0]]['name']}")
    print(f"   合格率: {best_exp[1]['pass_rate']:.1%}")
    print(f"   環境変数: {EXPERIMENTS[best_exp[0]]['env']}")

    # 重点ケース改善度
    print(f"\n📊 重点ケース改善:")
    for case_id in FOCUS_CASES:
        baseline_cer = all_results["baseline"]["focus_improvements"][case_id]["cer"]
        best_cer = best_exp[1]["focus_improvements"][case_id]["cer"]
        improvement = (baseline_cer - best_cer) / baseline_cer * 100

        print(f"   {case_id}: {baseline_cer:.3f} → {best_cer:.3f} ({improvement:+.1f}%)")

    # 結果をJSONに保存
    output_path = Path("tests/outputs/hyperparameter_search_results.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 詳細結果を保存: {output_path}")

if __name__ == "__main__":
    main()
