"""Send multiple JSON requests to a resident OCR worker.

Usage:
    python tools/send_to_resident.py [--profile mobile|server] [--count N]
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Test resident OCR worker")
    parser.add_argument("--profile", default="mobile", choices=["mobile", "server"])
    parser.add_argument("--count", type=int, default=5, help="Number of requests")
    parser.add_argument("--image", default="./test_image.png", help="Image path")
    args = parser.parse_args()

    # Setup environment
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = f".{os.pathsep}src{os.sep}python{os.pathsep}ocr-screenshot-app"
    env["OCR_PROFILE"] = args.profile

    print(f"[CLIENT] Starting resident worker (profile={args.profile})", file=sys.stderr)
    
    # Start resident worker
    proc = subprocess.Popen(
        [sys.executable, "-m", "ocr_worker.main", "--mode", "resident"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
        cwd=root,
    )

    def send_request(image_path: str) -> dict:
        """Send JSON request and read response."""
        req = json.dumps({"image_path": image_path}) + "\n"
        proc.stdin.write(req)
        proc.stdin.flush()
        response_line = proc.stdout.readline().strip()
        return json.loads(response_line) if response_line else {}

    # Wait for ready signal
    print("[CLIENT] Waiting for ready signal...", file=sys.stderr)
    ready_msg = proc.stdout.readline().strip()
    if ready_msg:
        ready_data = json.loads(ready_msg)
        print(f"[CLIENT] Worker ready: warmup={ready_data.get('warmup_time', 0):.2f}s", file=sys.stderr)

    # Send multiple requests
    print(f"[CLIENT] Sending {args.count} requests...", file=sys.stderr)
    times = []
    for i in range(args.count):
        start = time.perf_counter()
        result = send_request(args.image)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        
        success = result.get("success", False)
        proc_time = result.get("processing_time", 0)
        text_len = len(result.get("text", ""))
        
        print(f"[CLIENT] Request {i+1}/{args.count}: success={success} "
              f"proc_time={proc_time:.3f}s wall_time={elapsed:.3f}s text_len={text_len}", 
              file=sys.stderr)

    # Statistics
    if times:
        print(f"\n[CLIENT] Statistics (profile={args.profile}):", file=sys.stderr)
        print(f"  Total requests: {len(times)}", file=sys.stderr)
        print(f"  Min: {min(times):.3f}s", file=sys.stderr)
        print(f"  Max: {max(times):.3f}s", file=sys.stderr)
        print(f"  Mean: {sum(times)/len(times):.3f}s", file=sys.stderr)
        if len(times) > 1:
            print(f"  2nd+ requests mean: {sum(times[1:])/len(times[1:]):.3f}s", file=sys.stderr)

    # Cleanup
    proc.terminate()
    proc.wait(timeout=5)
    print("[CLIENT] Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
