# OCR Clipboard v2.0 (Archived)

**現在のブランチ**: `archive/paddle-to-wm-ocr` (アーカイブ専用)  
**GitHub リポジトリ**: [KEN513507/ver2.0_CSharp_Python_OCRClipboard](https://github.com/KEN513507/ver2.0_CSharp_Python_OCRClipboard)  
**タグ**: `v2-archive` — PaddleOCR 版の終了記録

このリポジトリは Windows.Media.Ocr ベースの新構成へ移行するためアーカイブ済みです。Python + PaddleOCR で得た知見は `salvage/` と C# のテンプレートコードに集約しました。

---

## プロジェクト概要

### 開発企画
**目的**: 画面範囲選択 → OCR → クリップボード自動コピー（デスクトップアイコン起動）  
**要件**: 2回目以降のOCRを **2-3秒以内** で完了（初回は遅くても許容）

### 終了理由
**PaddleOCR 版の性能不足**:
- 目標: 2-3秒 / 実測: 初回90秒、2回目以降80秒（**40倍遅い**）
- CPU制約: i7-8550U（モバイルU系）では大型モデルの高速化不可能
- 結論: Windows.Media.Ocr（<1秒）への全面移行

### ハードウェア要件
| 項目 | 要件 | 備考 |
|------|------|------|
| **OS** | Windows 10 1809+ | Windows.Media.Ocr API 必須 |
| **CPU** | 任意（U系でもOK） | Windows OCR は軽量、GPU不要 |
| **RAM** | 4GB以上推奨 | .NET 8 + WPF 動作環境 |
| **ディスプレイ** | プライマリ1枚 | マルチディスプレイ未対応 |
| **DPI** | 100% 推奨 | スケーリング対応は今後 |

### バイナリ配布（予定）
- **実行ファイル**: `OCRClipboard.exe`（単一実行ファイル、self-contained）
- **サイズ**: ~15MB（.NET 8 Runtime 内包）
- **依存**: なし（Python・PaddleOCR 完全削除済み）
- **起動**: デスクトップアイコン → 常駐トレイ → ホットキーで範囲選択

---

## 要件定義（確定版）

### 機能要件
| ID | 要件 | 優先度 | 状態 |
|----|------|--------|------|
| F-1 | デスクトップアイコン起動で常駐トレイ化 | 必須 | 未実装 |
| F-2 | ホットキー（例: Ctrl+Shift+O）で矩形選択開始 | 必須 | 部分実装（WPF Overlay） |
| F-3 | 範囲確定後、即座に OCR 実行（<1秒） | 必須 | 未実装（C# エンジン未統合） |
| F-4 | OCR 結果を自動的にクリップボードへコピー | 必須 | 未実装 |
| F-5 | トレイアイコンから手動終了 | 推奨 | 未実装 |
| F-6 | OCR 精度の品質判定（Levenshtein 25%/20文字） | 任意 | テンプレート実装済み |

### 非機能要件
| ID | 要件 | 測定方法 | 状態 |
|----|------|----------|------|
| NF-1 | 2回目以降の OCR を 2-3秒以内で完了 | `[PERF]` ログ | Windows.Media.Ocr で達成見込み |
| NF-2 | Display 1（プライマリ）で正確な座標取得 | DPI awareness 有効化 | WPF 側実装済み |
| NF-3 | バイナリサイズ 20MB 以下 | 実行ファイル計測 | 未計測 |
| NF-4 | メモリ使用量 100MB 以下（常駐時） | タスクマネージャー | 未計測 |

### 非要件（対応しない範囲）
- ❌ マルチディスプレイ（Display 2以降）の正確な座標補正
- ❌ DPI 125%/150% での完全動作保証（100%のみ対応）
- ❌ GPU 高速化（Windows.Media.Ocr は CPU のみで十分高速）
- ❌ オフライン大型モデル（PaddleOCR 等）のランタイム統合

---

## 現在の方針
- **本番実行は C# 単独**（Windows.Media.Ocr、矩形選択→OCR→クリップボードで < 1 秒）
- **Python/PaddleOCR は廃止**。重いモデルを常駐させても CPU（i7-8550U）では 90 秒以上かかるため要件不適合と判断
- **再利用する資産** は以下に整理済み
  - `salvage/` … テスト、品質ヒューリスティック、パフォーマンスログ、キャプチャ耐障害パターンのまとめ
  - `src/Infra/*.cs`, `src/Quality/*.cs`, `src/Ocr/*.cs`, `src/Worker/*.cs` … C# 用テンプレート
  - `tests/*` … xUnit ベースのテスト雛形（slow 分離、環境変数上書き等）

---

## 新しい C# プロジェクトの雛形
```
src/
 ├─ Infra/PerfLogger.cs              # [PERF]/[OCR] ログ整形
 ├─ Quality/QualityConfig.cs         # OCR 品質閾値（環境変数で可変）
 ├─ Quality/OcrQualityEvaluator.cs   # 25% / 20文字以内のヒューリスティック
 ├─ Ocr/IOcrEngine.cs                # OCR エンジンのインターフェース
 ├─ Ocr/OcrResult.cs, OcrFragment.cs # OCR 結果のラッパー
 ├─ Ocr/FakeOcrEngine.cs             # テスト用フェイク
 └─ Worker/Worker.cs                 # stdin→stdout の簡易ワーカー例

tests/
 ├─ Common/SlowOcrAttribute.cs       # Category("SlowOCR")
 ├─ Common/ConfigOverrideFixture.cs  # 環境変数上書き
 ├─ Quality/QualityEvaluatorTests.cs # 品質判定のユニットテスト
 ├─ Ocr/WorkerTests.cs               # stdin JSON 耐性テスト
 └─ Slow/WindowsMediaOcrIntegrationTests.cs (TODO)
```

## Salvage ディレクトリ
Python 版から抜き出した再利用素材。詳細は `salvage/SALVAGE_INDEX.md` を参照。

| 分類 | ファイル | 説明 |
|------|----------|------|
| テスト | `salvage/tests/conftest.py` | autouse モック (tkinter/mss/PaddleOCR) の原典 |
| 品質 | `salvage/python/quality_config.py` | 品質閾値クラスの Python 版 |
| ログ | `salvage/notes/perf_logging.md` | [PERF]/[OCR] ログ書式メモ |
| キャプチャ | `salvage/capture/mss_threading_pattern.md` | 1回ごと with + フォールバック |
| slow 分離 | `salvage/tests/slow_test_pattern.md` | pytest → xUnit カテゴリ移行メモ |

## 既知の教訓（PaddleOCR 版の失敗から）
- **モバイル U 系 CPU + PaddleOCR**: 初回 90 秒、2 回目 80 秒で実用にならない
- **モデル API の不安定性**: mobile/server 切り替え方法が頻繁に変わり、事前固定が必須だった
- **常駐化の限界**: モデルサイズが支配的で、ウォームアップしても速度改善は限定的
- **正しい選択**: 今回の要件は Windows.Media.Ocr（<1秒、GPU不要）で十分満たせる

---

## GitHub 設定・ブランチ戦略

### リポジトリ情報
- **リポジトリ**: `KEN513507/ver2.0_CSharp_Python_OCRClipboard`
- **デフォルトブランチ**: `main`（新実装用）
- **現在のブランチ**: `archive/paddle-to-wm-ocr`（アーカイブ専用、マージ不可）
- **タグ**: `v2-archive`（PaddleOCR 版の終了記録）

### ブランチ運用
| ブランチ | 用途 | 状態 |
|----------|------|------|
| `main` | Windows.Media.Ocr 版の開発 | 今後実装 |
| `archive/paddle-to-wm-ocr` | PaddleOCR 版の保存 | 読み取り専用 |
| `feature/*` | 新機能開発 | 今後作成 |
| `hotfix/*` | 緊急修正 | 今後作成 |

### CI/CD（予定）
- **GitHub Actions**: `dotnet build` + `dotnet test`（fast テストのみ）
- **Slow テスト**: 手動実行（`Category!=SlowOCR` フィルタ）
- **リリース**: GitHub Releases で単一実行ファイル配布

---

## 次にやること
1. **C# ソリューションをクリーンに作り直し**、上記テンプレートを取り込む
2. **Windows.Media.Ocr を統合**（`src/csharp/OCRClipboard.App/Ocr/WindowsOcrEngine.cs`）
3. **実機テストを整備**（`tests/Slow/WindowsMediaOcrIntegrationTests.cs`、Display 1 固定）
4. **常駐トレイ化**（ホットキー登録、バックグラウンド起動）
5. **品質ログ可視化**（`PerfLogger` 出力を集計、閾値チューニング）

---

過去の Python コードが必要になった場合は `salvage/` と Git 履歴から参照できます。
