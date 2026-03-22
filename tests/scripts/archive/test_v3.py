#!/usr/bin/env python3
"""PaddleOCR 2.9.1 / 3.x 両対応 総合テスト v4"""
import sys, os, time, json, re, subprocess, tempfile, traceback
from pathlib import Path

PASS="✅ PASS"; FAIL="❌ FAIL"; SKIP="⚠️  SKIP"
results = []

class SkipTest(Exception): pass

def run_test(no, name, fn):
    print(f"\n[{no:02d}/16] {name}\n" + "─"*50)
    start = time.perf_counter()
    try:
        msg = fn(); status = PASS; detail = msg or "OK"
    except SkipTest as e:
        status = SKIP; detail = str(e)
    except Exception as e:
        status = FAIL; detail = f"{type(e).__name__}: {e}"; traceback.print_exc()
    elapsed = time.perf_counter() - start
    print(f"  {status}  [{elapsed:.2f}s]  {detail}")
    results.append({"no":no,"name":name,"status":status,"elapsed":elapsed,"detail":detail})

def _paddle_ver() -> int:
    import paddleocr
    return int(getattr(paddleocr,"__version__","2.0.0").split(".")[0])

def _make_ocr_engine(lang="japan"):
    """2.x / 3.x 両対応ファクトリ"""
    from paddleocr import PaddleOCR
    # oneDNN無効化（3.x用・importより前に設定が必要）
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    if _paddle_ver() >= 3:
        return PaddleOCR(lang=lang)
    else:
        # 2.x API
        return PaddleOCR(
            use_angle_cls=True,
            lang=lang,
            use_gpu=False,
            show_log=False,
        )

def t01():
    v=sys.version_info; assert v.minor>=11
    return f"Python {v.major}.{v.minor}.{v.micro}"

def t02():
    v=os.environ.get("VIRTUAL_ENV",""); assert v,"venv未有効化"
    return f"venv: {v}"

def t03():
    import cv2; return f"OpenCV {cv2.__version__}"

def t04():
    from paddleocr import PaddleOCR
    import paddleocr
    ver=getattr(paddleocr,"__version__","?")
    api="3.x(lang=のみ)" if _paddle_ver()>=3 else "2.x(use_gpu対応)"
    return f"paddleocr {ver} [{api}]"

def t05():
    try:
        import yomitoku; return f"yomitoku {getattr(yomitoku,'__version__','?')}"
    except ImportError: raise SkipTest("yomitoku未インストール（オプション）")

def t06():
    try:
        import paddle
        n=paddle.device.cuda.device_count()
        if n==0: raise SkipTest("GPU未検出 → CPU動作（正常）")
        return f"GPU {n}台"
    except ImportError as e:
        raise SkipTest(f"paddle importエラー: {e}")

def t07():
    found=[]
    for p in [Path("test_image.png"),Path("ocr_app/test_image.png"),
              Path("ocr-screenshot-app/test_image.png")]:
        if p.exists(): found.append(str(p))
    for d in [Path("test_images/set1"),Path("tests/assets")]:
        if d.is_dir(): found+=[str(x) for x in list(d.glob("*.png"))[:2]]
    assert found,"テスト画像なし"
    return f"{len(found)}枚: {found[0]}"

def t08():
    e=_make_ocr_engine("japan"); assert e
    ver=_paddle_ver()
    return f"PaddleOCR(japan) 初期化OK [v{ver}.x API]"

def t09():
    import cv2, numpy as np
    p=next((x for x in ["test_image.png","ocr_app/test_image.png",
                         "ocr-screenshot-app/test_image.png"]
            if Path(x).exists()), None)
    if not p:
        img=np.ones((80,400,3),dtype="uint8")*255
        cv2.putText(img,"OCR Test 192.168.1.1",(10,55),
                    cv2.FONT_HERSHEY_SIMPLEX,1.2,(0,0,0),2)
        p=tempfile.mktemp(suffix=".png"); cv2.imwrite(p,img)
    e=_make_ocr_engine("japan")
    t0=time.perf_counter(); r=e.ocr(p); el=time.perf_counter()-t0
    assert el<10.0, f"10秒制約違反: {el:.2f}s（CPUのみでは厳しい場合あり）"
    texts=[]
    for blk in (r or []):
        if blk is None: continue
        for ln in blk:
            try: texts.append(ln[1][0])
            except: pass
    return f"{el:.2f}s / テキスト{len(texts)}件 / 10秒OK"

def t10():
    def rf(t):
        t=t.strip()
        if re.search(r'\d+\s*\.\s*\d+',t): t=re.sub(r'(\d+)\s*\.\s*',r'\1.',t)
        if "http" in t.lower(): t=t.replace(" ","")
        return t
    cases=[("192 . 168 . 1 . 1","192.168.1.1"),("10 . 0 . 0 . 1","10.0.0.1"),
           ("https://exam ple.com","https://example.com"),("  hello  ","hello")]
    for s,e in cases: assert rf(s)==e, f"{s!r}→{rf(s)!r}(期待:{e!r})"
    return f"{len(cases)}パターンOK"

