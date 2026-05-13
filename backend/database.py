"""
SQLite database layer for PainSignal.
Stores users, subscribers, and payment records.
"""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "painsignal.db"


@contextmanager
def get_db():
    """Context manager for DB connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist."""
    with get_db() as conn:
        # Users (paying members)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                plan TEXT DEFAULT 'free',
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT
            )
        """)

        # Newsletter subscribers (email capture from landing page)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                source TEXT DEFAULT 'landing_page',
                subscribed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                unsubscribed_at TEXT
            )
        """)

        # Payment events (audit log)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payment_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT NOT NULL,
                stripe_event_id TEXT,
                amount INTEGER,
                currency TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)


# ─── User Operations ──────────────────────────────────────────────
def create_user(email: str, password_hash: str, plan: str = "free"):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, plan) VALUES (?, ?, ?)",
            (email, password_hash, plan)
        )
        return cur.lastrowid


def get_user_by_email(email: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def update_user_plan(user_id: int, plan: str, stripe_customer_id: str = None, stripe_subscription_id: str = None):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET plan = ?, stripe_customer_id = ?, stripe_subscription_id = ? WHERE id = ?",
            (plan, stripe_customer_id, stripe_subscription_id, user_id)
        )


def update_user_login(user_id: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), user_id)
        )


# ─── Subscriber Operations ────────────────────────────────────────
def add_subscriber(email: str, source: str = "landing_page"):
    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO subscribers (email, source) VALUES (?, ?)",
                (email, source)
            )
            return True
        except sqlite3.IntegrityError:
            # Already subscribed
            return False


def get_all_subscribers():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM subscribers WHERE unsubscribed_at IS NULL ORDER BY subscribed_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_subscriber_count():
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as count FROM subscribers WHERE unsubscribed_at IS NULL"
        ).fetchone()
        return row["count"]


# ─── Payment Events ───────────────────────────────────────────────
def log_payment_event(user_id: int, event_type: str, stripe_event_id: str = None,
                      amount: int = None, currency: str = None, metadata: str = None):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO payment_events (user_id, event_type, stripe_event_id, amount, currency, metadata)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, event_type, stripe_event_id, amount, currency, metadata)
        )


# Initialize on import
init_db()
