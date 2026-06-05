import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"
MAX_MESSAGES = 40  # keep last N messages per user to avoid growing forever


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                user_id    INTEGER PRIMARY KEY,
                messages   TEXT    NOT NULL DEFAULT '[]',
                updated_at TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        """)


def load_history(user_id: int) -> list:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT messages FROM conversations WHERE user_id = ?", (user_id,)
        ).fetchone()
    return json.loads(row[0]) if row else []


def save_history(user_id: int, messages: list) -> None:
    trimmed = messages[-MAX_MESSAGES:]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO conversations (user_id, messages, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE
                SET messages = excluded.messages,
                    updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, json.dumps(trimmed, ensure_ascii=False)),
        )


def clear_history(user_id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
