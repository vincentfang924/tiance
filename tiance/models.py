from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


SecuCode = str
Freq = Literal["D", "W", "M"]


class AddStockRequest(BaseModel):
    query: str = Field(min_length=1)
    group_id: int | None = None


class WatchlistPatch(BaseModel):
    note: str | None = None
    group_id: int | None = None
    sort_order: int | None = None


class WatchlistRow(BaseModel):
    secucode: str
    secuname: str
    note: str | None = None
    group_id: int | None = None
    sort_order: int
    added_at: datetime
    unread_count: int = 0
    range_pct: float | None = None


class KlinePoint(BaseModel):
    date: date
    open: float
    close: float
    low: float
    high: float
    volume: float
    pct_change: float | None = None
    volume_change_pct: float | None = None
    ma: dict[str, float | None] = Field(default_factory=dict)
    macd: dict[str, float | None] = Field(default_factory=dict)


class KlineData(BaseModel):
    secucode: str
    freq: Freq
    points: list[KlinePoint]
