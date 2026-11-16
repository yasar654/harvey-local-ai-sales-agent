from __future__ import annotations
import os, sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(os.getenv("HARVEY_DB_PATH", Path(__file__).resolve().parents[2] / "data" / "harvey.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS businesses(
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
 website TEXT NOT NULL DEFAULT '', industry TEXT NOT NULL DEFAULT '', profile TEXT NOT NULL DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS products(
 id INTEGER PRIMARY KEY, business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
 name TEXT NOT NULL, description TEXT NOT NULL, benefits TEXT NOT NULL DEFAULT '', target_market TEXT NOT NULL DEFAULT '', icp TEXT NOT NULL DEFAULT '',
 created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS prospects(
 id INTEGER PRIMARY KEY, product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
 company TEXT NOT NULL, website TEXT NOT NULL DEFAULT '', industry TEXT NOT NULL DEFAULT '',
 company_size TEXT NOT NULL DEFAULT '', contact_name TEXT NOT NULL DEFAULT '', title TEXT NOT NULL DEFAULT '',
 email TEXT NOT NULL DEFAULT '', location TEXT NOT NULL DEFAULT '', source_text TEXT NOT NULL DEFAULT '',
 research TEXT NOT NULL DEFAULT '', buying_signals TEXT NOT NULL DEFAULT '[]', problem_statement TEXT NOT NULL DEFAULT '',
 score INTEGER NOT NULL DEFAULT 0, score_reason TEXT NOT NULL DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS generated(
 id INTEGER PRIMARY KEY, prospect_id INTEGER REFERENCES prospects(id) ON DELETE CASCADE,
 kind TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS prospect_embeddings(
 prospect_id INTEGER PRIMARY KEY REFERENCES prospects(id) ON DELETE CASCADE,
 model TEXT NOT NULL, vector BLOB NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS logs(
 id INTEGER PRIMARY KEY, event TEXT NOT NULL, model TEXT NOT NULL DEFAULT '', status TEXT NOT NULL,
 duration_ms INTEGER NOT NULL DEFAULT 0, details TEXT NOT NULL DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS ai_tasks(
 id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, prompt TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'queued', attempts INTEGER NOT NULL DEFAULT 0,
 result TEXT NOT NULL DEFAULT '', last_error TEXT NOT NULL DEFAULT '',
 created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""

@contextmanager
def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        db.commit()
    finally:
        db.close()

def init_db():
    with connect() as db:
        db.executescript(SCHEMA)
        # Additive migrations keep existing local databases compatible.
        business_columns = {row[1] for row in db.execute("PRAGMA table_info(businesses)")}
        if "profile" not in business_columns:
            db.execute("ALTER TABLE businesses ADD COLUMN profile TEXT NOT NULL DEFAULT ''")
        product_columns = {row[1] for row in db.execute("PRAGMA table_info(products)")}
        if "icp" not in product_columns:
            db.execute("ALTER TABLE products ADD COLUMN icp TEXT NOT NULL DEFAULT ''")

def rows(sql: str, args=()):
    with connect() as db:
        return [dict(r) for r in db.execute(sql, args).fetchall()]

def one(sql: str, args=()):
    result = rows(sql, args)
    return result[0] if result else None
