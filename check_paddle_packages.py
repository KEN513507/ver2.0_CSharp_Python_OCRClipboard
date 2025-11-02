#!/usr/bin/env python3
import importlib.util
import sys

modules = ['paddlex', 'paddleocr', 'paddlenlp', 'paddlehub']

for m in modules:
    try:
        spec = importlib.util.find_spec(m)
        if spec:
            mod = importlib.import_module(m)
            ver = getattr(mod, '__version__', '?')
            print(f"[HAVE] {m} {ver}")
        else:
            print(f"[MISS] {m}")
    except Exception as e:
        print(f"[MISS] {m} ({e.__class__.__name__})")
