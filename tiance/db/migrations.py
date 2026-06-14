from pathlib import Path

from tiance.db.sqlite import connect


SCHEMA = """
CREATE TABLE IF NOT EXISTS groups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist (
  secucode TEXT PRIMARY KEY,
  secuname TEXT NOT NULL,
  group_id INTEGER REFERENCES groups(id),
  note TEXT,
  sort_order INTEGER NOT NULL DEFAULT 0,
  added_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS concepts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  source TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_concepts (
  secucode TEXT NOT NULL REFERENCES watchlist(secucode) ON DELETE CASCADE,
  concept_id INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
  added_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY(secucode, concept_id)
);

CREATE TABLE IF NOT EXISTS announcements (
  ann_id TEXT PRIMARY KEY,
  secucode TEXT NOT NULL,
  title TEXT NOT NULL,
  ann_type TEXT,
  category_l1 TEXT,
  category_l1_label TEXT,
  category_bucket TEXT NOT NULL,
  is_keyword_hit INTEGER NOT NULL DEFAULT 0,
  publish_at TEXT NOT NULL,
  source TEXT NOT NULL,
  url TEXT,
  local_path TEXT,
  raw_payload TEXT,
  is_read INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS money_flows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  secucode TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  main_net_inflow REAL,
  main_net_inflow_pct REAL,
  raw_payload TEXT,
  UNIQUE(secucode, trade_date)
);

CREATE TABLE IF NOT EXISTS rank_list_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  secucode TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  reason TEXT NOT NULL DEFAULT '',
  amount REAL,
  raw_payload TEXT,
  UNIQUE(secucode, trade_date, reason)
);

CREATE TABLE IF NOT EXISTS task_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_name TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  rows_affected INTEGER,
  error TEXT
);

CREATE INDEX IF NOT EXISTS idx_announcements_secucode_publish
  ON announcements(secucode, publish_at DESC);
CREATE INDEX IF NOT EXISTS idx_task_runs_task_started
  ON task_runs(task_name, started_at DESC);
"""


def migrate(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
