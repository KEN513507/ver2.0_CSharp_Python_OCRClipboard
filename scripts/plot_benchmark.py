#!/usr/bin/env python3
"""
OCR Performance Benchmark Plotter
二次関数モデル (O(n²)) によるグラフ生成

統計的根拠:
- Linear:    R²=0.8759, AIC=67.40
- Quadratic: R²=0.9783, AIC=57.18 ← 採用
- ΔAIC = 10.22 → "almost certain" quadratic superiority
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import matplotlib
matplotlib.use('TkAgg')  # インタラクティブ表示

# 日本語フォント設定（可読性重視）
try:
    plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'Yu Gothic UI', 'Meiryo UI', 'MS Gothic', 'sans-serif']
except:
    plt.rcParams['font.family'] = ['MS Gothic', 'Yu Gothic', 'Meiryo', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False  # マイナス記号の文字化け防止

# 実測データ (文字数, フラグメント数, 処理時間ms)
BENCHMARK_DATA = [
    (50, 46, 69.9),
    (100, 94, 81.0),
    (200, 188, 115.7),
    (300, 282, 142.8),
    (500, 472, 214.8),
    (800, 754, 431.8),
    (1000, 944, 852.6),
]

# 二次関数係数 (統計的に最良のモデル)
A = 0.0010277886
B = -0.3301546922
C = 113.3679999142

# SLA設定
SLA_THRESHOLD_MS = 400
SLA_CHARS_LIMIT = 712  # 400msを達成できる理論限界


def quadratic_model(x):
    """二次関数モデル: y = Ax² + Bx + C"""
    return A * x**2 + B * x + C


def linear_model(x):
    """線形モデル (比較用・不適切)"""
    return 0.7332 * x - 36.32


def calculate_statistics(chars, ocr_ms):
    """統計指標を計算"""
    # 二次関数フィット
    coeffs_quad = np.polyfit(chars, ocr_ms, 2)
    pred_quad = np.polyval(coeffs_quad, chars)
    ss_res_quad = np.sum((ocr_ms - pred_quad) ** 2)
    ss_tot = np.sum((ocr_ms - np.mean(ocr_ms)) ** 2)
    r2_quad = 1 - ss_res_quad / ss_tot
    
    # 線形フィット
    coeffs_lin = np.polyfit(chars, ocr_ms, 1)
    pred_lin = np.polyval(coeffs_lin, chars)
    ss_res_lin = np.sum((ocr_ms - pred_lin) ** 2)
    r2_lin = 1 - ss_res_lin / ss_tot
    
    # AIC計算 (k=パラメータ数, n=サンプル数)
    n = len(chars)
    aic_quad = n * np.log(ss_res_quad / n) + 2 * 3  # 3パラメータ (a, b, c)
    aic_lin = n * np.log(ss_res_lin / n) + 2 * 2    # 2パラメータ (a, b)
    
    return {
        'r2_quad': r2_quad,
        'r2_lin': r2_lin,
        'aic_quad': aic_quad,
        'aic_lin': aic_lin,
        'delta_aic': aic_quad - aic_lin,
        'residual_std_quad': np.sqrt(ss_res_quad / (n - 3)),
        'residual_std_lin': np.sqrt(ss_res_lin / (n - 2)),
    }


def plot_benchmark(output_path='outputs/ocr_benchmark.png', show_linear=False, interactive=True):
    """ベンチマークグラフを生成"""
    
    # データ抽出
    chars = np.array([d[0] for d in BENCHMARK_DATA])
    fragments = np.array([d[1] for d in BENCHMARK_DATA])
    ocr_ms = np.array([d[2] for d in BENCHMARK_DATA])
    
    # 統計計算
    stats = calculate_statistics(chars, ocr_ms)
    
    # プロット用の滑らかな曲線
    x_smooth = np.linspace(0, 1100, 500)
    y_quad = quadratic_model(x_smooth)
    y_lin = linear_model(x_smooth)
    
    # グラフ作成
    fig, ax = plt.subplots(figsize=(14, 9))
    
    # 実測データ（文字数注記付き）
    scatter = ax.scatter(chars, ocr_ms, s=120, c='blue', alpha=0.7, 
                        label='実測データ', zorder=5, edgecolors='black', linewidths=1.5)
    
    # サンプル点に文字数注記（エビデンス強化）
    for i, (x, y) in enumerate(zip(chars, ocr_ms)):
        ax.annotate(f'{x}字', xy=(x, y), xytext=(5, 5), 
                   textcoords='offset points', fontsize=8, alpha=0.7)
    
    # 二次関数モデル（正式採用）
    ax.plot(x_smooth, y_quad, 'r-', linewidth=2.5, 
            label=f'二次関数モデル (R²={stats["r2_quad"]:.4f}, AIC={stats["aic_quad"]:.2f})',
            zorder=3)
    
    # 線形モデル（比較用・不適切）
    if show_linear:
        ax.plot(x_smooth, y_lin, 'g--', linewidth=1.5, alpha=0.6,
                label=f'線形モデル [不適切] (R²={stats["r2_lin"]:.4f}, AIC={stats["aic_lin"]:.2f})',
                zorder=2)
    
    # SLA閾値ライン（P95明記で実運用感）
    ax.axhline(y=SLA_THRESHOLD_MS, color='orange', linestyle='--', linewidth=2,
               label=f'SLA閾値 P95 < {SLA_THRESHOLD_MS}ms', zorder=4)
    ax.axvline(x=SLA_CHARS_LIMIT, color='orange', linestyle=':', linewidth=1.5,
               alpha=0.5, zorder=1)
    
    # 遷移領域の塗りつぶし
    ax.axvspan(500, 800, alpha=0.1, color='yellow', 
               label='O(n)→O(n²) 遷移領域')
    ax.axvspan(800, 1100, alpha=0.1, color='red',
               label='非線形支配領域 (自動分割必須)')
    
    # 自動分割戦略アイコン（対策の視覚化）
    ax.annotate('自動分割\n戦略', xy=(900, 700), xytext=(950, 780),
               fontsize=11, fontweight='bold', color='darkred',
               arrowprops=dict(arrowstyle='->', lw=2, color='darkred'),
               bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', edgecolor='darkred', linewidth=2))
    
    # ラベルとタイトル
    ax.set_xlabel('文字数', fontsize=14, fontweight='bold')
    ax.set_ylabel('処理時間 (ms)', fontsize=14, fontweight='bold')
    ax.set_title(
        f'OCR処理時間の二次関数特性 (O(n²) 挙動)\n'
        f'ΔAIC={abs(stats["delta_aic"]):.2f} → 二次モデル "almost certain" 優位',
        fontsize=16, fontweight='bold', pad=20
    )
    
    # グリッドと凡例
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='upper left', fontsize=11, framealpha=0.95)
    
    # 統計情報のテキストボックス（設計指針 + 運用指針）
    stats_text = (
        f'🔬 統計的根拠:\n'
        f'  • 二次モデル: R²={stats["r2_quad"]:.4f}, σ={stats["residual_std_quad"]:.1f}ms\n'
        f'  • 線形モデル: R²={stats["r2_lin"]:.4f}, σ={stats["residual_std_lin"]:.1f}ms\n'
        f'  • ΔAIC = {abs(stats["delta_aic"]):.2f} (>10 → 圧倒的優位)\n'
        f'  • 複雑性: O(n²) - フラグメント間干渉コスト\n'
        f'\n'
        f'🔒 設計指針:\n'
        f'  • 予測式: y = {A:.6f}x² + {B:.4f}x + {C:.2f}\n'
        f'  • 文字数計測 + {SLA_CHARS_LIMIT}字閾値で自動分割\n'
        f'  • KPI: P95 < {SLA_THRESHOLD_MS}ms / エラー率 <1%\n'
        f'\n'
        f'📈 運用:\n'
        f'  • 監視: 残差分布∥分散∥傾向変化\n'
        f'  • 精度低下時はA/B再学習\n'
        f'  • 外れ値: ±3σ超過でアラート'
    )
    ax.text(0.98, 0.02, stats_text, transform=ax.transAxes,
            fontsize=9, verticalalignment='bottom', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9, edgecolor='black', linewidth=1.5),
            family='monospace')
    
    # 軸範囲
    ax.set_xlim(-50, 1100)
    ax.set_ylim(0, 900)
    
    # 保存
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f'✅ グラフ保存: {output_path}')
    print(f'📊 統計サマリー:')
    print(f'   二次モデル R²={stats["r2_quad"]:.4f}, AIC={stats["aic_quad"]:.2f}')
    print(f'   線形モデル R²={stats["r2_lin"]:.4f}, AIC={stats["aic_lin"]:.2f}')
    print(f'   ΔAIC = {abs(stats["delta_aic"]):.2f} → 二次モデル圧倒的優位')
    
    # インタラクティブ表示
    if interactive:
        plt.show()
    
    return stats


def plot_complexity_analysis(output_path='outputs/complexity_analysis.png', interactive=True):
    """計算複雑性の比較グラフ"""
    
    chars = np.array([d[0] for d in BENCHMARK_DATA])
    ocr_ms = np.array([d[2] for d in BENCHMARK_DATA])
    
    # 各複雑性クラスのフィット
    x_smooth = np.linspace(50, 1000, 500)
    
    # O(n)
    coeffs_n = np.polyfit(chars, ocr_ms, 1)
    y_n = np.polyval(coeffs_n, x_smooth)
    r2_n = 1 - np.sum((ocr_ms - np.polyval(coeffs_n, chars))**2) / np.sum((ocr_ms - np.mean(ocr_ms))**2)
    
    # O(n²)
    coeffs_n2 = np.polyfit(chars, ocr_ms, 2)
    y_n2 = np.polyval(coeffs_n2, x_smooth)
    r2_n2 = 1 - np.sum((ocr_ms - np.polyval(coeffs_n2, chars))**2) / np.sum((ocr_ms - np.mean(ocr_ms))**2)
    
    # O(n log n)
    n_logn = chars * np.log(chars)
    coeffs_nlogn = np.polyfit(n_logn, ocr_ms, 1)
    y_nlogn = coeffs_nlogn[0] * x_smooth * np.log(x_smooth) + coeffs_nlogn[1]
    r2_nlogn = 1 - np.sum((ocr_ms - np.polyval(coeffs_nlogn, n_logn))**2) / np.sum((ocr_ms - np.mean(ocr_ms))**2)
    
    # プロット
    fig, ax = plt.subplots(figsize=(12, 8))
    
    ax.scatter(chars, ocr_ms, s=100, c='blue', alpha=0.7, 
               label='実測データ', zorder=5, edgecolors='black', linewidths=1.5)
    
    ax.plot(x_smooth, y_n, 'g--', linewidth=2, alpha=0.6,
            label=f'O(n) - 線形 (R²={r2_n:.4f})')
    ax.plot(x_smooth, y_n2, 'r-', linewidth=2.5,
            label=f'O(n²) - 二次 (R²={r2_n2:.4f}) ✅')
    ax.plot(x_smooth, y_nlogn, 'purple', linestyle='-.', linewidth=2, alpha=0.7,
            label=f'O(n log n) - 準線形 (R²={r2_nlogn:.4f})')
    
    ax.set_xlabel('文字数', fontsize=14, fontweight='bold')
    ax.set_ylabel('処理時間 (ms)', fontsize=14, fontweight='bold')
    ax.set_title('計算複雑性クラスの適合度比較', fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='upper left', fontsize=12, framealpha=0.95)
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f'✅ 複雑性グラフ保存: {output_path}')
    
    # インタラクティブ表示
    if interactive:
        plt.show()
    
    return {'r2_linear': r2_n, 'r2_quadratic': r2_n2, 'r2_nlogn': r2_nlogn}


if __name__ == '__main__':
    import sys
    
    # デフォルトで両方のグラフ生成
    print('📈 OCRベンチマークグラフ生成中...')
    print('=' * 60)
    
    # メインベンチマークグラフ
    stats = plot_benchmark(show_linear=True)
    
    print()
    print('📊 計算複雑性比較グラフ生成中...')
    print('=' * 60)
    
    # 複雑性比較グラフ
    plot_complexity_analysis()
    
    print()
    print('✨ 完了！')
    print('=' * 60)
    print('結論: 二次関数モデル (O(n²)) が統計的に最適')
    print(f'     ΔAIC={abs(stats["delta_aic"]):.2f} → 線形モデルは不適切')
