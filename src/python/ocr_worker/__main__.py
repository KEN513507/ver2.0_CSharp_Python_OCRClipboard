#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JSON-RPC server for OCR operations"""
import sys
import json
import logging
import os
import time
import numpy as np
from typing import Any, Dict

from .handler import handle_health_check, handle_ocr_perform, handle_ping

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # ← stderr に出力してノイズ分離
)
logger = logging.getLogger(__name__)


def warmup_paddle_ocr():
    """初期ウォームアップ：PaddleOCR を1枚ダミー画像で実行してモデルをロード"""
    try:
        from paddleocr import PaddleOCR
        
        lang_code = os.environ.get("OCR_PADDLE_LANG", "japan")
        use_cls = os.environ.get("OCR_PADDLE_USE_CLS", "0") in ("1", "true", "yes")
        
        logger.info(f"Warmup: Initializing PaddleOCR (lang={lang_code}, use_textline_orientation={use_cls})")
        t0 = time.perf_counter()
        
        ocr = PaddleOCR(lang=lang_code, use_textline_orientation=use_cls)
        
        # ダミー画像作成（100x100 白背景に黒文字 "Test"）
        dummy_img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        
        # ダミー実行
        _ = ocr.ocr(dummy_img)
        
        t1 = time.perf_counter()
        logger.info(f"Warmup: PaddleOCR ready in {t1-t0:.2f}s")
        
        return True
    except Exception as e:
        logger.error(f"Warmup failed: {e}")
        return False


def main():
    """JSON-RPC main loop: read requests from stdin, write responses to stdout"""
    # 起動識別子を stdout に出力（これで __main__.py が実行されたことが分かる）
    print(json.dumps({"_boot": "ocr_worker.__main__", "version": "2.0"}), flush=True)
    logger.info("OCR Worker started via __main__.py")
    
    # 初期ウォームアップ
    warmup_success = warmup_paddle_ocr()
    print(json.dumps({"_warmup": "complete", "success": warmup_success}), flush=True)
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            envelope = json.loads(line)
            req_id = envelope.get("id", "")
            req_type = envelope.get("type", "")
            payload = envelope.get("payload", {})

            if req_type == "ping":
                logger.debug("Heartbeat ping received (id=%s)", req_id)
            else:
                logger.info("Request: id=%s, type=%s", req_id, req_type)
            
            # Dispatch to handler
            if req_type in ("health_check", "health.check"):
                result = handle_health_check(payload)
            elif req_type == "ping":
                result = handle_ping(payload)
            elif req_type in ("ocr_perform", "ocr.perform"):
                result = handle_ocr_perform(payload)
            else:
                result = {"text": "", "confidence": 0.0, "error": f"Unknown type: {req_type}"}
            
            # Send response
            response_type = "pong" if req_type == "ping" else req_type
            response = {
                "id": req_id,
                "type": response_type,
                "payload": result
            }
            print(json.dumps(response), flush=True)
            if req_type == "ping":
                logger.debug("Heartbeat pong sent (id=%s)", req_id)
            else:
                logger.info("Response sent for id=%s", req_id)
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Handler error: {e}", exc_info=True)
            # Send error response if we have req_id
            try:
                error_response = {
                    "id": req_id if 'req_id' in locals() else "",
                    "type": req_type if 'req_type' in locals() else "error",
                    "payload": {"text": "", "confidence": 0.0, "error": str(e)}
                }
                print(json.dumps(error_response), flush=True)
            except:
                pass


if __name__ == "__main__":
    main()
