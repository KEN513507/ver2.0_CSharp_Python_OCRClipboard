"""マハラノビス距離による外れ値分析（統計的に堅牢な版）"""
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.spatial.distance import mahalanobis
from scipy.stats import chi2
from sklearn.decomposition import PCA
from sklearn.covariance import LedoitWolf
from sklearn.preprocessing import RobustScaler
import warnings

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Meiryo']
plt.rcParams['axes.unicode_minus'] = False
warnings.filterwarnings('ignore', category=RuntimeWarning)


def extract_text_features(text):
    """テキストから特徴量を抽出"""
    if not text:
        return np.zeros(8)
    
    total_chars = len(text)
    hiragana = sum(1 for c in text if '\u3040' <= c <= '\u309F')
    katakana = sum(1 for c in text if '\u30A0' <= c <= '\u30FF')
    kanji = sum(1 for c in text if '\u4E00' <= c <= '\u9FFF')
    ascii = sum(1 for c in text if ord(c) < 128)
    digit = sum(1 for c in text if c.isdigit())
    space = sum(1 for c in text if c.isspace())
    symbol = total_chars - (hiragana + katakana + kanji + ascii)
    
    return np.array([
        total_chars,
        hiragana / total_chars if total_chars > 0 else 0,
        katakana / total_chars if total_chars > 0 else 0,
        kanji / total_chars if total_chars > 0 else 0,
        ascii / total_chars if total_chars > 0 else 0,
        digit / total_chars if total_chars > 0 else 0,
        space / total_chars if total_chars > 0 else 0,
        symbol / total_chars if total_chars > 0 else 0,
    ])


def load_expected_texts():
    """正解テキストを読み込み"""
    root = Path("test_images/set1")
    expected = {}
    
    for i in range(1, 13):
        file_id = f"{i:03d}"
        # manifest.csvから正解テキストファイル名を取得
        txt_files = [
            "001__JP__clean.txt",
            "002__JP__clean-dense.txt",
            "003__JP__small.txt",
            "004__JP__large.txt",
            "005__JP__lowcontrast.txt",
            "006__JP__invert-small.txt",
            "007__JP__tilt2.txt",
            "008__JP__mono-code.txt",
            "009__EN__clean.txt",
            "010__EN__mono-code.txt",
            "011__MIX__clean.txt",
            "012__MIX__lowcontrast-dense.txt"
        ]
        
        if i <= len(txt_files):
            txt_path = root / txt_files[i-1]
            if txt_path.exists():
                expected[file_id] = txt_path.read_text(encoding='utf-8')
    
    return expected


def compute_loo_distances(X):
    """Leave-One-Out マハラノビス距離（自己有利バイアス除去）"""
    n = len(X)
    loo_distances = []
    
    for i in range(n):
        # i番目を除外して平均・共分散推定
        X_loo = np.delete(X, i, axis=0)
        mean_loo = X_loo.mean(axis=0)
        
        # Ledoit-Wolf正則化（n小でも安定）
        lw = LedoitWolf()
        lw.fit(X_loo)
        precision = lw.precision_
        
        # マハラノビス距離
        diff = X[i] - mean_loo
        d = np.sqrt(diff @ precision @ diff)
        loo_distances.append(d)
    
    return np.array(loo_distances)


def bootstrap_threshold(X, n_boot=1000, alpha=0.95):
    """ブートストラップによる経験的閾値算出"""
    n, d = X.shape
    boot_max_distances = []
    
    for _ in range(n_boot):
        # 再標本化
        idx = np.random.choice(n, n, replace=True)
        X_boot = X[idx]
        
        # LOO距離計算
        distances = compute_loo_distances(X_boot)
        boot_max_distances.append(np.max(distances))
    
    # 95%点を閾値とする
    threshold = np.percentile(boot_max_distances, alpha * 100)
    return threshold


