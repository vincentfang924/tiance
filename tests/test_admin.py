from datetime import date, datetime, timezone

import pytest

from tiance.db.migrations import migrate
from tiance.db.sqlite import connect
from tiance.errors import TaskRunning
from tiance.scheduler.runtime import run_tracked
from tiance.services.admin import AdminService
from tiance.services.announcement import AnnouncementService, classify_announcement
from tiance.services.watchlist import WatchlistService


class AnnouncementClient:
    def __init__(self) -> None:
        self.calls = []

    def search_security(self, query: str):
        return type("Security", (), {"secucode": "600519.SH", "secuname": "贵州茅台"})()

    def get_announcements(self, secucode: str, since: date):
        self.calls.append((secucode, since))
        return [
            {
                "ann_id": "ann-600519-001",
                "secucode": secucode,
                "title": "关于签订重大合同的公告",
                "category_l1_label": "临时公告",
                "publish_at": "2026-06-08T09:30:00+00:00",
                "url": "mock://announcements/600519/001",
            },
            {
                "ann_id": "ann-600519-002",
                "secucode": secucode,
                "title": "龙虎榜交易公开信息",
                "category_l1_label": "交易信息",
                "publish_at": "2026-06-08T10:00:00+00:00",
                "url": "mock://announcements/600519/002",
            },
        ]


class SharedAnnouncementIdClient:
    def get_announcements(self, secucode: str, since: date):
        return [
            {
                "ann_id": "shared-ann-id",
                "secucode": secucode,
                "title": "关于签订重大合同的公告",
                "publish_at": "2026-06-08T09:30:00+00:00",
            }
        ]


def test_data_sources_include_source_tables(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)

    rows = AdminService(db_path, scheduler=None).list_data_sources()

    announcement = next(item for item in rows if item["name"] == "公告")
    assert "jydb.lc_announcementinfo" in announcement["source_tables"]


def test_data_sources_use_real_chinese_and_section_name(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)

    rows = AdminService(db_path, scheduler=None).list_data_sources()
    by_task = {item["task_name"]: item for item in rows if item["task_name"]}

    assert by_task["fetch_announcements"]["name"] == "公告"
    assert by_task["fetch_announcements"]["section_name"] == "公告"
    assert by_task["fetch_rank_list"]["section_name"] == "龙虎榜"
    assert by_task["fetch_rank_list"]["schedule_desc"] == "每交易日 16:30"
    assert by_task["fetch_money_flow"]["schedule_desc"] == "每交易日 16:30"


def test_recent_task_status_is_attached(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO task_runs(task_name, started_at, finished_at, status, rows_affected, error)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "fetch_announcements",
                datetime(2026, 6, 8, tzinfo=timezone.utc).isoformat(),
                datetime(2026, 6, 8, 0, 1, tzinfo=timezone.utc).isoformat(),
                "success",
                3,
                None,
            ),
        )
        conn.commit()

    rows = AdminService(db_path, scheduler=None).list_data_sources()

    announcement = next(item for item in rows if item["task_name"] == "fetch_announcements")
    assert announcement["last_status"] == "success"
    assert announcement["last_rows_affected"] == 3


def test_classify_announcement_business_and_capital_flow():
    assert classify_announcement("关于签订重大合同的公告") == "business"
    assert classify_announcement("龙虎榜交易公开信息") == "capital_flow"


