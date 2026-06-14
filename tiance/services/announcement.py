import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from tiance.db.sqlite import connect, rows_to_dicts


CAPITAL_FLOW_KEYWORDS = ("大宗交易", "龙虎榜", "异动")
BUSINESS_KEYWORDS = (
    "订单",
    "合作",
    "涨价",
    "人事",
    "业绩",
    "年报",
    "半年报",
    "季报",
    "预告",
    "增持",
    "减持",
    "回购",
    "签订",
    "中标",
    "重大合同",
)


def classify_announcement(title: str, category_l1_label: str | None = None) -> str:
    text = f"{title or ''} {category_l1_label or ''}"
    if any(keyword in text for keyword in CAPITAL_FLOW_KEYWORDS):
        return "capital_flow"
    if any(keyword in text for keyword in BUSINESS_KEYWORDS):
        return "business"
    return "other"


class AnnouncementService:
    def __init__(self, db_path: Path, tianyan_client) -> None:
        self.db_path = db_path
        self.tianyan_client = tianyan_client

    def fetch_all_watchlist(self, since: date | datetime | str | None = None) -> int:
        since_date = _coerce_date(since) if since is not None else date.today() - timedelta(days=7)
        with connect(self.db_path) as conn:
            secucodes = [
                row["secucode"]
                for row in conn.execute("SELECT secucode FROM watchlist ORDER BY sort_order ASC").fetchall()
            ]

        return sum(self.fetch_for(secucode, since_date) for secucode in secucodes)

    def fetch_for(self, secucode: str, since: date | datetime | str) -> int:
        since_date = _coerce_date(since)
        rows = self.tianyan_client.get_announcements(secucode, since_date)
        inserted = 0
        now = datetime.now(timezone.utc).isoformat()

        with connect(self.db_path) as conn:
            for row in rows:
                title = row.get("title") or ""
                category_l1_label = row.get("category_l1_label")
                bucket = classify_announcement(title, category_l1_label)
                publish_at = _coerce_publish_at(row)
                ann_id = _announcement_id(secucode, row, publish_at)
                result = conn.execute(
                    """
                    INSERT OR IGNORE INTO announcements(
                      ann_id,
                      secucode,
                      title,
                      ann_type,
                      category_l1,
                      category_l1_label,
                      category_bucket,
                      is_keyword_hit,
                      publish_at,
                      source,
                      url,
                      local_path,
                      raw_payload,
                      created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ann_id,
                        row.get("secucode") or secucode,
                        title,
                        row.get("ann_type"),
                        row.get("category_l1"),
                        category_l1_label,
                        bucket,
                        1 if bucket != "other" else 0,
                        publish_at,
                        row.get("source") or "tianyan",
                        row.get("url"),
                        row.get("local_path"),
                        json.dumps(row, ensure_ascii=False, default=str),
                        now,
                    ),
                )
                inserted += result.rowcount
            conn.commit()

        return inserted

    def list_for_stock(
        self,
        secucode: str,
        bucket: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        safe_limit = max(1, min(limit, 200))
        params: list[object] = [secucode]
        sql = "SELECT * FROM announcements WHERE secucode = ?"
        if bucket:
            sql += " AND category_bucket = ?"
            params.append(bucket)
        sql += " ORDER BY publish_at DESC LIMIT ?"
        params.append(safe_limit)

        with connect(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return rows_to_dicts(rows)


def _coerce_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _coerce_publish_at(row: dict) -> str:
    value = row.get("publish_at") or row.get("publish_date")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc).isoformat()
    if value:
        return str(value)
    return datetime.now(timezone.utc).isoformat()


def _announcement_id(secucode: str, row: dict, publish_at: str) -> str:
    if row.get("ann_id"):
        return f"{secucode}:{row['ann_id']}"
    if row.get("id"):
        return f"{secucode}:{row['id']}"
    return f"{secucode}:{publish_at}:{row.get('title', '')}"
