#!/usr/bin/env python3
import sys
import os
import subprocess

# tools/check_prerequisites.py を呼び出すためのラッパー
def main():
    script_path = os.path.join(os.path.dirname(__file__), "tools", "check_prerequisites.py")
    if not os.path.exists(script_path):
        print(f"Error: {script_path} not found.")
        sys.exit(1)

    # 同じ Python インタプリタで実行
    os.execv(sys.executable, [sys.executable, script_path] + sys.argv[1:])

if __name__ == "__main__":
    main()
