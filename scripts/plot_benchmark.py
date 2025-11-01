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
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# 左: OCR時間 vs 文字数（線形回帰付き）
ax1.scatter(chars, ocr_ms, s=80, alpha=0.7, label='実測データ')
ax1.plot(chars, linear_fit(chars), 'r--', alpha=0.8, 
         label=f'線形回帰: y = {coeffs[0]:.3f}x + {coeffs[1]:.1f}\nR² = {r2:.4f}')
ax1.set_xlabel('文字数', fontsize=12)
ax1.set_ylabel('OCR処理時間 (ms)', fontsize=12)
ax1.set_title('OCR処理時間 vs 文字数\n(Windows.Media.Ocr on Windows 11)', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left')

# SLA基準線（400ms）
ax1.axhline(y=400, color='orange', linestyle='--', alpha=0.6, label='SLA目標 (400ms)')
ax1.legend(loc='upper left')

# 右: 文字あたりのコスト（ms/文字）
ms_per_char = ocr_ms / chars
ax2.scatter(chars, ms_per_char, s=80, alpha=0.7, color='green')
ax2.set_xlabel('文字数', fontsize=12)
ax2.set_ylabel('処理コスト (ms/文字)', fontsize=12)
ax2.set_title('文字あたりの処理コスト\n（線形なら一定、非線形なら増加）', fontsize=14, fontweight='bold')
ax2.grid(True, alpha=0.3)

# 平均線
avg_cost = np.mean(ms_per_char)
ax2.axhline(y=avg_cost, color='red', linestyle='--', alpha=0.6, 
            label=f'平均: {avg_cost:.3f} ms/文字')
ax2.legend()

plt.tight_layout()
plt.savefig('outputs/ocr_benchmark.png', dpi=150, bbox_inches='tight')
print(f"✅ グラフ保存: outputs/ocr_benchmark.png")
print(f"\n[分析結果]")
print(f"線形回帰式: OCR時間 = {coeffs[0]:.3f} * 文字数 + {coeffs[1]:.1f}")
print(f"決定係数 R² = {r2:.4f}")
print(f"文字あたり平均コスト: {avg_cost:.3f} ms/文字")

if r2 > 0.95:
    print("✅ 結論: ほぼ完全な線形関係")
elif r2 > 0.85:
    print("⚠️  結論: おおむね線形（800文字以上で非線形要素増加）")
else:
    print("❌ 結論: 非線形（文字数以外の要因が支配的）")

print(f"\n[実用ガイドライン]")
for c in [50, 100, 200, 500, 1000]:
    predicted = linear_fit(c)
    print(f"  {c:4}文字 → 予測: {predicted:6.1f}ms")

plt.show()
