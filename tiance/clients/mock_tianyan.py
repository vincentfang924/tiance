from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class Security:
    secucode: str
    secuname: str


class MockTianyanClient:
    def __init__(self) -> None:
        recent = date.today() - timedelta(days=2)
        self._securities = [
            Security(secucode="600519.SH", secuname="\u8d35\u5dde\u8305\u53f0"),
            Security(secucode="300750.SZ", secuname="\u5b81\u5fb7\u65f6\u4ee3"),
            Security(secucode="000001.SZ", secuname="\u5e73\u5b89\u94f6\u884c"),
            Security(secucode="301511.SZ", secuname="\u5fb7\u798f\u79d1\u6280"),
        ]
        self._announcements = {
            "600519.SH": [
                {
                    "secucode": "600519.SH",
                    "publish_date": recent,
                    "title": "\u8d35\u5dde\u8305\u53f0\u5173\u4e8e\u8058\u4efb\u8463\u4e8b\u4f1a\u79d8\u4e66\u7684\u516c\u544a",
                    "url": "mock://announcements/600519/recent",
                },
                {
                    "secucode": "600519.SH",
                    "publish_date": date(2026, 3, 18),
                    "title": "\u8d35\u5dde\u8305\u53f0\u5173\u4e8e\u7b7e\u8ba2\u91cd\u5927\u5408\u540c\u7684\u516c\u544a",
                    "url": "mock://announcements/600519/2026-03-18",
                },
            ],
            "300750.SZ": [
                {
                    "secucode": "300750.SZ",
                    "publish_date": date(2026, 2, 10),
                    "title": "\u5b81\u5fb7\u65f6\u4ee3\u5173\u4e8e\u6218\u7565\u5408\u4f5c\u534f\u8bae\u7b7e\u8ba2\u7684\u516c\u544a",
                    "url": "mock://announcements/300750/2026-02-10",
                }
            ],
            "000001.SZ": [
                {
                    "secucode": "000001.SZ",
                    "publish_date": date(2026, 1, 15),
                    "title": "\u5e73\u5b89\u94f6\u884c\u4e1a\u52a1\u8fdb\u5c55\u516c\u544a",
                    "url": "mock://announcements/000001/2026-01-15",
                }
            ],
            "301511.SZ": [
                {
                    "secucode": "301511.SZ",
                    "publish_date": recent,
                    "title": "\u5fb7\u798f\u79d1\u6280\u5173\u4e8e\u54112026\u5e74\u9650\u5236\u6027\u80a1\u7968\u6fc0\u52b1\u8ba1\u5212\u6fc0\u52b1\u5bf9\u8c61\u6388\u4e88\u9650\u5236\u6027\u80a1\u7968\u7684\u516c\u544a",
                    "url": "mock://announcements/301511/recent",
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
