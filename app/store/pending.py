"""
app/store/pending.py — clarify questions that are waiting for the user's answer.

WHAT: When Pehchaan decides "clarify" (e.g. book B has two doctors and no default), we store a pending item:
      the transcript, the contact book, the phrase we asked about ("my doctor") and the candidates with
      name + role + reason. POST /api/clarify/{id} answers it later. Functions: create(), get(), claim(), link_reminder().
WHY:  Asking is only useful if the answer can be acted on. Storing the question (instead of keeping it in
      memory) means it survives a server restart and can't be answered twice.
"""

import json
import secrets
from datetime import datetime

from app.store.db import connect


def create(conn, visitor_id: str, book: str, transcript: str, direction: str, caller_contact_id: str | None, phrase: str, reason: str,
           candidates: list[dict]) -> dict:
    """Store an open question and return it (with its new random id)."""
    item = {"id": secrets.token_hex(8),  # 16 hex characters: unguessable and URL-safe
            "created_at": datetime.now().isoformat(timespec="seconds"), "contact_book": book,
            "heard_transcript": transcript, "direction": direction, "caller_contact_id": caller_contact_id,
            "phrase": phrase, "reason": reason, "candidates": candidates, "status": "open", "reminder_id": None}
    conn.execute("INSERT INTO pending (id, created_at, contact_book, heard_transcript, direction, caller_contact_id,"
                 " phrase, reason, candidates_json, visitor_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (item["id"], item["created_at"], book, transcript, direction, caller_contact_id, phrase, reason,
                  json.dumps(candidates, ensure_ascii=False), visitor_id))
    return item


def get(pending_id: str, visitor_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM pending WHERE id = ? AND visitor_id = ?", (pending_id, visitor_id)).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["candidates"] = json.loads(item.pop("candidates_json"))
    return item


def claim(conn, pending_id: str, visitor_id: str) -> bool:
    """Claim the answer in the same transaction as any resulting reminder."""
    cur = conn.execute("UPDATE pending SET status = 'answered' WHERE id = ? AND visitor_id = ? AND status = 'open'",
                       (pending_id, visitor_id))
    return cur.rowcount == 1


def link_reminder(conn, pending_id: str, visitor_id: str, reminder_id: int) -> None:
    conn.execute("UPDATE pending SET reminder_id = ? WHERE id = ? AND visitor_id = ?",
                 (reminder_id, pending_id, visitor_id))
