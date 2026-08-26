import json, os
from datetime import datetime, timezone

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_LOG_PATH = os.path.join(_REPO_ROOT, 'audit_log.jsonl')


def log_event(payment_id: str, phase: str, detail: dict) -> None:
    """Append one structured audit entry to audit_log.jsonl.

    Args:
        payment_id: Payment being processed (e.g. PMT-00001).
        phase:      Pipeline phase name (DETECTION, DIAGNOSIS,
                    SCORING, ACTION_SELECTION, EXECUTION).
        detail:     Phase-specific key/value dict.

    Entry written: {timestamp, payment_id, phase, detail}
    """
    entry = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "payment_id": payment_id,
        "phase": phase,
        "detail": detail,
    }
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
