import sqlite3

from tiance.db.migrations import migrate
from tiance.db.sqlite import connect, rows_to_dicts


def test_migration_is_idempotent(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    migrate(db_path)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()

    table_names = {row[0] for row in rows}
    assert "watchlist" in table_names
    assert "announcements" in table_names
    assert "task_runs" in table_names


def test_raw_payload_columns_exist(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    with sqlite3.connect(db_path) as conn:
        announcement_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(announcements)")
        }
        money_cols = {row[1] for row in conn.execute("PRAGMA table_info(money_flows)")}
    assert "raw_payload" in announcement_cols
    assert "raw_payload" in money_cols


def test_rank_list_reason_uses_empty_string_for_uniqueness(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)

    with sqlite3.connect(db_path) as conn:
        reason_col = next(
            row for row in conn.execute("PRAGMA table_info(rank_list_events)") if row[1] == "reason"
        )
        conn.execute(
            """
            INSERT INTO rank_list_events(secucode, trade_date, reason, amount)
            VALUES (?, ?, ?, ?)
            """,
            ("000001.SZ", "2026-06-08", "", 10.5),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO rank_list_events(secucode, trade_date, reason, amount)
            VALUES (?, ?, ?, ?)
            """,
            ("000001.SZ", "2026-06-08", "", 11.5),
        )
        count = conn.execute("SELECT COUNT(*) FROM rank_list_events").fetchone()[0]

    assert reason_col[3] == 1
    assert reason_col[4] == "''"
    assert count == 1


def test_connect_enables_named_rows_and_foreign_keys(tmp_path):
    db_path = tmp_path / "tiance.db"
    with connect(db_path) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        conn.execute("INSERT INTO sample(name) VALUES (?)", ("alpha",))
        row = conn.execute("SELECT id, name FROM sample").fetchone()
        foreign_keys = conn.execute("PRAGMA foreign_keys").fetchone()[0]

    assert row["name"] == "alpha"
    assert foreign_keys == 1


def test_rows_to_dicts_converts_sqlite_rows(tmp_path):
    db_path = tmp_path / "tiance.db"
    with connect(db_path) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        conn.execute("INSERT INTO sample(name) VALUES (?)", ("alpha",))
        rows = conn.execute("SELECT id, name FROM sample").fetchall()

    assert rows_to_dicts(rows) == [{"id": 1, "name": "alpha"}]


def test_migration_creates_indexes(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
        ).fetchall()

    index_names = {row[0] for row in rows}
    assert "idx_announcements_secucode_publish" in index_names
    assert "idx_task_runs_task_started" in index_names
