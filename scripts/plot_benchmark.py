"""
OCR処理時間 vs 文字数のベンチマーク結果をグラフ化
実行: python scripts/plot_benchmark.py

【目的】
Windows.Media.Ocrの処理時間が文字数に対して線形に増加するか検証。
TECHNICAL_LIMITS.mdの「文字数が増えると処理時間が線形に増加するだけ」という主張を実測データで証明。

【検証方法】
1. 異なる文字数（50〜1000文字）の画像を自動生成
2. 各文字数で3回OCR実行して平均値を取得
3. 線形回帰で近似し、決定係数R²で線形性を評価
4. 文字あたりの処理コスト（ms/文字）を可視化

【評価基準】
- R² > 0.95: ほぼ完全な線形
- R² > 0.85: おおむね線形（実用上問題なし）
- R² < 0.85: 非線形要素が支配的
"""
import matplotlib.pyplot as plt
import numpy as np
import matplotlib
matplotlib.rc('font', family='Yu Gothic')  # 日本語フォント設定

# ベンチマーク実測データ (2025-11-01)
# (文字数, fragments数, OCR処理時間ms)
data = [
    (50, 46, 69.9),
    (100, 94, 81.0),
    (200, 188, 115.7),
    (300, 282, 142.8),
    (500, 472, 214.8),
    (800, 754, 431.8),
    (1000, 944, 852.6),
]

chars = np.array([d[0] for d in data])
fragments = np.array([d[1] for d in data])
ocr_ms = np.array([d[2] for d in data])

# 線形回帰
coeffs = np.polyfit(chars, ocr_ms, 1)
linear_fit = np.poly1d(coeffs)

# 決定係数 R²
y_mean = np.mean(ocr_ms)
ss_total = np.sum((ocr_ms - y_mean) ** 2)
ss_res = np.sum((ocr_ms - linear_fit(chars)) ** 2)
r2 = 1 - (ss_res / ss_total)

# グラフ作成
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle('Windows.Media.Ocr ベンチマーク結果 (Windows 11, 2025-11-01)', 
             fontsize=16, fontweight='bold', y=0.98)

# 左: OCR時間 vs 文字数（線形回帰付き）
ax1.scatter(chars, ocr_ms, s=100, alpha=0.8, color='#1f77b4', label='実測データ', zorder=3)
ax1.plot(chars, linear_fit(chars), 'r--', linewidth=2, alpha=0.8, 
         label=f'線形回帰: y = {coeffs[0]:.3f}x + {coeffs[1]:.1f}\nR² = {r2:.4f}', zorder=2)
ax1.axhline(y=400, color='orange', linestyle='--', linewidth=2, alpha=0.7, 
            label='プロジェクトSLA目標 (400ms)', zorder=1)
ax1.set_xlabel('文字数', fontsize=13, fontweight='bold')
ax1.set_ylabel('OCR処理時間 (ms)', fontsize=13, fontweight='bold')
ax1.set_title('【検証①】OCR処理時間 vs 文字数\n線形性の確認（R²が1に近いほど線形）', 
              fontsize=14, fontweight='bold', pad=15)
ax1.grid(True, alpha=0.3, linestyle='--')
ax1.legend(loc='upper left', fontsize=11, framealpha=0.9)
ax1.set_xlim(0, 1100)
ax1.set_ylim(0, 900)

# データポイントにラベル表示
for i, (c, ms) in enumerate(zip(chars, ocr_ms)):
    ax1.annotate(f'{c}字\n{ms:.0f}ms', 
                 xy=(c, ms), 
                 xytext=(5, 5), 
                 textcoords='offset points',
                 fontsize=8, 
                 alpha=0.7)

# 右: 文字あたりのコスト（ms/文字）
ms_per_char = ocr_ms / chars
ax2.scatter(chars, ms_per_char, s=100, alpha=0.8, color='#2ca02c', zorder=3)
avg_cost = np.mean(ms_per_char)
ax2.axhline(y=avg_cost, color='red', linestyle='--', linewidth=2, alpha=0.7, 
            label=f'平均: {avg_cost:.3f} ms/文字', zorder=1)
ax2.set_xlabel('文字数', fontsize=13, fontweight='bold')
ax2.set_ylabel('処理コスト (ms/文字)', fontsize=13, fontweight='bold')
ax2.set_title('【検証②】文字あたりの処理コスト\n線形なら一定、非線形なら文字数増加で上昇', 
              fontsize=14, fontweight='bold', pad=15)
ax2.grid(True, alpha=0.3, linestyle='--')
ax2.legend(fontsize=11, framealpha=0.9)
ax2.set_xlim(0, 1100)

# データポイントにラベル表示
for i, (c, cost) in enumerate(zip(chars, ms_per_char)):
    ax2.annotate(f'{c}字\n{cost:.2f}', 
                 xy=(c, cost), 
                 xytext=(5, 5), 
                 textcoords='offset points',
                 fontsize=8, 
                 alpha=0.7)

plt.tight_layout()
plt.savefig('outputs/ocr_benchmark.png', dpi=150, bbox_inches='tight')
print("=" * 70)
print("✅ グラフ保存: outputs/ocr_benchmark.png")
print("=" * 70)
print("\n【ベンチマーク結果サマリー】")
print(f"テスト日時: 2025-11-01")
print(f"テスト環境: Windows 11, Windows.Media.Ocr")
print(f"測定範囲: 50〜1000文字（7パターン × 3回測定平均）")
print("\n【線形回帰分析】")
print(f"回帰式: OCR時間(ms) = {coeffs[0]:.3f} * 文字数 + {coeffs[1]:.1f}")
print(f"解釈: 文字が1文字増えるごとに {coeffs[0]:.3f}ms 増加")
print(f"決定係数 R² = {r2:.4f}")

if r2 > 0.95:
    conclusion = "✅ ほぼ完全な線形関係（文字数と処理時間は比例）"
elif r2 > 0.85:
    conclusion = "⚠️  おおむね線形（800文字以上で非線形要素が増加傾向）"
else:
    conclusion = "❌ 非線形（文字数以外の要因が支配的）"

print(f"\n【結論】{conclusion}")
print(f"\n【文字あたりの処理コスト】")
print(f"平均: {avg_cost:.3f} ms/文字")
print(f"最小: {min(ms_per_char):.3f} ms/文字 ({chars[np.argmin(ms_per_char)]}文字時)")
print(f"最大: {max(ms_per_char):.3f} ms/文字 ({chars[np.argmax(ms_per_char)]}文字時)")

print(f"\n【実用ガイドライン】線形回帰式による予測値")
print("─" * 50)
for c in [50, 100, 200, 500, 1000, 2000]:
    predicted = linear_fit(c)
    sla_status = "✅ SLA達成" if predicted < 400 else "❌ SLA超過"
    print(f"  {c:5}文字 → 予測: {predicted:7.1f}ms  {sla_status}")

print("─" * 50)
print("\n【TECHNICAL_LIMITS.md への提言】")
if r2 > 0.90:
    print("✅ 「文字数が増えると処理時間が線形に増加する」は実測で証明済み")
    print(f"   R²={r2:.4f} により、文字数が処理時間の主要因であることが確認された")
else:
    print("⚠️  「線形増加」は近似的に正しいが、以下の注意が必要：")
    print(f"   - R²={r2:.4f} のため、文字数以外の要因も影響（画像サイズ、フラグメント数等）")
    print(f"   - 800文字以上では非線形要素が顕著（1000文字で {ocr_ms[-1]:.1f}ms）")

print("\n" + "=" * 70)

plt.show()
