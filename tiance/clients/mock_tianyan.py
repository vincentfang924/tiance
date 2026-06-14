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
            Security(secucode="300502.SZ", secuname="\u65b0\u6613\u76db"),
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
                        "adj_close_backward": close_price,
                        "adj_factor": 1,
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

    def get_stock_concepts(self, secucode: str) -> list[dict]:
        if secucode != "300502.SZ":
            return [
                {
                    "concept_code": 11100011,
                    "concept_name": "\u82af\u7247\u6982\u5ff5",
                    "class_name": "\u79d1\u6280",
                    "subclass_name": "\u5236\u90202025",
                }
            ]
        return [
            {
                "concept_code": 11062211,
                "concept_name": "\u5171\u5c01\u88c5\u5149\u6a21\u5757(CPO\uff09",
                "class_name": "\u79d1\u6280",
                "subclass_name": "\u65b0\u79d1\u6280",
            },
            {
                "concept_code": 11102190,
                "concept_name": "\u5149\u901a\u4fe1",
                "class_name": "\u79d1\u6280",
                "subclass_name": "\u5236\u90202025",
            },
            {
                "concept_code": 15030008,
                "concept_name": "\u878d\u8d44\u878d\u5238",
                "class_name": "\u5176\u4ed6",
                "subclass_name": "\u7279\u6b8a\u80a1\u7968",
            },
        ]

    def get_concept_moneyflow(self, concept_codes: list[int]) -> dict:
        rows = {
            11062211: {
                "concept_code": 11062211,
                "flow_1d": -860082.2174,
                "flow_5d": -2648311.1115,
                "flow_20d": 134566.1383,
                "stock_count": 175,
            },
            11102190: {
                "concept_code": 11102190,
                "flow_1d": 12000,
                "flow_5d": 23000,
                "flow_20d": 230000,
                "stock_count": 83,
            },
            11100011: {
                "concept_code": 11100011,
                "flow_1d": 21000,
                "flow_5d": -11000,
                "flow_20d": 32000,
                "stock_count": 128,
            },
        }
        return {
            "latest_trade_date": "20260612",
            "items": [rows[code] for code in concept_codes if code in rows],
        }


def _coerce_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)
