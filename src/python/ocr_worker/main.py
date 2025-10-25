from __future__ import annotations

import json
import sys
from typing import Any, Dict

from .dto import Envelope
from . import handler


def _respond(env_id: str, typ: str, payload: Dict[str, Any]) -> None:
    out = {"id": env_id, "type": typ, "payload": payload}
    sys.stdout.write(json.dumps(out, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _respond_error(env_id: str, code: str, message: str) -> None:
    _respond(env_id, "error", {"code": code, "message": message})


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            env = json.loads(line)
            env_id = env.get("id", "")
            typ = env.get("type", "")
            payload = env.get("payload", {})

            if typ == "health.check":
                res = handler.handle_health_check(payload)
                _respond(env_id, "health.ok", res)
            elif typ == "ocr.perform":
                res = handler.handle_ocr_perform(payload)
                _respond(env_id, "ocr.result", res)
            else:
                _respond_error(env_id, "unknown_type", f"Unknown type: {typ}")
        except Exception as e:  # noqa: BLE001
            # Try to extract id if possible
            try:
                env_id = json.loads(line).get("id", "")
            except Exception:  # noqa: BLE001
                env_id = ""
            _respond_error(env_id, "exception", str(e))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

