"""マハラノビス距離を使ってOCRテストデータの外れ値度を分析"""
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.spatial.distance import mahalanobis
from scipy.stats import chi2

# 日本語フォント設定
plt.rcParams['font.family'] = ['MS Gothic', 'Yu Gothic', 'Meiryo', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False


def extract_text_features(text: str) -> np.ndarray:
    """テキストから特徴量を抽出
    
    特徴量:
    1. 文字数
    2. 行数
    3. ASCII文字率
    4. 日本語文字率
    5. 数字率
    6. 記号率
    7. 空白率
    8. 平均行長
    9. 最大行長
    10. 最小行長
    """
    if not text:
        return np.zeros(10)
    
    lines = text.splitlines()
    num_lines = len(lines) if lines else 1
    num_chars = len(text)
    
    # 文字種別カウント
    ascii_count = sum(1 for c in text if ord(c) < 128)
    japanese_count = sum(1 for c in text if ord(c) >= 0x3040)  # ひらがな、カタカナ、漢字
    digit_count = sum(1 for c in text if c.isdigit())
    symbol_count = sum(1 for c in text if not c.isalnum() and not c.isspace())
    space_count = sum(1 for c in text if c.isspace())
    
    # 率の計算
    ascii_ratio = ascii_count / num_chars if num_chars > 0 else 0
    japanese_ratio = japanese_count / num_chars if num_chars > 0 else 0
    digit_ratio = digit_count / num_chars if num_chars > 0 else 0
    symbol_ratio = symbol_count / num_chars if num_chars > 0 else 0
    space_ratio = space_count / num_chars if num_chars > 0 else 0
    
    # 行長の統計
    line_lengths = [len(line) for line in lines if line]
    avg_line_length = np.mean(line_lengths) if line_lengths else 0
    max_line_length = max(line_lengths) if line_lengths else 0
    min_line_length = min(line_lengths) if line_lengths else 0
    
    return np.array([
        num_chars,
        num_lines,
        ascii_ratio,
        japanese_ratio,
        digit_ratio,
        symbol_ratio,
        space_ratio,
        avg_line_length,
        max_line_length,
        min_line_length
    ])


def calculate_mahalanobis_distances(results: list) -> dict:
    """マハラノビス距離を計算"""
    # 正解テキストを読み込み
    test_images_dir = Path("test_images/set1")
    
    features_list = []
    ids = []
    
    for result in results:
        file_id = result["id"]
        file_name = result["file"]
        
        # 正解テキストファイルを読み込み
        txt_file = test_images_dir / file_name.replace(".png", ".txt")
        if not txt_file.exists():
            print(f"[WARN] {file_id}: 正解ファイル未発見: {txt_file}")
            continue
        
        expected_text = txt_file.read_text(encoding="utf-8")
        features = extract_text_features(expected_text)
        
        features_list.append(features)
        ids.append(file_id)
    
    if len(features_list) < 2:
        print("[ERROR] 特徴量が不足（最低2件必要）")
        return {}
    
    # 特徴量行列
    X = np.array(features_list)
    
    # 平均と共分散行列
    mean = np.mean(X, axis=0)
    cov = np.cov(X, rowvar=False)
    
    # 共分散行列の逆行列（特異行列対策）
    try:
        cov_inv = np.linalg.inv(cov)
    except np.linalg.LinAlgError:
        print("[WARN] 共分散行列が特異行列のため、疑似逆行列を使用")
        cov_inv = np.linalg.pinv(cov)
    
    # マハラノビス距離を計算
    distances = {}
    for i, (file_id, features) in enumerate(zip(ids, features_list)):
        dist = mahalanobis(features, mean, cov_inv)
        distances[file_id] = dist
    
    return distances, mean, cov_inv


def plot_mahalanobis_distances(results: list, distances: dict, output_dir: Path):
    """マハラノビス距離を可視化"""
    # データ準備
    ids = []
    dists = []
    cers = []
    quality_oks = []
    
    for result in results:
        file_id = result["id"]
        if file_id in distances:
            ids.append(file_id)
            dists.append(distances[file_id])
            cers.append(result["cer"])
            quality_oks.append(result["quality_ok"])
    
    if not ids:
        print("[ERROR] プロット用データなし")
        return
    
    # カイ二乗分布の95%点（自由度=特徴量数=10）
    chi2_threshold = chi2.ppf(0.95, df=10)
    mahal_threshold = np.sqrt(chi2_threshold)
    
    # グラフ1: マハラノビス距離の棒グラフ
    fig, ax = plt.subplots(figsize=(14, 6), dpi=300)
    
    colors = ['green' if qok else 'red' for qok in quality_oks]
    bars = ax.bar(range(len(ids)), dists, color=colors, alpha=0.7, edgecolor='black')
    
    # 閾値線
    ax.axhline(y=mahal_threshold, color='orange', linestyle='--', linewidth=2, 
               label=f'外れ値閾値 (95%点): {mahal_threshold:.2f}')
    
    ax.set_xlabel('画像ID', fontsize=12, fontweight='bold')
    ax.set_ylabel('マハラノビス距離', fontsize=12, fontweight='bold')
    ax.set_title('OCRテストデータの外れ値分析（マハラノビス距離）', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(ids)))
    ax.set_xticklabels(ids, rotation=45, ha='right')
    ax.grid(axis='y', alpha=0.3)
    ax.legend(fontsize=10)
    
    # 凡例追加
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='green', alpha=0.7, label='合格 (CER≤0.15)'),
        Patch(facecolor='red', alpha=0.7, label='不合格 (CER>0.15)')
    ]
    ax.legend(handles=legend_elements + [ax.get_lines()[0]], loc='upper left', fontsize=10)
    
    plt.tight_layout()
    output_path = output_dir / "ocr_mahalanobis_distance.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ マハラノビス距離グラフ保存: {output_path}")
    
    # グラフ2: マハラノビス距離 vs CER散布図
    fig, ax = plt.subplots(figsize=(10, 8), dpi=300)
    
    scatter = ax.scatter(dists, cers, c=colors, s=100, alpha=0.7, edgecolors='black')
    
    # 各点にIDラベルを追加
    for i, file_id in enumerate(ids):
        ax.annotate(file_id, (dists[i], cers[i]), 
                   xytext=(5, 5), textcoords='offset points', fontsize=9)
    
    # 閾値線
    ax.axvline(x=mahal_threshold, color='orange', linestyle='--', linewidth=2, 
               label=f'外れ値閾値: {mahal_threshold:.2f}')
    ax.axhline(y=0.15, color='blue', linestyle='--', linewidth=2, 
               label='CER合格ライン: 0.15')
    
    ax.set_xlabel('マハラノビス距離', fontsize=12, fontweight='bold')
    ax.set_ylabel('CER（文字誤り率）', fontsize=12, fontweight='bold')
    ax.set_title('外れ値度 vs OCR精度', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    
    plt.tight_layout()
    output_path = output_dir / "ocr_mahalanobis_vs_cer.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ マハラノビス vs CER散布図保存: {output_path}")
    
    # 統計情報表示
    print(f"\n📊 マハラノビス距離統計:")
    print(f"   平均: {np.mean(dists):.3f}")
    print(f"   中央値: {np.median(dists):.3f}")
    print(f"   最大: {np.max(dists):.3f} ({ids[np.argmax(dists)]})")
    print(f"   最小: {np.min(dists):.3f} ({ids[np.argmin(dists)]})")
    print(f"   外れ値閾値: {mahal_threshold:.3f}")
    
    outliers = [ids[i] for i, d in enumerate(dists) if d > mahal_threshold]
    if outliers:
        print(f"   外れ値: {', '.join(outliers)}")
    else:
        print(f"   外れ値: なし")


def main():
    # データ読み込み
    json_path = Path("tests/outputs/ocr_dataset_eval.json")
    
    if not json_path.exists():
        print(f"[ERROR] {json_path} が見つかりません")
        return
    
    with open(json_path, "r", encoding="utf-8") as f:
        results = json.load(f)
    
    print(f"📊 データ読み込み: {json_path}")
    print(f"   {len(results)}件のテスト結果\n")
    
    # マハラノビス距離を計算
    print("🔢 マハラノビス距離計算中...")
    distances, mean, cov_inv = calculate_mahalanobis_distances(results)
    
    if not distances:
        print("[ERROR] マハラノビス距離の計算失敗")
        return
    
    # グラフ生成
    print("\n📈 グラフ生成中...")
    output_dir = Path("tests/outputs")
    plot_mahalanobis_distances(results, distances, output_dir)
    
    print("\n✅ すべてのグラフを tests/outputs に保存しました")


if __name__ == "__main__":
    main()
