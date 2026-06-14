from datetime import date, timedelta

import pandas as pd

from tiance.errors import InvalidFreq
from tiance.models import KlineData, KlinePoint
from tiance.services.indicators import _nullable_float, add_ma, add_macd, resample_ohlcv


class MarketService:
    def __init__(self, tianyan_client) -> None:
        self.tianyan_client = tianyan_client

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

        frame = pd.DataFrame(rows)
        frame = resample_ohlcv(frame, freq)
        if ma:
            frame = add_ma(frame, ma)
        frame = add_macd(frame)

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
            ma={f"ma{period}": _nullable_float(row[f"ma{period}"]) for period in ma_periods},
            macd={
                "dif": _nullable_float(row["dif"]),
                "dea": _nullable_float(row["dea"]),
                "macd": _nullable_float(row["macd"]),
            },
        )
