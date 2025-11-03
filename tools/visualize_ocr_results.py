#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/visualize_ocr_results.py - OCRテスト結果の可視化 + マハラノビス距離異常検知

使い方:
  python tools/visualize_ocr_results.py --input tests/outputs/ocr_dataset_eval.json
"""

import argparse
import json
import pathlib
import sys
from datetime import datetime
from collections import defaultdict, Counter

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import scipy.stats as stats
from sklearn.covariance import LedoitWolf

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 距離単位の固定（D²で統一）
# 注意: 以下の閾値は標準化なしの正しいマハラノビス距離用に再調整が必要
THEORETICAL_THRESHOLD_D2 = 15.51  # χ²(df=8) 95%点（理論値）
EMPIRICAL_THRESHOLD_D2 = 26.0     # 実データに基づく閾値（要再推定）
WARNING_THRESHOLD_D2 = 18.0       # 準異常閾値（要再推定）


def load_results(json_path: pathlib.Path):
    """JSONファイルからテスト結果を読み込む"""
    with json_path.open(encoding='utf-8') as f:
        return json.load(f)


def extract_features(results):
    """テスト結果から8次元特徴量を抽出"""
    features = []
    for r in results:
        # 8次元特徴量の構成
        feature_vector = [
            r.get('cer', 0.0),                    # 1. CER
            r.get('latency_ms', 0.0),             # 2. レイテンシ
            len(r.get('detected_text', '')),       # 3. 検出文字数
            len(r.get('ground_truth', '')),        # 4. 正解文字数
            r.get('confidence', 1.0),              # 5. 信頼度
            len(r.get('dt_boxes', [])),            # 6. 検出ボックス数
            r.get('ocr_ms', 0.0),                  # 7. OCR処理時間
            r.get('post_ms', 0.0),                 # 8. 後処理時間
        ]
        features.append(feature_vector)
    return np.array(features)


def compute_mahalanobis_distances(features, cov_estimator='ledoit_wolf'):
    """マハラノビス距離（D²）を計算 - Leave-One-Out方式
    
    正しいマハラノビス距離の定義:
    D² = (x - μ)ᵀ Σ⁻¹ (x - μ)
    
    ここで:
    - x: テストサンプル
    - μ: 訓練データの平均ベクトル
    - Σ: 訓練データの共分散行列
    
    注意: 標準化は不要。マハラノビス距離自体がスケール不変。
    """
    n_samples, n_features = features.shape
    distances_d2 = []
    
    for i in range(n_samples):
        # LOO: i番目のサンプルを除いた訓練データ
        train_mask = np.ones(n_samples, dtype=bool)
        train_mask[i] = False
        X_train = features[train_mask]  # 元データを使用（標準化なし）
        
        # 訓練データの平均ベクトル
        center = X_train.mean(axis=0)
        
        # 共分散行列推定
        if cov_estimator == 'ledoit_wolf':
            # Ledoit-Wolf推定（少数標本に適用）
            cov_est = LedoitWolf()
            cov_est.fit(X_train)
            cov_matrix = cov_est.covariance_
        else:
            # 経験共分散
            cov_matrix = np.cov(X_train.T)
        
        # 共分散行列の逆行列
        try:
            cov_inv = np.linalg.inv(cov_matrix)
        except np.linalg.LinAlgError:
            # 逆行列が計算できない場合は擬似逆行列を使用
            cov_inv = np.linalg.pinv(cov_matrix)
        
        # テストサンプル（i番目）のマハラノビス距離D²を計算
        test_sample = features[i]  # 元データを使用（標準化なし）
        diff = test_sample - center
        d_squared = np.dot(np.dot(diff, cov_inv), diff)
        distances_d2.append(d_squared)
    
    return np.array(distances_d2), cov_estimator


def classify_anomaly_level(distance_d2):
    """マハラノビス距離D²に基づく異常レベル分類"""
    if distance_d2 > EMPIRICAL_THRESHOLD_D2:
        return 'strong_anomaly', 'degrade'
    elif distance_d2 > WARNING_THRESHOLD_D2:
        return 'weak_anomaly', 'warn'
    else:
        return 'normal', 'normal'


def create_mahalanobis_analysis(results, distances_d2, output_dir: pathlib.Path):
    """マハラノビス距離の分析・可視化"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. 距離ヒストグラム + 閾値
    ax1.hist(distances_d2, bins=15, alpha=0.7, color='skyblue', edgecolor='black')
    ax1.axvline(THEORETICAL_THRESHOLD_D2, color='red', linestyle='--', linewidth=2, 
                label=f'理論: χ²95% (={THEORETICAL_THRESHOLD_D2:.1f})')
    ax1.axvline(EMPIRICAL_THRESHOLD_D2, color='orange', linestyle='-', linewidth=2,
                label=f'経験: 95% (={EMPIRICAL_THRESHOLD_D2:.1f})')
    ax1.axvline(WARNING_THRESHOLD_D2, color='yellow', linestyle=':', linewidth=2,
                label=f'準異常 (={WARNING_THRESHOLD_D2:.1f})')
    ax1.set_xlabel('マハラノビス距離 D²', fontsize=10, fontweight='bold')
    ax1.set_ylabel('頻度', fontsize=10, fontweight='bold')
    ax1.set_title('LOO距離分布と閾値', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(alpha=0.3)
    
    # 2. QQプロット（正規性チェック）
    stats.probplot(distances_d2, dist="chi2", sparams=(8,), plot=ax2)
    ax2.set_title('QQプロット (χ²分布, df=8)', fontsize=12, fontweight='bold')
    ax2.grid(alpha=0.3)
    
    # 3. タグ別距離
    tag_distances = defaultdict(list)
    for r, d in zip(results, distances_d2):
        tags = r['tags'].split('-')
        for tag in tags:
            tag_distances[tag].append(d)
    
    # タグをソート
    sorted_tags = sorted(tag_distances.items(), key=lambda x: np.median(x[1]))
    tags = [t[0] for t in sorted_tags]
    data = [t[1] for t in sorted_tags]
    
    bp = ax3.boxplot(data, tick_labels=tags, patch_artist=True, notch=True)
    for patch in bp['boxes']:
        patch.set_facecolor('lightcoral')
        patch.set_alpha(0.7)
    
    ax3.axhline(EMPIRICAL_THRESHOLD_D2, color='orange', linestyle='-', linewidth=2)
    ax3.axhline(WARNING_THRESHOLD_D2, color='yellow', linestyle=':', linewidth=2)
    ax3.set_ylabel('マハラノビス距離 D²', fontsize=10, fontweight='bold')
    ax3.set_title('タグ別異常度分布', fontsize=12, fontweight='bold')
    ax3.tick_params(axis='x', rotation=45)
    ax3.grid(alpha=0.3)
    
    # 4. 距離 vs CER散布図
    cers = [r['cer'] for r in results]
    ids = [r['id'] for r in results]
    
    # 異常レベル別の色分け
    colors = []
    for d in distances_d2:
        level, _ = classify_anomaly_level(d)
        if level == 'strong_anomaly':
            colors.append('#e74c3c')  # 赤
        elif level == 'weak_anomaly':
            colors.append('#f39c12')  # オレンジ
        else:
            colors.append('#2ecc71')  # 緑
    
    scatter = ax4.scatter(distances_d2, cers, c=colors, s=100, alpha=0.7, edgecolors='black')
    
    # IDラベル（異常のみ）
    for i, (d, cer, id_) in enumerate(zip(distances_d2, cers, ids)):
        if d > WARNING_THRESHOLD_D2:
            ax4.annotate(id_, (d, cer), fontsize=8, ha='center', va='bottom')
    
    ax4.axvline(EMPIRICAL_THRESHOLD_D2, color='orange', linestyle='-', linewidth=2)
    ax4.axvline(WARNING_THRESHOLD_D2, color='yellow', linestyle=':', linewidth=2)
    ax4.set_xlabel('マハラノビス距離 D²', fontsize=10, fontweight='bold')
    ax4.set_ylabel('CER', fontsize=10, fontweight='bold')
    ax4.set_title('異常度 vs CER', fontsize=12, fontweight='bold')
    ax4.grid(alpha=0.3)
    
    # 凡例
    normal_patch = mpatches.Patch(color='#2ecc71', alpha=0.7, label='通常運転')
    warn_patch = mpatches.Patch(color='#f39c12', alpha=0.7, label='準異常')
    strong_patch = mpatches.Patch(color='#e74c3c', alpha=0.7, label='強い異常')
    ax4.legend(handles=[normal_patch, warn_patch, strong_patch], fontsize=9)
    
    plt.suptitle('マハラノビス距離による異常検知分析', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    output_path = output_dir / 'mahalanobis_analysis.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ マハラノビス分析保存: {output_path}")
    plt.close()


def create_operational_log(results, distances_d2, output_dir: pathlib.Path, cov_version='LedoitWolf'):
    """運用ログ（JSON Lines）の出力"""
    log_path = output_dir / f'ocr_operational_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl'
    
    with open(log_path, 'w', encoding='utf-8') as f:
        for r, distance_d2 in zip(results, distances_d2):
            level, decision = classify_anomaly_level(distance_d2)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'image_id': r['id'],
                'tag': r['tags'],
                
                # 特徴量（運用監視用）
                'features_raw': {
                    'cer': r.get('cer', 0.0),
                    'latency_ms': r.get('latency_ms', 0.0),
                    'detected_chars': len(r.get('detected_text', '')),
                    'ground_truth_chars': len(r.get('ground_truth', '')),
                    'confidence': r.get('confidence', 1.0),
                    'dt_boxes_count': len(r.get('dt_boxes', [])),
                    'ocr_ms': r.get('ocr_ms', 0.0),
                    'post_ms': r.get('post_ms', 0.0),
                },
                
                # 異常検知
                'anomaly_detection': {
                    'mahal_distance_d2': float(distance_d2),
                    'cov_version': cov_version,
                    'thresholds': {
                        'theory_d2': THEORETICAL_THRESHOLD_D2,
                        'empirical_d2': EMPIRICAL_THRESHOLD_D2,
                        'warning_d2': WARNING_THRESHOLD_D2
                    },
                    'level': level,
                    'decision': decision,
                    'rationale': f'D²={distance_d2:.2f} vs 閾値={EMPIRICAL_THRESHOLD_D2}'
                },
                
                # 品質指標
                'quality_metrics': {
                    'cer': r.get('cer', 0.0),
                    'levenshtein': r.get('levenshtein_distance', 0),
                    'rule_used': 'empirical_95pct',
                    'quality_ok': r.get('quality_ok', False)
                },
                
                # パフォーマンス
                'performance': {
                    'proc_total_ms': r.get('latency_ms', 0.0),
                    'ocr_ms': r.get('ocr_ms', 0.0),
                    'post_ms': r.get('post_ms', 0.0),
                    'engine': r.get('engine', 'unknown')
                }
            }
            
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    print(f"✅ 運用ログ出力: {log_path}")
    return log_path


def create_cer_bar_chart(results, distances_d2, output_dir: pathlib.Path, threshold: float = 0.30):
    """CERの棒グラフを作成（異常検知統合版）"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[2, 1])
    
    ids = [r['id'] for r in results]
    cers = [r['cer'] for r in results]
    tags = [r['tags'] for r in results]
    quality_ok = [r['quality_ok'] for r in results]
    
    # 異常レベル別の色分け
    colors = []
    for d in distances_d2:
        level, _ = classify_anomaly_level(d)
        if level == 'strong_anomaly':
            colors.append('#e74c3c')  # 赤：強い異常
        elif level == 'weak_anomaly':
            colors.append('#f39c12')  # オレンジ：準異常
        else:
            colors.append('#2ecc71')  # 緑：通常
    
    # 上段：CER棒グラフ
    bars = ax1.bar(ids, cers, color=colors, alpha=0.7, edgecolor='black', linewidth=1.2)
    ax1.axhline(y=threshold, color='purple', linestyle='--', linewidth=2, label=f'CER閾値={threshold}')
    
    ax1.set_xlabel('画像ID', fontsize=12, fontweight='bold')
    ax1.set_ylabel('CER (Character Error Rate)', fontsize=12, fontweight='bold')
    ax1.set_title('OCR精度評価結果（異常検知統合版）- PaddleOCR 2.7.0.3', fontsize=14, fontweight='bold')
    ax1.set_ylim(0, 1.0)
    ax1.grid(axis='y', alpha=0.3, linestyle=':', linewidth=0.8)
    
    # タグをX軸ラベルに追加
    ax1.set_xticks(range(len(ids)))
    ax1.set_xticklabels([f"{id_}\n({tag})" for id_, tag in zip(ids, tags)], 
                        rotation=45, ha='right', fontsize=9)
    
    # CER値を棒の上に表示
    for bar, cer in zip(bars, cers):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{cer:.3f}', ha='center', va='bottom', fontsize=8, fontweight='bold')
    
    # 下段：マハラノビス距離D²
    bars2 = ax2.bar(ids, distances_d2, color=colors, alpha=0.7, edgecolor='black', linewidth=1.2)
    ax2.axhline(y=EMPIRICAL_THRESHOLD_D2, color='orange', linestyle='-', linewidth=2, 
                label=f'経験95% (={EMPIRICAL_THRESHOLD_D2:.1f})')
    ax2.axhline(y=WARNING_THRESHOLD_D2, color='yellow', linestyle=':', linewidth=2,
                label=f'準異常 (={WARNING_THRESHOLD_D2:.1f})')
    ax2.axhline(y=THEORETICAL_THRESHOLD_D2, color='red', linestyle='--', linewidth=1,
                label=f'理論95% (={THEORETICAL_THRESHOLD_D2:.1f})')
    
    ax2.set_xlabel('画像ID', fontsize=12, fontweight='bold')
    ax2.set_ylabel('マハラノビス距離 D²', fontsize=12, fontweight='bold')
    ax2.set_title('異常検知スコア（D²ベース）', fontsize=12, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3, linestyle=':', linewidth=0.8)
    ax2.legend(fontsize=9, loc='upper left')
    
    # D²値を棒の上に表示
    for bar, d in zip(bars2, distances_d2):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{d:.1f}', ha='center', va='bottom', fontsize=8, fontweight='bold')
    
    # 凡例（上段）
    normal_patch = mpatches.Patch(color='#2ecc71', alpha=0.7, label='通常運転')
    warn_patch = mpatches.Patch(color='#f39c12', alpha=0.7, label='準異常（要観察）')
    strong_patch = mpatches.Patch(color='#e74c3c', alpha=0.7, label='強い異常（デグレード）')
    cer_line = ax1.get_lines()[0]
    ax1.legend(handles=[normal_patch, warn_patch, strong_patch, cer_line], 
              loc='upper left', fontsize=10)
    
    # 統計情報をテキストで追加
    passed = sum(quality_ok)
    total = len(results)
    pass_rate = (passed / total) * 100
    avg_cer = np.mean(cers)
    anomaly_count = sum(1 for d in distances_d2 if d > WARNING_THRESHOLD_D2)
    
    stats_text = (f'合格率: {passed}/{total} ({pass_rate:.1f}%)\n'
                  f'平均CER: {avg_cer:.3f}\n'
                  f'異常検知: {anomaly_count}/{total}件')
    ax1.text(0.98, 0.98, stats_text, transform=ax1.transAxes,
            fontsize=11, verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    output_path = output_dir / 'ocr_integrated_analysis.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ 統合分析保存: {output_path}")
    plt.close()


def create_engine_comparison(results, output_dir: pathlib.Path):
    """エンジン別の使用状況を円グラフで表示"""
    from collections import Counter
    
    engines = [r['engine'] for r in results]
    engine_counts = Counter(engines)
    
    fig, ax = plt.subplots(figsize=(8, 8))
    
    labels = list(engine_counts.keys())
    sizes = list(engine_counts.values())
    colors = ['#3498db', '#e67e22', '#95a5a6']
    
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                                        startangle=90, textprops={'fontsize': 12, 'fontweight': 'bold'})
    
    ax.set_title('使用エンジン分布', fontsize=14, fontweight='bold', pad=20)
    
    # 凡例
    ax.legend(wedges, [f'{label}: {count}件' for label, count in engine_counts.items()],
              loc='upper left', bbox_to_anchor=(1, 0, 0.5, 1), fontsize=10)
    
    plt.tight_layout()
    output_path = output_dir / 'ocr_engine_distribution.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ 円グラフ保存: {output_path}")
    plt.close()


def create_tag_analysis(results, distances_d2, output_dir: pathlib.Path, threshold: float = 0.30):
    """タグ別のCER分布＋異常検知分析"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 10))
    
    # タグ別データ整理
    tag_cers = defaultdict(list)
    tag_distances = defaultdict(list)
    tag_samples = defaultdict(list)
    
    for i, r in enumerate(results):
        tags = r['tags'].split('-')
        for tag in tags:
            tag_cers[tag].append(r['cer'])
            tag_distances[tag].append(distances_d2[i])
            tag_samples[tag].append(r['id'])
    
    # タグをCERの中央値でソート
    sorted_tags = sorted(tag_cers.items(), key=lambda x: np.median(x[1]))
    tags = [t[0] for t in sorted_tags]
    
    # 1. CER箱ひげ図
    cer_data = [tag_cers[tag] for tag in tags]
    bp1 = ax1.boxplot(cer_data, tick_labels=tags, patch_artist=True, notch=True,
                      boxprops=dict(facecolor='lightblue', alpha=0.7),
                      medianprops=dict(color='red', linewidth=2))
    
    ax1.axhline(y=threshold, color='orange', linestyle='--', linewidth=2, 
                label=f'CER閾値={threshold}')
    ax1.set_ylabel('CER', fontsize=10, fontweight='bold')
    ax1.set_title('タグ別CER分布', fontsize=12, fontweight='bold')
    ax1.set_ylim(0, 1.0)
    ax1.grid(axis='y', alpha=0.3)
    ax1.legend(fontsize=9)
    ax1.tick_params(axis='x', rotation=45)
    
    # 2. マハラノビス距離箱ひげ図
    distance_data = [tag_distances[tag] for tag in tags]
    bp2 = ax2.boxplot(distance_data, tick_labels=tags, patch_artist=True, notch=True,
                      boxprops=dict(facecolor='lightcoral', alpha=0.7),
                      medianprops=dict(color='blue', linewidth=2))
    
    ax2.axhline(y=EMPIRICAL_THRESHOLD_D2, color='orange', linestyle='-', linewidth=2,
                label=f'経験95% (={EMPIRICAL_THRESHOLD_D2:.1f})')
    ax2.axhline(y=WARNING_THRESHOLD_D2, color='yellow', linestyle=':', linewidth=2,
                label=f'準異常 (={WARNING_THRESHOLD_D2:.1f})')
    ax2.set_ylabel('マハラノビス距離 D²', fontsize=10, fontweight='bold')
    ax2.set_title('タグ別異常度分布', fontsize=12, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    ax2.legend(fontsize=9)
    ax2.tick_params(axis='x', rotation=45)
    
    # 3. タグ別異常率
    tag_anomaly_rates = {}
    for tag in tags:
        total_samples = len(tag_distances[tag])
        anomaly_samples = sum(1 for d in tag_distances[tag] if d > WARNING_THRESHOLD_D2)
        tag_anomaly_rates[tag] = (anomaly_samples / total_samples) * 100 if total_samples > 0 else 0
    
    ax3.bar(tags, [tag_anomaly_rates[tag] for tag in tags], 
            color='coral', alpha=0.7, edgecolor='black')
    ax3.set_ylabel('異常率 (%)', fontsize=10, fontweight='bold')
    ax3.set_title('タグ別異常検知率', fontsize=12, fontweight='bold')
    ax3.grid(axis='y', alpha=0.3)
    ax3.tick_params(axis='x', rotation=45)
    
    # 値を棒の上に表示
    for i, rate in enumerate([tag_anomaly_rates[tag] for tag in tags]):
        ax3.text(i, rate + 1, f'{rate:.1f}%', ha='center', va='bottom', fontsize=9)
    
    # 4. サンプル数と品質傾向
    tag_stats = []
    for tag in tags:
        n_samples = len(tag_cers[tag])
        avg_cer = np.mean(tag_cers[tag])
        avg_distance = np.mean(tag_distances[tag])
        tag_stats.append({
            'tag': tag,
            'n_samples': n_samples,
            'avg_cer': avg_cer,
            'avg_distance': avg_distance
        })
    
    # テーブル表示
    table_data = []
    for stat in tag_stats:
        table_data.append([
            stat['tag'],
            str(stat['n_samples']),
            f"{stat['avg_cer']:.3f}",
            f"{stat['avg_distance']:.1f}",
            f"{tag_anomaly_rates[stat['tag']]:.1f}%"
        ])
    
    ax4.axis('tight')
    ax4.axis('off')
    table = ax4.table(cellText=table_data,
                      colLabels=['タグ', 'サンプル数', '平均CER', '平均D²', '異常率'],
                      cellLoc='center',
                      loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)
    ax4.set_title('タグ別統計サマリー', fontsize=12, fontweight='bold', pad=20)
    
    plt.suptitle('タグ別分析（CER + 異常検知統合）', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    output_path = output_dir / 'ocr_tag_analysis_integrated.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ タグ別分析保存: {output_path}")
    plt.close()


def create_performance_scatter(results, distances_d2, output_dir: pathlib.Path, threshold: float = 0.30):
    """CER vs レイテンシの散布図（異常検知統合版）"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    cers = [r['cer'] for r in results]
    latencies = [r['latency_ms'] for r in results]
    ids = [r['id'] for r in results]
    
    # 異常レベル別の色分け
    colors = []
    for d in distances_d2:
        level, _ = classify_anomaly_level(d)
        if level == 'strong_anomaly':
            colors.append('#e74c3c')  # 赤
        elif level == 'weak_anomaly':
            colors.append('#f39c12')  # オレンジ
        else:
            colors.append('#2ecc71')  # 緑
    
    # 1. CER vs レイテンシ
    scatter1 = ax1.scatter(latencies, cers, c=colors, s=150, alpha=0.7, edgecolors='black', linewidth=1.5)
    
    # 異常サンプルのIDラベル
    for i, (lat, cer, id_) in enumerate(zip(latencies, cers, ids)):
        if distances_d2[i] > WARNING_THRESHOLD_D2:
            ax1.annotate(id_, (lat, cer), fontsize=9, fontweight='bold',
                        ha='center', va='bottom', 
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.5))
    
    ax1.axhline(y=threshold, color='purple', linestyle='--', linewidth=2, label=f'CER閾値={threshold}')
    ax1.set_xlabel('処理時間 (ms)', fontsize=10, fontweight='bold')
    ax1.set_ylabel('CER', fontsize=10, fontweight='bold')
    ax1.set_title('CER vs 処理時間（異常検知統合）', fontsize=12, fontweight='bold')
    ax1.set_ylim(0, 1.0)
    ax1.grid(alpha=0.3)
    ax1.legend(fontsize=9)
    
    # 2. マハラノビス距離 vs CER
    scatter2 = ax2.scatter(distances_d2, cers, c=colors, s=150, alpha=0.7, edgecolors='black', linewidth=1.5)
    
    for i, (d, cer, id_) in enumerate(zip(distances_d2, cers, ids)):
        if d > WARNING_THRESHOLD_D2:
            ax2.annotate(id_, (d, cer), fontsize=9, fontweight='bold',
                        ha='center', va='bottom',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.5))
    
    ax2.axvline(x=EMPIRICAL_THRESHOLD_D2, color='orange', linestyle='-', linewidth=2)
    ax2.axvline(x=WARNING_THRESHOLD_D2, color='yellow', linestyle=':', linewidth=2)
    ax2.axhline(y=threshold, color='purple', linestyle='--', linewidth=2)
    ax2.set_xlabel('マハラノビス距離 D²', fontsize=10, fontweight='bold')
    ax2.set_ylabel('CER', fontsize=10, fontweight='bold')
    ax2.set_title('異常度 vs CER', fontsize=12, fontweight='bold')
    ax2.set_ylim(0, 1.0)
    ax2.grid(alpha=0.3)
    
    # 3. マハラノビス距離 vs レイテンシ
    scatter3 = ax3.scatter(distances_d2, latencies, c=colors, s=150, alpha=0.7, edgecolors='black', linewidth=1.5)
    
    ax3.axvline(x=EMPIRICAL_THRESHOLD_D2, color='orange', linestyle='-', linewidth=2)
    ax3.axvline(x=WARNING_THRESHOLD_D2, color='yellow', linestyle=':', linewidth=2)
    ax3.set_xlabel('マハラノビス距離 D²', fontsize=10, fontweight='bold')
    ax3.set_ylabel('処理時間 (ms)', fontsize=10, fontweight='bold')
    ax3.set_title('異常度 vs 処理時間', fontsize=12, fontweight='bold')
    ax3.grid(alpha=0.3)
    
    # 4. 運用決定マトリックス
    decision_counts = {'normal': 0, 'warn': 0, 'degrade': 0}
    decision_examples = {'normal': [], 'warn': [], 'degrade': []}
    
    for i, d in enumerate(distances_d2):
        level, decision = classify_anomaly_level(d)
        decision_counts[decision] += 1
        if len(decision_examples[decision]) < 3:  # 最大3個まで
            decision_examples[decision].append(ids[i])
    
    # 意思決定フローチャート風の表示
    ax4.axis('off')
    
    # タイトル
    ax4.text(0.5, 0.95, '運用意思決定ルール', fontsize=14, fontweight='bold', 
             ha='center', transform=ax4.transAxes)
    
    # ルールの描画
    rules_text = f'''
【D² ≤ {WARNING_THRESHOLD_D2:.0f}】通常運転 ({decision_counts['normal']}件)
　→ 処理続行、標準閾値適用
　例: {', '.join(decision_examples['normal'][:3])}

【{WARNING_THRESHOLD_D2:.0f} < D² ≤ {EMPIRICAL_THRESHOLD_D2:.0f}】準異常 ({decision_counts['warn']}件)  
　→ 要観察、ログ記録、閾値緩和なし
　例: {', '.join(decision_examples['warn'][:3])}

【D² > {EMPIRICAL_THRESHOLD_D2:.0f}】強い異常 ({decision_counts['degrade']}件)
　→ 前処理強化→再試行→フォールバック
　例: {', '.join(decision_examples['degrade'][:3])}
    '''
    
    ax4.text(0.05, 0.8, rules_text, fontsize=11, ha='left', va='top',
             transform=ax4.transAxes, 
             bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.3))
    
    # 全体凡例（右下に配置）
    normal_patch = mpatches.Patch(color='#2ecc71', alpha=0.7, label='通常運転')
    warn_patch = mpatches.Patch(color='#f39c12', alpha=0.7, label='準異常（要観察）')
    strong_patch = mpatches.Patch(color='#e74c3c', alpha=0.7, label='強い異常（デグレード）')
    
    fig.legend(handles=[normal_patch, warn_patch, strong_patch], 
               loc='lower right', fontsize=11, bbox_to_anchor=(0.98, 0.02))
    
    plt.suptitle('パフォーマンス分析（異常検知統合版）', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    output_path = output_dir / 'ocr_performance_integrated.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ パフォーマンス分析保存: {output_path}")
    plt.close()
    print(f"✅ 散布図保存: {output_path}")
    plt.close()


def create_summary_dashboard(results, distances_d2, output_dir: pathlib.Path, threshold: float = 0.30):
    """総合ダッシュボード（異常検知統合版）"""
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.3)
    
    # データ準備
    ids = [r['id'] for r in results]
    cers = [r['cer'] for r in results]
    quality_ok = [r['quality_ok'] for r in results]
    
    # 異常レベル別カウント
    decision_counts = {'normal': 0, 'warn': 0, 'degrade': 0}
    colors = []
    for d in distances_d2:
        level, decision = classify_anomaly_level(d)
        decision_counts[decision] += 1
        if level == 'strong_anomaly':
            colors.append('#e74c3c')
        elif level == 'weak_anomaly':
            colors.append('#f39c12')
        else:
            colors.append('#2ecc71')
    
    # 1. CER棒グラフ（上段全体）
    ax1 = fig.add_subplot(gs[0, :])
    bars = ax1.bar(ids, cers, color=colors, alpha=0.7, edgecolor='black', linewidth=1.2)
    ax1.axhline(y=threshold, color='purple', linestyle='--', linewidth=2, 
                label=f'CER閾値={threshold}')
    ax1.set_xlabel('画像ID', fontsize=12, fontweight='bold')
    ax1.set_ylabel('CER', fontsize=12, fontweight='bold')
    ax1.set_title('OCR精度評価結果（異常検知統合）', fontsize=14, fontweight='bold')
    ax1.set_ylim(0, 1.0)
    ax1.grid(axis='y', alpha=0.3)
    ax1.legend(fontsize=10)
    
    for bar, cer in zip(bars, cers):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{cer:.2f}', ha='center', va='bottom', fontsize=8)
    
    # 2. エンジン分布
    ax2 = fig.add_subplot(gs[1, 0])
    engines = [r['engine'] for r in results]
    engine_counts = Counter(engines)
    ax2.pie(engine_counts.values(), labels=engine_counts.keys(), autopct='%1.1f%%',
            colors=['#3498db', '#e67e22', '#95a5a6'], startangle=90)
    ax2.set_title('使用エンジン分布', fontsize=12, fontweight='bold')
    
    # 3. 合格率と異常検知率
    ax3 = fig.add_subplot(gs[1, 1])
    passed = sum(quality_ok)
    total = len(results)
    failed = total - passed
    
    quality_data = [passed, failed]
    quality_labels = [f'合格\n({passed}件)', f'不合格\n({failed}件)']
    ax3.pie(quality_data, labels=quality_labels, autopct='%1.1f%%',
            colors=['#2ecc71', '#e74c3c'], startangle=90)
    ax3.set_title(f'品質評価結果\n合格率: {passed/total*100:.1f}%', 
                  fontsize=12, fontweight='bold')
    
    # 4. 異常検知分布
    ax4 = fig.add_subplot(gs[1, 2])
    anomaly_data = [decision_counts['normal'], decision_counts['warn'], decision_counts['degrade']]
    anomaly_labels = [f'通常\n({decision_counts["normal"]}件)', 
                      f'準異常\n({decision_counts["warn"]}件)',
                      f'強異常\n({decision_counts["degrade"]}件)']
    ax4.pie(anomaly_data, labels=anomaly_labels, autopct='%1.1f%%',
            colors=['#2ecc71', '#f39c12', '#e74c3c'], startangle=90)
    ax4.set_title('異常検知分布', fontsize=12, fontweight='bold')
    
    # 5. マハラノビス距離ヒストグラム
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.hist(distances_d2, bins=10, alpha=0.7, color='skyblue', edgecolor='black')
    ax5.axvline(EMPIRICAL_THRESHOLD_D2, color='orange', linestyle='-', linewidth=2,
                label=f'経験95% (={EMPIRICAL_THRESHOLD_D2:.1f})')
    ax5.axvline(WARNING_THRESHOLD_D2, color='yellow', linestyle=':', linewidth=2,
                label=f'準異常 (={WARNING_THRESHOLD_D2:.1f})')
    ax5.set_xlabel('マハラノビス距離 D²', fontsize=10, fontweight='bold')
    ax5.set_ylabel('頻度', fontsize=10, fontweight='bold')
    ax5.set_title('距離分布と閾値', fontsize=12, fontweight='bold')
    ax5.legend(fontsize=9)
    ax5.grid(alpha=0.3)
    
    # 6. パフォーマンス傾向
    ax6 = fig.add_subplot(gs[2, 1])
    latencies = [r['latency_ms'] for r in results]
    ax6.scatter(distances_d2, latencies, c=colors, s=80, alpha=0.7, edgecolors='black')
    ax6.axvline(EMPIRICAL_THRESHOLD_D2, color='orange', linestyle='-', linewidth=2)
    ax6.axvline(WARNING_THRESHOLD_D2, color='yellow', linestyle=':', linewidth=2)
    ax6.set_xlabel('マハラノビス距離 D²', fontsize=10, fontweight='bold')
    ax6.set_ylabel('処理時間 (ms)', fontsize=10, fontweight='bold')
    ax6.set_title('異常度 vs 処理時間', fontsize=12, fontweight='bold')
    ax6.grid(alpha=0.3)
    
    # 7. 統計サマリー
    ax7 = fig.add_subplot(gs[2, 2])
    ax7.axis('off')
    
    # 統計計算
    avg_cer = np.mean(cers)
    avg_latency = np.mean(latencies)
    avg_distance = np.mean(distances_d2)
    anomaly_rate = (decision_counts['warn'] + decision_counts['degrade']) / total * 100
    
    stats_text = f'''
【総合統計】
• 総サンプル数: {total}件
• 平均CER: {avg_cer:.3f}
• 平均処理時間: {avg_latency:.1f}ms
• 平均異常度: {avg_distance:.1f}D²

【品質評価】
• 合格率: {passed/total*100:.1f}% ({passed}/{total})
• 異常検知率: {anomaly_rate:.1f}%

【閾値設定】
• 理論95%: {THEORETICAL_THRESHOLD_D2:.1f}D²
• 経験95%: {EMPIRICAL_THRESHOLD_D2:.1f}D²
• 準異常: {WARNING_THRESHOLD_D2:.1f}D²

【運用ルール】
• D² ≤ {WARNING_THRESHOLD_D2:.0f}: 通常運転
• {WARNING_THRESHOLD_D2:.0f} < D² ≤ {EMPIRICAL_THRESHOLD_D2:.0f}: 要観察
• D² > {EMPIRICAL_THRESHOLD_D2:.0f}: デグレード対応
    '''
    
    ax7.text(0.05, 0.95, stats_text, fontsize=11, ha='left', va='top',
             transform=ax7.transAxes,
             bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.3))
    
    # 全体タイトル
    fig.suptitle('OCR品質監視ダッシュボード - 異常検知統合版', 
                 fontsize=18, fontweight='bold', y=0.98)
    
    output_path = output_dir / 'ocr_integrated_dashboard.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ 統合ダッシュボード保存: {output_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='OCRテスト結果の可視化 + 異常検知分析')
    parser.add_argument('--input', type=str, default='tests/outputs/ocr_dataset_eval.json',
                        help='入力JSONファイル')
    parser.add_argument('--output', type=str, default='tests/outputs',
                        help='出力ディレクトリ')
    parser.add_argument('--threshold', type=float, default=0.30,
                        help='CER閾値')
    parser.add_argument('--cov_estimator', type=str, default='ledoit_wolf',
                        choices=['ledoit_wolf', 'empirical'],
                        help='共分散推定手法')
    parser.add_argument('--exclude_stress', action='store_true',
                        help='ストレステスト画像（012など）を除外')
    args = parser.parse_args()
    
    # パス設定
    input_path = pathlib.Path(args.input)
    output_dir = pathlib.Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_path.exists():
        print(f"❌ エラー: {input_path} が見つかりません")
        sys.exit(1)
    
    # データ読み込み
    print(f"📊 データ読み込み: {input_path}")
    all_results = load_results(input_path)
    
    # ストレステスト除外オプション
    if args.exclude_stress:
        # 012のような意図的困難画像を除外
        results = [r for r in all_results if not any(tag in r['tags'] for tag in ['012', 'stress', 'impossible'])]
        excluded_count = len(all_results) - len(results)
        print(f"   ストレステスト除外: {excluded_count}件 → 分析対象: {len(results)}件")
    else:
        results = all_results
        print(f"   {len(results)}件のテスト結果（ストレステスト含む）")
    
    if len(results) < 5:
        print("❌ エラー: サンプル数が少なすぎます（最低5件必要）")
        sys.exit(1)
    
    # 特徴量抽出とマハラノビス距離計算
    print("\n🔍 マハラノビス距離計算中...")
    features = extract_features(results)
    distances_d2, cov_version = compute_mahalanobis_distances(features, args.cov_estimator)
    
    print(f"   特徴量: {features.shape}")
    print(f"   共分散推定: {cov_version}")
    print(f"   距離範囲: {distances_d2.min():.1f} - {distances_d2.max():.1f} D²")
    
    # 異常検知サマリー
    anomaly_counts = {'normal': 0, 'warn': 0, 'strong': 0}
    for d in distances_d2:
        level, _ = classify_anomaly_level(d)
        if level == 'strong_anomaly':
            anomaly_counts['strong'] += 1
        elif level == 'weak_anomaly':
            anomaly_counts['warn'] += 1
        else:
            anomaly_counts['normal'] += 1
    
    print(f"   異常検知結果:")
    print(f"     通常: {anomaly_counts['normal']}件")
    print(f"     準異常: {anomaly_counts['warn']}件 (要観察)")
    print(f"     強異常: {anomaly_counts['strong']}件 (デグレード対応)")
    
    # グラフ生成
    print("\n📈 グラフ生成中...")
    create_cer_bar_chart(results, distances_d2, output_dir, args.threshold)
    create_mahalanobis_analysis(results, distances_d2, output_dir)
    create_tag_analysis(results, distances_d2, output_dir, args.threshold)
    create_performance_scatter(results, distances_d2, output_dir, args.threshold)
    create_summary_dashboard(results, distances_d2, output_dir, args.threshold)
    
    # 運用ログ出力
    print("\n📝 運用ログ出力中...")
    log_path = create_operational_log(results, distances_d2, output_dir, cov_version)
    
    # 最終サマリー
    print(f"\n✅ 分析完了！")
    print(f"   📁 出力ディレクトリ: {output_dir}")
    print(f"   📊 グラフ: 5種類生成")
    print(f"   📝 運用ログ: {log_path.name}")
    print(f"\n🎯 運用推奨事項:")
    print(f"   • 経験閾値 {EMPIRICAL_THRESHOLD_D2:.0f}D² を異常判定基準として採用")
    print(f"   • 準異常 {WARNING_THRESHOLD_D2:.0f}D² 超過時は要観察")
    print(f"   • 強異常は前処理強化→再試行→フォールバック")
    if args.exclude_stress:
        print(f"   • ストレステストは別枠で管理（回帰テストから分離）")


if __name__ == '__main__':
    main()
