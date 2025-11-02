#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JSON-RPC server for OCR operations"""
import sys
import json
import logging
from typing import Any, Dict

from .handler import handle_health_check, handle_ocr_perform

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # ← stderr に出力してノイズ分離
)
logger = logging.getLogger(__name__)


def main():
    """JSON-RPC main loop: read requests from stdin, write responses to stdout"""
    logger.info("OCR Worker started")
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            envelope = json.loads(line)
            req_id = envelope.get("id", "")
            req_type = envelope.get("type", "")
            payload = envelope.get("payload", {})
            
            logger.info(f"Request: id={req_id}, type={req_type}")
            
            # Dispatch to handler
            if req_type == "health_check":
                result = handle_health_check(payload)
            elif req_type == "ocr_perform":
                result = handle_ocr_perform(payload)
            else:
                result = {"text": "", "confidence": 0.0, "error": f"Unknown type: {req_type}"}
            
            # Send response
            response = {
                "id": req_id,
                "type": req_type,
                "payload": result
            }
            print(json.dumps(response), flush=True)
            logger.info(f"Response sent for id={req_id}")
        
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
