from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from tiance.db.sqlite import connect


def run_tracked(db_path: Path, task_name: str, work: Callable[[], object]) -> int:
    started_at = datetime.now().isoformat(timespec="seconds")
    with connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO task_runs(task_name, started_at, status)
            VALUES (?, ?, ?)
            """,
            (task_name, started_at, "running"),
        )
        run_id = cursor.lastrowid
        conn.commit()

    try:
        rows_affected = _normalize_rows_affected(work())
        with connect(db_path) as conn:
            conn.execute(
                """
                UPDATE task_runs
                SET finished_at = ?, status = ?, rows_affected = ?
                WHERE id = ?
                """,
                (
                    datetime.now().isoformat(timespec="seconds"),
                    "success",
                    rows_affected,
                    run_id,
                ),
            )
            conn.commit()
    except Exception as exc:
        with connect(db_path) as conn:
            conn.execute(
                """
                UPDATE task_runs
                SET finished_at = ?, status = ?, error = ?
                WHERE id = ?
                """,
                (
                    datetime.now().isoformat(timespec="seconds"),
                    "failed",
                    str(exc),
                    run_id,
                ),
            )
            conn.commit()
        raise
    return rows_affected


def create_scheduler() -> BackgroundScheduler:
    return BackgroundScheduler(timezone="Asia/Shanghai")


def _normalize_rows_affected(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TypeError("rows_affected must be an integer-compatible value") from exc
