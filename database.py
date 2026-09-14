import sqlite3
from datetime import datetime

DB_PATH = "signals.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            trade_type TEXT,
            side TEXT,
            entry REAL,
            stop REAL,
            take REAL,
            rr REAL,
            strength TEXT,
            reason TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'active'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS strength_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            old_strength TEXT,
            new_strength TEXT,
            changed_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_signal(data: dict) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO signals (symbol, trade_type, side, entry, stop, take, rr, strength, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["symbol"], data["trade_type"], data["side"],
        data["entry"], data["stop"], data["take"], data["rr"],
        data["strength"], data["reason"], datetime.utcnow().isoformat()
    ))
    signal_id = c.lastrowid
    conn.commit()
    conn.close()
    return signal_id

def get_active_signals(limit=20):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM signals WHERE status='active' ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows
