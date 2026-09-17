import sqlite3
from datetime import datetime, timedelta

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
            triggered INTEGER DEFAULT 0,
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS toxic_coins (
            symbol TEXT PRIMARY KEY,
            fail_streak INTEGER DEFAULT 0,
            until TEXT
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


def has_active_signal(symbol: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT COUNT(*) FROM signals WHERE symbol = ? AND status = 'active'",
        (symbol,)
    )
    count = c.fetchone()[0]
    conn.close()
    return count > 0


def get_active_signals(limit=100):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT * FROM signals WHERE status='active' ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def get_recent_signals(limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def mark_triggered(signal_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE signals SET triggered = 1 WHERE id = ?", (signal_id,))
    conn.commit()
    conn.close()


def update_signal_status(signal_id: int, status: str, result_price: float = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE signals
        SET status = ?, result_price = ?, closed_at = ?
        WHERE id = ?
    """, (status, result_price, datetime.utcnow().isoformat(), signal_id))
    conn.commit()
    conn.close()


# ─── Журнал «токсичных» монет ────────────────────────────────────
def get_toxic_symbols() -> list:
    """Вернуть монеты, которые временно исключены из сканирования."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("SELECT symbol FROM toxic_coins WHERE until > ?", (now,))
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows


def register_loss(symbol: str):
    """Зарегистрировать убыток. Если стрик >= TOXIC_STREAK — добавить в токсичные."""
    from config import TOXIC_STREAK, TOXIC_COOLDOWN_HOURS
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT fail_streak FROM toxic_coins WHERE symbol = ?", (symbol,))
    row = c.fetchone()
    streak = (row[0] + 1) if row else 1

    if streak >= TOXIC_STREAK:
        until = (datetime.utcnow() + timedelta(hours=TOXIC_COOLDOWN_HOURS)).isoformat()
        c.execute("""
            INSERT INTO toxic_coins (symbol, fail_streak, until)
            VALUES (?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET fail_streak = ?, until = ?
        """, (symbol, streak, until, streak, until))
    else:
        c.execute("""
            INSERT INTO toxic_coins (symbol, fail_streak, until)
            VALUES (?, ?, NULL)
            ON CONFLICT(symbol) DO UPDATE SET fail_streak = ?
        """, (symbol, streak, streak))
    conn.commit()
    conn.close()


def register_win(symbol: str):
    """Сбросить стрик убытков при выигрыше."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM toxic_coins WHERE symbol = ?", (symbol,))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    stats = {
        "total": 0, "win": 0, "loss": 0, "expired": 0,
        "active": 0, "not_triggered": 0,
        "by_type": {}, "avg_rr": 0.0,
    }

    c.execute("SELECT COUNT(*), AVG(rr) FROM signals")
    row = c.fetchone()
    stats["total"] = row[0] or 0
    stats["avg_rr"] = round(row[1], 2) if row[1] else 0.0

    c.execute("SELECT status, COUNT(*) FROM signals GROUP BY status")
    for status, count in c.fetchall():
        if status in stats:
            stats[status] = count

    c.execute("""
        SELECT trade_type,
               COUNT(*),
               SUM(CASE WHEN status='win' THEN 1 ELSE 0 END),
               SUM(CASE WHEN status='loss' THEN 1 ELSE 0 END),
               SUM(CASE WHEN status='not_triggered' THEN 1 ELSE 0 END)
        FROM signals
        GROUP BY trade_type
    """)
    for ttype, total, wins, losses, not_trig in c.fetchall():
        closed = wins + losses
        winrate = round(wins / closed * 100, 1) if closed > 0 else 0.0
        stats["by_type"][ttype] = {
            "total": total,
            "win": wins,
            "loss": losses,
            "not_triggered": not_trig,
            "winrate": winrate,
        }

    conn.close()
    return stats
