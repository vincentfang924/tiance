import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from tiance.db.sqlite import connect
from tiance.errors import InvalidFreq
from tiance.models import KlineData, KlinePoint
from tiance.services.indicators import _nullable_float, add_ma, add_macd, resample_ohlcv


class MarketService:
    def __init__(self, tianyan_client, db_path: Path | None = None) -> None:
        self.tianyan_client = tianyan_client
        self.db_path = db_path

    def get_kline(
        self,
        secucode: str,
        start: date | None = None,
        end: date | None = None,
        freq: str = "D",
        ma: list[int] | None = None,
    ) -> KlineData:
        if freq not in {"D", "W", "M"}:
            raise InvalidFreq(f"不支持的K线频率：{freq}")

        end_date = end or date.today()
        start_date = start or end_date - timedelta(days=365)
        rows = self.tianyan_client.get_daily_kline(secucode, start_date, end_date)
        if not rows:
            return KlineData(secucode=secucode, freq=freq, points=[])
        self._backup_daily_rows(secucode, rows)

        frame = pd.DataFrame(rows)
        frame = resample_ohlcv(frame, freq)
        if ma:
            frame = add_ma(frame, ma)
        frame = add_macd(frame)
        frame["pct_change"] = frame["close"].pct_change() * 100
        frame["volume_change_pct"] = frame["volume"].pct_change() * 100

        points = [self._point_from_row(row, ma or []) for _, row in frame.iterrows()]
        return KlineData(secucode=secucode, freq=freq, points=points)

    def _point_from_row(self, row, ma_periods: list[int]) -> KlinePoint:
        point_date = row["date"]
        if hasattr(point_date, "date"):
            point_date = point_date.date()

        return KlinePoint(
            date=point_date,
            open=_nullable_float(row["open"]),
            close=_nullable_float(row["close"]),
            low=_nullable_float(row["low"]),
            high=_nullable_float(row["high"]),
            volume=_nullable_float(row["volume"]),
            pct_change=_nullable_float(row["pct_change"]),
            volume_change_pct=_nullable_float(row["volume_change_pct"]),
            ma={f"ma{period}": _nullable_float(row[f"ma{period}"]) for period in ma_periods},
            macd={
                "dif": _nullable_float(row["dif"]),
                "dea": _nullable_float(row["dea"]),
                "macd": _nullable_float(row["macd"]),
            },
        )

    def _backup_daily_rows(self, secucode: str, rows: list[dict]) -> None:
        if self.db_path is None:
            return
        now = datetime.now(timezone.utc).isoformat()
        with connect(self.db_path) as conn:
            for row in rows:
                trade_date = _date_text(row["date"])
                conn.execute(
                    """
                    INSERT INTO market_bars(
                      secucode,
                      trade_date,
                      open,
                      high,
                      low,
                      close,
                      volume,
                      source,
                      raw_payload,
                      created_at,
                      updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(secucode, trade_date) DO UPDATE SET
                      open = excluded.open,
                      high = excluded.high,
                      low = excluded.low,
                      close = excluded.close,
                      volume = excluded.volume,
                      source = excluded.source,
                      raw_payload = excluded.raw_payload,
                      updated_at = excluded.updated_at
                    """,
                    (
                        secucode,
                        trade_date,
                        _nullable_float(row.get("open")),
                        _nullable_float(row.get("high")),
                        _nullable_float(row.get("low")),
                        _nullable_float(row.get("close")),
                        _nullable_float(row.get("volume")),
                        "tianyan",
                        json.dumps(row, ensure_ascii=False, default=str),
                        now,
                        now,
                    ),
                )
            conn.commit()


def _date_text(value) -> str:
    if hasattr(value, "date"):
        value = value.date()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)
