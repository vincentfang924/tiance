import pytest

from tiance.clients.mock_tianyan import MockTianyanClient
from tiance.db.migrations import migrate
from tiance.errors import AlreadyWatching, StockNotFound
from tiance.services.watchlist import WatchlistService


def make_service(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    return WatchlistService(db_path, MockTianyanClient())


def test_add_stock_by_name(tmp_path):
    service = make_service(tmp_path)
    row = service.add_stock("茅台")
    assert row.secucode == "600519.SH"
    assert row.secuname == "贵州茅台"


def test_duplicate_stock_is_rejected(tmp_path):
    service = make_service(tmp_path)
    service.add_stock("600519")
    with pytest.raises(AlreadyWatching):
        service.add_stock("贵州茅台")


def test_unknown_stock_is_rejected(tmp_path):
    service = make_service(tmp_path)
    with pytest.raises(StockNotFound):
        service.add_stock("不存在")


def test_get_stock_returns_existing_row(tmp_path):
    service = make_service(tmp_path)
    created = service.add_stock("600519")

    row = service.get_stock(created.secucode)

    assert row.secucode == "600519.SH"
    assert row.secuname == "贵州茅台"


def test_get_stock_rejects_missing_secucode(tmp_path):
    service = make_service(tmp_path)

    with pytest.raises(StockNotFound):
        service.get_stock("000000.SH")


def test_list_watchlist_returns_rows_in_sort_order(tmp_path):
    service = make_service(tmp_path)
    first = service.add_stock("600519")
    second = service.add_stock("300750")

    rows = service.list_watchlist()

    assert [row.secucode for row in rows] == [first.secucode, second.secucode]
    assert [row.sort_order for row in rows] == [1, 2]


def test_remove_stock_deletes_existing_row(tmp_path):
    service = make_service(tmp_path)
    created = service.add_stock("600519")

    service.remove_stock(created.secucode)

    with pytest.raises(StockNotFound):
        service.get_stock(created.secucode)
