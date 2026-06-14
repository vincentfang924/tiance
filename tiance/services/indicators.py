import pandas as pd


def _nullable_float(value):
    if pd.isna(value):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric):
        return None
    return round(numeric, 6)


def _nullable_series(series: pd.Series) -> pd.Series:
    return pd.Series(
        [_nullable_float(value) for value in series],
        index=series.index,
        dtype=object,
    )


def add_ma(df: pd.DataFrame, periods: list[int]) -> pd.DataFrame:
    result = df.copy()
    for period in periods:
        values = result["close"].rolling(window=period, min_periods=period).mean()
        result[f"ma{period}"] = _nullable_series(values)
    return result


def add_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    result = df.copy()
    close = result["close"].astype(float)
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd = (dif - dea) * 2
    result["dif"] = _nullable_series(dif)
    result["dea"] = _nullable_series(dea)
    result["macd"] = _nullable_series(macd)
    return result


def resample_ohlcv(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    if freq == "D":
        return df.copy()

    rule = {"W": "W-FRI", "M": "ME"}[freq]
    source = df.copy()
    source["date"] = pd.to_datetime(source["date"])
    aggregated = (
        source.set_index("date")
        .resample(rule)
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna(subset=["open", "high", "low", "close"])
        .reset_index()
    )
    return aggregated
