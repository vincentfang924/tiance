from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class Security:
    secucode: str
    secuname: str


class MockTianyanClient:
    def __init__(self) -> None:
        self._securities = [
            Security(secucode="600519.SH", secuname="贵州茅台"),
            Security(secucode="300750.SZ", secuname="宁德时代"),
            Security(secucode="000001.SZ", secuname="平安银行"),
        ]
        self._announcements = {
            "600519.SH": [
                {
                    "secucode": "600519.SH",
                    "publish_date": date(2026, 3, 18),
                    "title": "贵州茅台关于签订重大合同的公告",
                    "url": "mock://announcements/600519/2026-03-18",
                }
            ],
            "300750.SZ": [
                {
                    "secucode": "300750.SZ",
                    "publish_date": date(2026, 2, 10),
                    "title": "宁德时代关于战略合作协议签订的公告",
                    "url": "mock://announcements/300750/2026-02-10",
                }
            ],
            "000001.SZ": [
                {
                    "secucode": "000001.SZ",
                    "publish_date": date(2026, 1, 15),
                    "title": "平安银行业务进展公告",
                    "url": "mock://announcements/000001/2026-01-15",
                }
            ],
        }

    def list_securities(self) -> list[Security]:
        return list(self._securities)

    def search_security(self, query: str) -> Security | None:
        normalized = query.strip().upper()
        for security in self._securities:
            code = security.secucode.upper()
            six_digit_code = code.split(".", maxsplit=1)[0]
            if normalized in {code, six_digit_code}:
                return security
            if query.strip() and query.strip() in security.secuname:
                return security
        return None

    def get_daily_kline(self, secucode: str, start: date, end: date) -> list[dict]:
        current = _coerce_date(start)
        end_date = _coerce_date(end)
        rows = []
        seed = sum(ord(char) for char in secucode) % 100

        while current <= end_date:
            if current.weekday() < 5:
                offset = len(rows)
                open_price = round(100 + seed + offset * 0.8, 2)
                close_price = round(open_price + 0.6, 2)
                rows.append(
                    {
                        "date": current,
                        "open": open_price,
                        "close": close_price,
                        "low": round(open_price - 1.2, 2),
                        "high": round(close_price + 1.4, 2),
                        "volume": 1_000_000 + offset * 10_000,
                    }
                )
            current += timedelta(days=1)

        return rows

    def get_announcements(self, secucode: str, since: date) -> list[dict]:
        since_date = _coerce_date(since)
        return [
            dict(announcement)
            for announcement in self._announcements.get(secucode, [])
            if announcement["publish_date"] > since_date
        ]


def _coerce_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)
