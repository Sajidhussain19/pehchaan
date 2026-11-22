"""
app/store/reminders.py — create, list, get and delete stored reminders (the one real action).

WHAT: A `Reminder` model (Pydantic, so every stored reminder has the same checked shape) and four
      functions: create(), list_all(), get(), delete_all(). Each runs plain SQL on data/app.db.
WHY:  CLAUDE.md: "One real action only: Remind. It creates a real stored reminder (person, time, place,
      heard vs resolved), listed and openable in the UI." The reminder keeps BOTH what was heard and what
      it was resolved to, with the reason, so the user can always see why Pehchaan chose that person.
      It also records HOW the target was decided (`resolution`), which is what the learning demo shows.
"""

import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.store.db import connect

Resolution = Literal["auto", "clarified_this_time", "clarified_always", "preference"]


class Reminder(BaseModel):
    id: int | None = None  # set by the database
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    contact_book: str
    heard_transcript: str
    output_transcript: str
    target_entity_id: str | None = None
    target_name: str | None = None
    target_role: str | None = None
    place_entity_id: str | None = None
    place_name: str | None = None
    time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    raw_time_text: str | None = None
    entities: list[dict] = []  # heard -> resolved -> confidence -> reason (stored as entities_json)
    resolution: Resolution  # auto | clarified_this_time | clarified_always | preference
    status: Literal["created"] = "created"


COLUMNS = ("created_at", "contact_book", "heard_transcript", "output_transcript", "target_entity_id", "target_name",
           "target_role", "place_entity_id", "place_name", "time", "raw_time_text", "entities_json", "resolution",
           "status", "visitor_id")


def _from_row(row) -> Reminder:
    data = dict(row)
    data["entities"] = json.loads(data.pop("entities_json"))
    return Reminder(**data)


def create(conn, reminder: Reminder, visitor_id: str) -> Reminder:
    """Store a reminder and return it with its new id."""
    values = reminder.model_dump()
    values["entities_json"] = json.dumps(values.pop("entities"), ensure_ascii=False)
    values["visitor_id"] = visitor_id
    cur = conn.execute(f"INSERT INTO reminders ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})",
                       [values[c] for c in COLUMNS])
    return reminder.model_copy(update={"id": cur.lastrowid})


def list_all(visitor_id: str) -> list[Reminder]:
    """This visitor’s reminders, newest first."""
    with connect() as conn:
        rows = conn.execute("SELECT * FROM reminders WHERE visitor_id = ? ORDER BY id DESC", (visitor_id,))
        return [_from_row(row) for row in rows]


def get(reminder_id: int, visitor_id: str) -> Reminder | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM reminders WHERE id = ? AND visitor_id = ?", (reminder_id, visitor_id)).fetchone()
        return _from_row(row) if row else None


def delete_all(visitor_id: str) -> int:
    """Remove this visitor’s reminders (to reset between demos). Returns how many were deleted."""
    with connect() as conn:
        return conn.execute("DELETE FROM reminders WHERE visitor_id = ?", (visitor_id,)).rowcount
