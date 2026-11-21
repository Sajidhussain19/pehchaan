"""
app/store/pending.py — clarify questions that are waiting for the user's answer.

WHAT: When Pehchaan decides "clarify" (e.g. book B has two doctors and no default), we store a pending item:
      the transcript, the contact book, the phrase we asked about ("my doctor") and the candidates with
      name + role + reason. POST /api/clarify/{id} answers it later. Functions: create(), get(), mark_answered().
WHY:  Asking is only useful if the answer can be acted on. Storing the question (instead of keeping it in
      memory) means it survives a server restart and can't be answered twice.
"""

import json
import secrets
from datetime import datetime

from app.store.db import connect


def create(book: str, transcript: str, direction: str, caller_contact_id: str | None, phrase: str, reason: str,
           candidates: list[dict]) -> dict:
    """Store an open question and return it (with its new random id)."""
    item = {"id": secrets.token_hex(8),  # 16 hex characters: unguessable and URL-safe
            "created_at": datetime.now().isoformat(timespec="seconds"), "contact_book": book,
            "heard_transcript": transcript, "direction": direction, "caller_contact_id": caller_contact_id,
            "phrase": phrase, "reason": reason, "candidates": candidates, "status": "open", "reminder_id": None}
    with connect() as conn:
        conn.execute("INSERT INTO pending (id, created_at, contact_book, heard_transcript, direction, caller_contact_id,"
                     " phrase, reason, candidates_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (item["id"], item["created_at"], book, transcript, direction, caller_contact_id, phrase, reason,
                      json.dumps(candidates, ensure_ascii=False)))
    return item


def get(pending_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM pending WHERE id = ?", (pending_id,)).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["candidates"] = json.loads(item.pop("candidates_json"))
    return item


def mark_answered(pending_id: str, reminder_id: int | None) -> bool:
    """Close the question. Returns False if it was already answered (so it can't be answered twice)."""
    with connect() as conn:
        cur = conn.execute("UPDATE pending SET status = 'answered', reminder_id = ? WHERE id = ? AND status = 'open'",
                           (reminder_id, pending_id))
        return cur.rowcount == 1
