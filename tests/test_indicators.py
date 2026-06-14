from datetime import date

import pandas as pd
import pytest

from tiance.clients.mock_tianyan import MockTianyanClient
from tiance.db.migrations import migrate
from tiance.db.sqlite import connect
from tiance.errors import InvalidFreq
from tiance.services.indicators import _nullable_float, add_macd, add_ma, resample_ohlcv
from tiance.services.market import MarketService


def test_add_ma_adds_expected_column():
    df = pd.DataFrame({"close": [1, 2, 3, 4, 5]})
    result = add_ma(df, [3])
    assert result["ma3"].tolist() == [None, None, 2.0, 3.0, 4.0]


def test_nullable_float_returns_none_for_pd_na():
    assert _nullable_float(pd.NA) is None


def test_nullable_float_returns_none_for_non_numeric_string():
    assert _nullable_float("abc") is None


def test_add_macd_adds_columns():
    df = pd.DataFrame({"close": list(range(1, 40))})
    result = add_macd(df)
    assert {"dif", "dea", "macd"}.issubset(result.columns)


def test_resample_weekly_uses_ohlcv_rules():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-01", "2026-06-02", "2026-06-03"]),
            "open": [10, 11, 12],
            "high": [11, 12, 13],
            "low": [9, 8, 10],
            "close": [10.5, 11.5, 12.5],
            "volume": [100, 200, 300],
        }
    )
    result = resample_ohlcv(df, "W")
    assert result.iloc[0]["open"] == 10
    assert result.iloc[0]["high"] == 13
    assert result.iloc[0]["low"] == 8
    assert result.iloc[0]["close"] == 12.5
    assert result.iloc[0]["volume"] == 600


def test_market_service_get_kline_returns_points_with_ma_and_macd():
    service = MarketService(MockTianyanClient())

    result = service.get_kline(
        "600519.SH",
        start=date(2026, 6, 1),
        end=date(2026, 6, 8),
        freq="D",
        ma=[3],
    )

    assert result.secucode == "600519.SH"
    assert result.freq == "D"
    assert result.points
    assert "ma3" in result.points[-1].ma
    assert {"dif", "dea", "macd"} <= set(result.points[-1].macd)


def test_market_service_get_kline_adds_price_and_volume_percent_changes():
    service = MarketService(MockTianyanClient())

    result = service.get_kline(
        "600519.SH",
        start=date(2026, 6, 1),
        end=date(2026, 6, 5),
        freq="D",
        ma=[],
    )

    assert result.points[0].pct_change is None
    assert result.points[0].volume_change_pct is None
    assert result.points[1].pct_change is not None
    assert result.points[1].volume_change_pct == 1.0


def test_market_service_backs_up_daily_kline_rows_to_sqlite(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    service = MarketService(MockTianyanClient(), db_path=db_path)

    service.get_kline(
        "600519.SH",
        start=date(2026, 6, 1),
        end=date(2026, 6, 8),
        freq="D",
        ma=[3],
    )

    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT secucode, trade_date, open, high, low, close, volume, source
            FROM market_bars
            WHERE secucode = ?
            ORDER BY trade_date ASC
            """,
            ("600519.SH",),
        ).fetchall()

    assert rows
    assert rows[0]["trade_date"] == "2026-06-01"
    assert rows[0]["source"] == "tianyan"


def test_market_service_get_kline_rejects_invalid_freq():
    service = MarketService(MockTianyanClient())

    with pytest.raises(InvalidFreq):
        service.get_kline(
            "600519.SH",
            start=date(2026, 6, 1),
            end=date(2026, 6, 8),
            freq="X",
        )