def test_fetch_all_watchlist_inserts_mock_announcements_once(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    client = AnnouncementClient()
    WatchlistService(db_path, client).add_stock("600519")
    service = AnnouncementService(db_path, client)

    inserted = service.fetch_all_watchlist(since=date(2026, 6, 1))
    inserted_again = service.fetch_all_watchlist(since=date(2026, 6, 1))

    assert inserted == 2
    assert inserted_again == 0


def test_fetch_for_allows_same_upstream_announcement_id_across_stocks(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    service = AnnouncementService(db_path, SharedAnnouncementIdClient())

    first = service.fetch_for("600519.SH", since=date(2026, 6, 1))
    second = service.fetch_for("300750.SZ", since=date(2026, 6, 1))

    with connect(db_path) as conn:
        rows = conn.execute("SELECT secucode FROM announcements ORDER BY secucode").fetchall()

    assert first == 1
    assert second == 1
    assert [row["secucode"] for row in rows] == ["300750.SZ", "600519.SH"]


def test_list_for_stock_filters_business_bucket(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    client = AnnouncementClient()
    WatchlistService(db_path, client).add_stock("600519")
    service = AnnouncementService(db_path, client)
    service.fetch_all_watchlist(since=date(2026, 6, 1))

    rows = service.list_for_stock("600519.SH", bucket="business")

    assert [row["title"] for row in rows] == ["关于签订重大合同的公告"]
    assert rows[0]["category_bucket"] == "business"


def test_list_for_stock_clamps_invalid_limit(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    client = AnnouncementClient()
    WatchlistService(db_path, client).add_stock("600519")
    service = AnnouncementService(db_path, client)
    service.fetch_all_watchlist(since=date(2026, 6, 1))

    rows = service.list_for_stock("600519.SH", limit=-1)

    assert len(rows) == 1


def test_data_sources_match_phase0_source_tables_and_task_names(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)

    rows = AdminService(db_path, scheduler=None).list_data_sources()
    by_tables = {tuple(item["source_tables"]): item for item in rows}

    assert ("jydb.lc_announcementinfo",) in by_tables
    assert by_tables[("jydb.lc_announcementinfo",)]["task_name"] == "fetch_announcements"
    assert ("jydb.lc_7percentchange", "jydb.lc_stiboptradinfo") in by_tables
    assert by_tables[("jydb.lc_7percentchange", "jydb.lc_stiboptradinfo")]["task_name"] == "fetch_rank_list"
    assert ("wind_admin.ASHAREMONEYFLOW",) in by_tables
    assert by_tables[("wind_admin.ASHAREMONEYFLOW",)]["task_name"] == "fetch_money_flow"
    assert ("wind_admin.ASHAREEODPRICES",) in by_tables
    assert by_tables[("wind_admin.ASHAREEODPRICES",)]["task_name"] is None
    assert ("jydb.lc_coconcept", "jydb.lc_conceptlist") in by_tables
    assert ("jydb.secumain",) in by_tables
    assert by_tables[("jydb.secumain",)]["task_name"] == "reload_securities"


def test_trigger_refresh_rejects_running_task(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    service = AdminService(db_path, scheduler=None)
    service.running_tasks.add("fetch_announcements")

    with pytest.raises(TaskRunning):
        service.trigger_refresh("fetch_announcements")


def test_trigger_refresh_reserves_queued_manual_task(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    scheduled_jobs = []

    class FakeScheduler:
        def add_job(self, func, **kwargs):
            scheduled_jobs.append((func, kwargs))

    service = AdminService(db_path, scheduler=FakeScheduler())

    first = service.trigger_refresh("fetch_announcements")

    assert first["accepted"] is True
    assert scheduled_jobs
    with pytest.raises(TaskRunning):
        service.trigger_refresh("fetch_announcements")


def test_running_scheduled_task_blocks_manual_refresh(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    service = AdminService(db_path, scheduler=None)

    def work():
        with pytest.raises(TaskRunning):
            service.trigger_refresh("fetch_announcements")
        return 1

    assert service.run_task("fetch_announcements", work) == 1


def test_trigger_refresh_accepts_refreshable_task_in_testing(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    service = AdminService(db_path, scheduler=None)

    result = service.trigger_refresh("fetch_announcements")

    assert result["accepted"] is True
    assert result["run_at"]
    assert "测试模式" in result["message"]


def test_trigger_refresh_rejects_non_refreshable_task(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    service = AdminService(db_path, scheduler=None)

    result = service.trigger_refresh("not_a_task")

    assert result["accepted"] is False
    assert "不可刷新" in result["message"]


def test_get_table_rows_rejects_unknown_or_quoted_table_names(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    service = AdminService(db_path, scheduler=None)

    assert service.get_table_rows("missing_table") == []
    assert service.get_table_rows('watchlist" WHERE 1=1 --') == []


def test_run_tracked_records_success(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)

    rows = run_tracked(db_path, "fetch_announcements", lambda: 7)

    with connect(db_path) as conn:
        run = conn.execute("SELECT * FROM task_runs WHERE task_name = ?", ("fetch_announcements",)).fetchone()

    assert rows == 7
    assert run["status"] == "success"
    assert run["rows_affected"] == 7
    assert run["finished_at"] is not None
    assert run["error"] is None


def test_run_tracked_records_failure_and_reraises(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)

    def fail():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        run_tracked(db_path, "fetch_announcements", fail)

    with connect(db_path) as conn:
        run = conn.execute("SELECT * FROM task_runs WHERE task_name = ?", ("fetch_announcements",)).fetchone()

    assert run["status"] == "failed"
    assert run["finished_at"] is not None
    assert run["error"] == "boom"


def test_run_tracked_marks_non_numeric_rows_as_failed(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)

    with pytest.raises(TypeError):
        run_tracked(db_path, "fetch_announcements", lambda: ["not-bindable"])

    with connect(db_path) as conn:
        run = conn.execute("SELECT * FROM task_runs WHERE task_name = ?", ("fetch_announcements",)).fetchone()

    assert run["status"] == "failed"
    assert run["finished_at"] is not None
    assert "rows_affected" in run["error"]


def test_run_tracked_normalizes_none_rows_to_zero(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)

    rows = run_tracked(db_path, "fetch_announcements", lambda: None)

    with connect(db_path) as conn:
        run = conn.execute("SELECT * FROM task_runs WHERE task_name = ?", ("fetch_announcements",)).fetchone()

    assert rows == 0
    assert run["status"] == "success"
    assert run["rows_affected"] == 0
