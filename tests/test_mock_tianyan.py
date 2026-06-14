from datetime import date, datetime, timedelta

from tiance.clients.mock_tianyan import MockTianyanClient
from tiance.clients.tianyan import create_tianyan_client
from tiance.config import Settings


def test_search_security_by_name_returns_maotai_secucode():
    client = MockTianyanClient()

    result = client.search_security("茅台")

    assert result.secucode == "600519.SH"


def test_search_security_by_name_returns_defu_secucode():
    client = MockTianyanClient()

    result = client.search_security("德福科技")

    assert result.secucode == "301511.SZ"


def test_search_security_by_six_digit_code_returns_full_secucode():
    client = MockTianyanClient()

    result = client.search_security("600519")

    assert result.secucode == "600519.SH"


def test_search_security_by_full_code_returns_full_secucode():
    client = MockTianyanClient()

    result = client.search_security("600519.SH")

    assert result.secucode == "600519.SH"


def test_list_securities_contains_builtin_securities():
    client = MockTianyanClient()

    securities = {(item.secucode, item.secuname) for item in client.list_securities()}

    assert ("600519.SH", "\u8d35\u5dde\u8305\u53f0") in securities
    assert ("300750.SZ", "\u5b81\u5fb7\u65f6\u4ee3") in securities
    assert ("000001.SZ", "\u5e73\u5b89\u94f6\u884c") in securities
    assert ("301511.SZ", "德福科技") in securities


def test_list_securities_returns_list_copy():
    client = MockTianyanClient()
    first_result = client.list_securities()

    first_result.clear()

    remaining_codes = {item.secucode for item in client.list_securities()}
    assert remaining_codes == {
        "600519.SH",
        "300750.SZ",
        "000001.SZ",
        "301511.SZ",
        "300502.SZ",
    }


def test_get_daily_kline_returns_ohlcv_rows_for_weekdays():
    client = MockTianyanClient()

    rows = client.get_daily_kline(
        "600519.SH",
        start=date(2026, 6, 8),
        end=date(2026, 6, 12),
    )

    assert rows
    assert {"date", "open", "close", "low", "high", "volume"} <= set(rows[0])


def test_get_daily_kline_excludes_weekend_days():
    client = MockTianyanClient()

    rows = client.get_daily_kline(
        "600519.SH",
        start=date(2026, 6, 6),
        end=date(2026, 6, 8),
    )

    assert len(rows) == 1
    assert [row["date"] for row in rows] == [date(2026, 6, 8)]


def test_get_announcements_returns_contract_related_titles_since_date():
    client = MockTianyanClient()

    announcements = client.get_announcements("600519.SH", since=date(2026, 1, 1))

    assert announcements
    assert any("重大合同" in item["title"] or "签订" in item["title"] for item in announcements)


def test_get_recent_announcements_returns_mock_rows_for_manual_sync():
    client = MockTianyanClient()

    announcements = client.get_announcements("301511.SZ", since=date.today() - timedelta(days=7))

    assert announcements
    assert announcements[0]["secucode"] == "301511.SZ"


def test_get_announcements_accepts_datetime_since():
    client = MockTianyanClient()

    announcements = client.get_announcements(
        "600519.SH",
        since=datetime(2026, 1, 1, 9, 30),
    )

    assert isinstance(announcements, list)
    assert announcements


def test_create_tianyan_client_returns_mock_client(tmp_path):
    settings = Settings(
        root_dir=tmp_path,
        data_dir=tmp_path,
        db_path=tmp_path / "tiance.db",
    )

    assert isinstance(create_tianyan_client(settings), MockTianyanClient)
