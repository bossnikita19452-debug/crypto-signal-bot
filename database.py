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
            status TEXT DEFAULT 'active',
            result_price REAL,
            closed_at TEXT
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
    """Все открытые сделки (status='active')."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM signals WHERE status='active' ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_recent_signals(limit=10):
    """Последние сигналы (включая закрытые)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def update_signal_status(signal_id: int, status: str, result_price: float = None):
    """Закрыть сделку: win / loss / expired."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE signals
        SET status = ?, result_price = ?, closed_at = ?
        WHERE id = ?
    """, (status, result_price, datetime.utcnow().isoformat(), signal_id))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    """Собрать статистику по всем сделкам."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    stats = {"total": 0, "win": 0, "loss": 0, "expired": 0, "active": 0,
             "by_type": {}, "avg_rr": 0.0}

    c.execute("SELECT COUNT(*), AVG(rr) FROM signals")
    row = c.fetchone()
    stats["total"] = row[0] or 0
    stats["avg_rr"] = round(row[1], 2) if row[1] else 0.0

    c.execute("SELECT status, COUNT(*) FROM signals GROUP BY status")
    for status, count in c.fetchall():
        if status in stats:
            stats[status] = count

    # Разбивка по типам сделок
    c.execute("""
        SELECT trade_type,
               COUNT(*),
               SUM(CASE WHEN status='win' THEN 1 ELSE 0 END),
               SUM(CASE WHEN status='loss' THEN 1 ELSE 0 END)
        FROM signals
        GROUP BY trade_type
    """)
    for ttype, total, wins, losses in c.fetchall():
        closed = wins + losses
        winrate = round(wins / closed * 100, 1) if closed > 0 else 0.0
        stats["by_type"][ttype] = {
            "total": total,
            "win": wins,
            "loss": losses,
            "winrate": winrate,
        }

    conn.close()
    return stats
