from datetime import datetime, timezone
from pathlib import Path

from tiance.db.sqlite import connect
from tiance.errors import AlreadyWatching, StockNotFound
from tiance.models import WatchlistRow


class WatchlistService:
    def __init__(self, db_path: Path, tianyan_client) -> None:
        self.db_path = db_path
        self.tianyan_client = tianyan_client

    def add_stock(self, query: str, group_id: int | None = None) -> WatchlistRow:
        security = self.tianyan_client.search_security(query)
        if security is None:
            raise StockNotFound(f"未找到股票：{query}")

        with connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT secucode FROM watchlist WHERE secucode = ?",
                (security.secucode,),
            ).fetchone()
            if existing is not None:
                raise AlreadyWatching(f"已在自选列表：{security.secucode}")

            max_sort_order = conn.execute(
                "SELECT COALESCE(MAX(sort_order), 0) FROM watchlist"
            ).fetchone()[0]
            added_at = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO watchlist(secucode, secuname, group_id, sort_order, added_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    security.secucode,
                    security.secuname,
                    group_id,
                    max_sort_order + 1,
                    added_at,
                ),
            )
            conn.commit()

        return self.get_stock(security.secucode)

    def get_stock(self, secucode: str) -> WatchlistRow:
        with connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT
                  w.secucode,
                  w.secuname,
                  w.note,
                  w.group_id,
                  w.sort_order,
                  w.added_at,
                  COALESCE(SUM(CASE WHEN a.is_read = 0 THEN 1 ELSE 0 END), 0) AS unread_count,
                  NULL AS range_pct
                FROM watchlist w
                LEFT JOIN announcements a ON a.secucode = w.secucode
                WHERE w.secucode = ?
                GROUP BY w.secucode
                """,
                (secucode,),
            ).fetchone()

        if row is None:
            raise StockNotFound(f"未找到股票：{secucode}")
        return WatchlistRow.model_validate(dict(row))

    def list_watchlist(self) -> list[WatchlistRow]:
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT
                  w.secucode,
                  w.secuname,
                  w.note,
                  w.group_id,
                  w.sort_order,
                  w.added_at,
                  COALESCE(SUM(CASE WHEN a.is_read = 0 THEN 1 ELSE 0 END), 0) AS unread_count,
                  NULL AS range_pct
                FROM watchlist w
                LEFT JOIN announcements a ON a.secucode = w.secucode
                GROUP BY w.secucode
                ORDER BY w.sort_order ASC, w.added_at ASC
                """
            ).fetchall()

        return [WatchlistRow.model_validate(dict(row)) for row in rows]

    def remove_stock(self, secucode: str) -> None:
        with connect(self.db_path) as conn:
            result = conn.execute(
                "DELETE FROM watchlist WHERE secucode = ?",
                (secucode,),
            )
            conn.commit()

        if result.rowcount == 0:
            raise StockNotFound(f"未找到股票：{secucode}")
