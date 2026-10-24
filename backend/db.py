import os
import sqlite3
import time
from contextlib import contextmanager

DB_PATH = os.environ.get("RECEIPTS_DB", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "receipts.db"))
_SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with conn() as c:
        c.executescript(open(_SCHEMA).read())
        # lightweight migrations for DBs created before these columns existed
        for sql in (
            "ALTER TABLE trace ADD COLUMN actor TEXT DEFAULT 'system'",
            "ALTER TABLE candidates ADD COLUMN incumbent INTEGER DEFAULT 0",
        ):
            try:
                c.execute(sql)
            except sqlite3.OperationalError:
                pass


def q(sql, args=()):
    with conn() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def one(sql, args=()):
    rows = q(sql, args)
    return rows[0] if rows else None


def ins(sql, args=()):
    with conn() as c:
        return c.execute(sql, args).lastrowid


def touch_run(run_id, **fields):
    fields["updated_at"] = time.time()
    sql = "UPDATE runs SET " + ", ".join(f"{k}=?" for k in fields) + " WHERE id=?"
    with conn() as c:
        c.execute(sql, (*fields.values(), run_id))
