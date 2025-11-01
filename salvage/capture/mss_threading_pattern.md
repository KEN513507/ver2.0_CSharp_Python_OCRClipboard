# mss スレッドセーフ・キャプチャパターン

## 問題
`mss` は `_thread._local` でハンドルを管理するため、グローバル保持や別スレッド使い回しで落ちる。

## 解法（定石）
**毎回 `with mss.mss()` で生成→同一スレッドで `grab()`→閉じる**

```python
import mss
import mss.tools
from PIL import Image

def grab_image(x, y, width, height):
    """スレッドセーフなキャプチャ（mss使い捨て + PILフォールバック）"""
    try:
        with mss.mss() as sct:
            monitor = {"left": x, "top": y, "width": width, "height": height}
            sct_img = sct.grab(monitor)
            # mss → PIL 変換
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    except Exception as e:
        print(f"[WARNING] mss failed: {e}, fallback to PIL.ImageGrab", file=sys.stderr)
        from PIL import ImageGrab
        return ImageGrab.grab(bbox=(x, y, x + width, y + height))
```

## DPI awareness（Windows）
```python
import ctypes

def enable_dpi_awareness():
    try:
        # Windows 10 1607+ (Per-Monitor V2)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Fallback: Windows Vista~
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
```

## 適用場面
- **スレッドセーフが必要なキャプチャ**（WPF UI、バックグラウンドワーカー等）
- **PIL との相互フォールバック**（クラウド環境でmssが使えない場合）
- **座標ズレ抑制**（DPI 100%以外でもある程度正確）

## 移植先候補
- C# WPF → `System.Windows.Forms.Screen.PrimaryScreen.Bounds` + `Graphics.CopyFromScreen`
- C# WinUI3 → `Windows.Graphics.Capture` API（UWP式）