def main():
    # データ読み込み
    json_path = Path("tests/outputs/ocr_dataset_eval.json")
    with open(json_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    expected_texts = load_expected_texts()
    
    # 特徴量抽出
    features = []
    ids = []
    cer_values = []
    tags_list = []
    
    for r in results:
        file_id = r['id']
        if file_id in expected_texts:
            feat = extract_text_features(expected_texts[file_id])
            features.append(feat)
            ids.append(file_id)
            cer_values.append(r['cer'])
            tags_list.append(r.get('tags', ''))
    
    X_raw = np.array(features)
    
    # 1. NaN/定数列チェック
    valid_cols = []
    for j in range(X_raw.shape[1]):
        col = X_raw[:, j]
        if not np.any(np.isnan(col)) and np.std(col) > 1e-10:
            valid_cols.append(j)
    
    X_clean = X_raw[:, valid_cols]
    print(f"📊 特徴量健全性チェック")
    print(f"   元次元: {X_raw.shape[1]} → 有効次元: {X_clean.shape[1]}")
    
    # 2. ロバストスケーリング（median/IQR）
    scaler = RobustScaler()
    X = scaler.fit_transform(X_clean)
    
    # 3. LOO距離計算（自己有利バイアス除去）
    loo_distances = compute_loo_distances(X)
    
    # 4. 理論的閾値（Ledoit-Wolf共分散のrank使用）
    lw = LedoitWolf()
    lw.fit(X)
    cov_rank = np.linalg.matrix_rank(lw.covariance_)
    threshold_theory = np.sqrt(chi2.ppf(0.95, df=cov_rank))
    
    # 5. ブートストラップ閾値（経験的）
    print(f"   ブートストラップ中（1000回）...", end='', flush=True)
    threshold_boot = bootstrap_threshold(X, n_boot=1000, alpha=0.95)
    print(f" 完了")
    
    # 閾値の最終決定（保守的に大きい方）
    threshold = max(threshold_theory, threshold_boot)
    
    print(f"\n📊 マハラノビス距離分析（LOO + 正則化）")
    print(f"   有効特徴量次元: {X.shape[1]} (共分散rank={cov_rank})")
    print(f"   理論閾値（χ²₍{cov_rank},0.95₎）: {threshold_theory:.3f}")
    print(f"   経験閾値（bootstrap 95%）: {threshold_boot:.3f}")
    print(f"   採用閾値（保守的）: {threshold:.3f}\n")
    
    for file_id, d, cer, tags in zip(ids, loo_distances, cer_values, tags_list):
        status = "⚠️外れ値" if d > threshold else "✅正常"
        print(f"   {file_id} ({tags:20s}): LOO距離={d:.3f} CER={cer:.3f} {status}")
    
    # PCAで2次元に投影
    pca = PCA(n_components=2)
    X_2d = pca.fit_transform(X)
    
    # QQプロット用にD²をχ²分布と比較
    d_squared = loo_distances ** 2
    d_squared_sorted = np.sort(d_squared)
    theoretical_quantiles = chi2.ppf(np.linspace(0.01, 0.99, len(d_squared_sorted)), df=cov_rank)
    
    # 可視化
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    
    # 左上: PCA散布図（8D距離を色で表現）
    ax = axes[0, 0]
    scatter = ax.scatter(X_2d[:, 0], X_2d[:, 1], c=loo_distances, cmap='coolwarm', 
                         s=150, alpha=0.8, edgecolors='black', linewidth=1.5)
    
    for i, (x, y) in enumerate(X_2d):
        ax.annotate(ids[i], (x, y), fontsize=9, ha='right', fontweight='bold')
    
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('LOO マハラノビス距離', fontsize=11)
    
    ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)', fontsize=12)
    ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)', fontsize=12)
    ax.set_title('PCA 2D投影（色=8次元LOO距離）', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # 右上: LOO距離 vs CER
    ax = axes[0, 1]
    colors = ['red' if d > threshold else 'blue' for d in loo_distances]
    ax.scatter(loo_distances, cer_values, c=colors, s=120, alpha=0.7, edgecolors='black', linewidth=1.5)
    
    for i, (d, cer) in enumerate(zip(loo_distances, cer_values)):
        ax.annotate(ids[i], (d, cer), fontsize=9, ha='left')
    
    ax.axvline(threshold_theory, color='orange', linestyle=':', linewidth=2, label=f'理論閾値={threshold_theory:.2f}')
    ax.axvline(threshold_boot, color='green', linestyle='-.', linewidth=2, label=f'経験閾値={threshold_boot:.2f}')
    ax.axvline(threshold, color='red', linestyle='--', linewidth=2.5, label=f'採用閾値={threshold:.2f}')
    ax.set_xlabel('LOO マハラノビス距離', fontsize=12)
    ax.set_ylabel('CER', fontsize=12)
    ax.set_title('距離 vs OCR精度（3種の閾値比較）', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    
    # 左下: QQプロット（D² vs χ²分布）
    ax = axes[1, 0]
    ax.scatter(theoretical_quantiles, d_squared_sorted, s=80, alpha=0.7, edgecolors='black')
    
    # 理想線（y=x）
    lim_max = max(theoretical_quantiles.max(), d_squared_sorted.max())
    ax.plot([0, lim_max], [0, lim_max], 'r--', linewidth=2, label='理想線 (y=x)')
    
    for i, (tq, ds) in enumerate(zip(theoretical_quantiles[::2], d_squared_sorted[::2])):
        if i % 2 == 0:
            ax.annotate(ids[np.where(d_squared == ds)[0][0]], (tq, ds), fontsize=8, alpha=0.6)
    
    ax.set_xlabel(f'χ²分布 理論分位点 (df={cov_rank})', fontsize=12)
    ax.set_ylabel('観測 D² 分位点', fontsize=12)
    ax.set_title('QQプロット（多変量正規性検証）', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # 右下: 距離ランキング
    ax = axes[1, 1]
    sorted_idx = np.argsort(loo_distances)[::-1]
    sorted_ids = [ids[i] for i in sorted_idx]
    sorted_distances = loo_distances[sorted_idx]
    sorted_colors = ['red' if d > threshold else 'blue' for d in sorted_distances]
    
    y_pos = np.arange(len(sorted_ids))
    ax.barh(y_pos, sorted_distances, color=sorted_colors, alpha=0.7, edgecolor='black')
    ax.axvline(threshold, color='red', linestyle='--', linewidth=2, label=f'閾値={threshold:.2f}')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(sorted_ids, fontsize=10)
    ax.set_xlabel('LOO マハラノビス距離', fontsize=12)
    ax.set_title('距離ランキング（降順）', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig('tests/outputs/ocr_mahalanobis_robust.png', dpi=300, bbox_inches='tight')
    print(f"\n✅ 堅牢グラフ保存: tests/outputs/ocr_mahalanobis_robust.png")


if __name__ == "__main__":
    main()
