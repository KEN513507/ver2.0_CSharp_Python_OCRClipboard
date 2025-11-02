#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JSON-RPC server for OCR operations"""
import sys
import json
import logging

from .handler import (
    ensure_warmup_from_env,
    handle_health_check,
    handle_ocr_perform,
    handle_ping,
    handle_warmup,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # ← stderr に出力してノイズ分離
)
logger = logging.getLogger(__name__)
def main():
    """JSON-RPC main loop: read requests from stdin, write responses to stdout"""
    # 起動識別子を stdout に出力（これで __main__.py が実行されたことが分かる）
    print(json.dumps({"_boot": "ocr_worker.__main__", "version": "2.0"}), flush=True)
    logger.info("OCR Worker started via __main__.py")
    
    # 初期ウォームアップ
    try:
        warmed = ensure_warmup_from_env(force=True)
        warmed_langs = sorted({lang for lang, _ in warmed})
        print(json.dumps({"_warmup": "complete", "langs": warmed_langs}), flush=True)
        logger.info(
            "Warmup completed for langs=%s",
            ", ".join(warmed_langs) if warmed_langs else "none",
        )
    except Exception as exc:
        logger.error("Initial warmup failed: %s", exc, exc_info=True)
        print(json.dumps({"_warmup": "failed", "error": str(exc)}), flush=True)
        raise
    
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
            elif req_type in ("warmup", "ocr.warmup"):
                result = handle_warmup(payload)
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