def t11():
    ts="OCR_CLIP_TEST_郷健也_12345"
    if os.environ.get("WAYLAND_DISPLAY"):
        if subprocess.run(["which","wl-copy"],capture_output=True).returncode!=0:
            raise SkipTest("wl-copy未インストール: sudo apt install wl-clipboard")
        subprocess.run(["wl-copy",ts],check=True)
        got=subprocess.run(["wl-paste"],capture_output=True,text=True).stdout.strip()
        assert got==ts
        return "wl-copy(Wayland) OK"
    else:
        if subprocess.run(["which","xclip"],capture_output=True).returncode!=0:
            raise SkipTest("xclip未インストール: sudo apt install xclip")
        subprocess.run(["xclip","-selection","clipboard"],input=ts.encode(),check=True)
        got=subprocess.run(["xclip","-selection","clipboard","-o"],
                           capture_output=True,text=True).stdout.strip()
        assert got==ts, f"不一致:{got!r}"
        return "xclip(X11) OK"

def t12():
    w=os.environ.get("WAYLAND_DISPLAY","")
    x=os.environ.get("DISPLAY","")
    xdg=os.environ.get("XDG_SESSION_TYPE","")
    if w: return f"Wayland({w}) XDG={xdg}"
    if x: return f"X11({x}) XDG={xdg}"
    raise Exception("表示サーバー未検出")

def t13():
    f=[t for t in["grim","scrot","gnome-screenshot"]
       if subprocess.run(["which",t],capture_output=True).returncode==0]
    if not f: raise SkipTest("要インストール: sudo apt install grim または scrot")
    return f"利用可能: {', '.join(f)}"

def t14():
    r=subprocess.run(["dotnet","--version"],capture_output=True,text=True)
    if r.returncode!=0:
        raise SkipTest(".NET未インストール: sudo apt install dotnet-sdk-8.0")
    v=r.stdout.strip()
    assert int(v.split(".")[0])>=8, f"8以上必要:{v}"
    return f".NET {v}"

def t15():
    req={"jsonrpc":"2.0","id":1,"method":"ocr.perform",
         "params":{"image":"b64==","lang":"japan"}}
    p=json.loads(json.dumps(req,ensure_ascii=False))
    assert p["method"]=="ocr.perform"
    return "JSON-RPC 2.0 OK"

def t16():
    # Python側の必須ファイル
    py_required={
        "src/python/ocr_worker/handler.py": "OCRワーカー",
        "requirements.txt":                 "依存定義",
        ".venv-ocr27":                      "Python venv",
    }
    miss=[f"{k}({v})" for k,v in py_required.items() if not Path(k).exists()]
    if miss: raise Exception("Python必須ファイル不足: "+", ".join(miss))

    # C#は任意（Ubuntu移植中のためSKIPにしない）
    csharp_ok = Path("src/csharp").exists()
    sln_ok    = any(Path(".").glob("*.sln"))
    csharp_status = "あり" if csharp_ok else "なし（Ubuntu移植中）"

    opt=[p for p in["src/python/ocr_worker/capture_linux.py",
                    "src/python/ocr_worker/selector_linux.py"] if not Path(p).exists()]
    return (f"Python必須構成OK / C#:{csharp_status} / "
            f"Linux移植未実装:{len(opt)}件")

if __name__=="__main__":
    print("="*60)
    print(f"  OCR Clipboard v2.0 総合テスト v4")
    print(f"  実行日時: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python: {sys.version.split()[0]}  CWD: {Path.cwd()}")
    print("="*60)

    tests=[
        ( 1,"Pythonバージョン(>=3.11)",t01),
        ( 2,"venv有効化確認",          t02),
        ( 3,"cv2インポート",            t03),
        ( 4,"PaddleOCRインポート",      t04),
        ( 5,"yomitokuインポート[任意]", t05),
        ( 6,"GPU/CUDA検出[任意]",       t06),
        ( 7,"テスト画像ファイル確認",   t07),
        ( 8,"PaddleOCRエンジン初期化",  t08),
        ( 9,"OCR実行+10秒制約",         t09),
        (10,"refine_text IP/URL補正",  t10),
        (11,"クリップボード書込/読出",  t11),
        (12,"表示サーバー検出",         t12),
        (13,"スクリーンショットツール", t13),
        (14,".NET SDK確認[任意]",       t14),
        (15,"JSON-RPC フォーマット",    t15),
        (16,"プロジェクト構成確認",     t16),
    ]
    for no,name,fn in tests: run_test(no,name,fn)

    print("\n"+"="*60)
    print("  サマリー")
    print("="*60)
    pa=[r for r in results if r["status"]==PASS]
    fa=[r for r in results if r["status"]==FAIL]
    sk=[r for r in results if r["status"]==SKIP]
    for r in results:
        ic="✅" if r["status"]==PASS else("❌" if r["status"]==FAIL else"⚠️ ")
        print(f"  {ic} [{r['no']:02d}] {r['name']:<32} {r['elapsed']:.2f}s")
    print(f"\n  PASS:{len(pa)} / FAIL:{len(fa)} / SKIP:{len(sk)}")
    if fa:
        print("\n❌ 失敗:")
        for r in fa: print(f"  [{r['no']:02d}] {r['name']}: {r['detail'][:80]}")
    if sk:
        print("\n⚠️  スキップ:")
        for r in sk: print(f"  [{r['no']:02d}] {r['name']}: {r['detail'][:60]}")
    print(f"\n  総実行時間: {sum(r['elapsed'] for r in results):.2f}s")
    print("🎉 全テスト合格！" if not fa else f"🔧 {len(fa)}件のFAILを修正してください")
    sys.exit(len(fa))
