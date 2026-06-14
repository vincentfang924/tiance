from fastapi.testclient import TestClient

from tiance.db.sqlite import connect
from tiance.main import create_app


def test_health_response_is_wrapped():
    with TestClient(create_app(testing=True)) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok"}}


def test_business_error_is_wrapped():
    with TestClient(create_app(testing=True)) as client:
        response = client.get("/api/watchlist/000000.SH")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "STOCK_NOT_FOUND"


def test_post_watchlist_adds_stock_by_name():
    with TestClient(create_app(testing=True)) as client:
        response = client.post("/api/watchlist", json={"query": "茅台"})

    assert response.status_code == 200
    assert response.json()["data"]["secucode"] == "600519.SH"


def test_post_watchlist_adds_defu_technology_by_name():
    with TestClient(create_app(testing=True)) as client:
        response = client.post("/api/watchlist", json={"query": "德福科技"})

    assert response.status_code == 200
    assert response.json()["data"]["secucode"] == "301511.SZ"


def test_post_watchlist_rejects_duplicate_stock():
    with TestClient(create_app(testing=True)) as client:
        client.post("/api/watchlist", json={"query": "600519"})

        response = client.post("/api/watchlist", json={"query": "贵州茅台"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ALREADY_WATCHING"


def test_get_watchlist_returns_added_items():
    with TestClient(create_app(testing=True)) as client:
        client.post("/api/watchlist", json={"query": "茅台"})

        response = client.get("/api/watchlist")

    assert response.status_code == 200
    assert [item["secucode"] for item in response.json()["data"]] == ["600519.SH"]


def test_deleted_stock_detail_returns_not_found():
    with TestClient(create_app(testing=True)) as client:
        created = client.post("/api/watchlist", json={"query": "茅台"}).json()["data"]

        delete_response = client.delete(f"/api/watchlist/{created['secucode']}")
        detail_response = client.get(f"/api/watchlist/{created['secucode']}")

    assert delete_response.status_code == 200
    assert detail_response.status_code == 404
    assert detail_response.json()["error"]["code"] == "STOCK_NOT_FOUND"


def test_testing_apps_use_clean_fixed_test_database():
    first_app = create_app(testing=True)
    with TestClient(first_app) as first_client:
        first_client.post("/api/watchlist", json={"query": "茅台"})

    second_app = create_app(testing=True)
    with TestClient(second_app) as second_client:
        response = second_client.get("/api/watchlist")

    assert first_app.state.settings.db_path.name == "tiance_test.db"
    assert second_app.state.settings.db_path.name == "tiance_test.db"
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_empty_watchlist_add_body_returns_wrapped_validation_error():
    with TestClient(create_app(testing=True)) as client:
        response = client.post("/api/watchlist", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "请求参数无效"
    assert body["error"]["details"]


def test_get_market_kline_returns_points():
    with TestClient(create_app(testing=True)) as client:
        response = client.get(
            "/api/market/600519.SH/kline",
            params={
                "start": "2026-06-01",
                "end": "2026-06-08",
                "freq": "D",
                "ma": "3",
            },
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["secucode"] == "600519.SH"
    assert data["points"]


def test_get_market_kline_returns_price_and_volume_percent_changes():
    with TestClient(create_app(testing=True)) as client:
        response = client.get(
            "/api/market/600519.SH/kline",
            params={
                "start": "2026-06-01",
                "end": "2026-06-05",
                "freq": "D",
            },
        )

    assert response.status_code == 200
    points = response.json()["data"]["points"]
    assert points[0]["pct_change"] is None
    assert points[0]["volume_change_pct"] is None
    assert points[1]["pct_change"] is not None
    assert points[1]["volume_change_pct"] == 1.0


def test_get_market_kline_accepts_forward_adjustment():
    with TestClient(create_app(testing=True)) as client:
        response = client.get(
            "/api/market/600519.SH/kline",
            params={
                "start": "2026-06-01",
                "end": "2026-06-05",
                "freq": "D",
                "adjust": "forward",
            },
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["adjust"] == "forward"
    assert data["points"][0]["adjust_ratio"] == 1


def test_get_market_kline_accepts_comma_separated_ma():
    with TestClient(create_app(testing=True)) as client:
        response = client.get(
            "/api/market/600519.SH/kline",
            params={
                "start": "2026-06-01",
                "end": "2026-06-08",
                "freq": "D",
                "ma": "3,5",
            },
        )

    assert response.status_code == 200
    point = response.json()["data"]["points"][-1]
    assert "ma3" in point["ma"]
    assert "ma5" in point["ma"]


def test_get_market_kline_rejects_invalid_freq():
    with TestClient(create_app(testing=True)) as client:
        response = client.get(
            "/api/market/600519.SH/kline",
            params={
                "start": "2026-06-01",
                "end": "2026-06-08",
                "freq": "X",
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_FREQ"


def test_get_market_kline_rejects_invalid_adjust_mode():
    with TestClient(create_app(testing=True)) as client:
        response = client.get(
            "/api/market/600519.SH/kline",
            params={
                "start": "2026-06-01",
                "end": "2026-06-08",
                "adjust": "backward",
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ADJUST_MODE"


def test_blank_watchlist_query_returns_wrapped_validation_error():
    with TestClient(create_app(testing=True)) as client:
        response = client.post("/api/watchlist", json={"query": ""})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "请求参数无效"
    assert body["error"]["details"]
def test_get_admin_data_sources_returns_sources():
    with TestClient(create_app(testing=True)) as client:
        response = client.get("/api/admin/data-sources")

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["data"]]
    assert "公告" in names


def test_get_admin_db_tables_includes_watchlist():
    with TestClient(create_app(testing=True)) as client:
        response = client.get("/api/admin/db/tables")

    assert response.status_code == 200
    assert "watchlist" in response.json()["data"]


def test_get_announcements_returns_fetched_rows():
    app = create_app(testing=True)
    with TestClient(app) as client:
        client.post("/api/watchlist", json={"query": "600519"})
        app.state.announcement_service.fetch_for("600519.SH", since="2026-01-01")

        response = client.get("/api/announcements/600519.SH")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data
    assert data[0]["secucode"] == "600519.SH"
    assert data[0]["summary"]


def test_get_announcements_generates_summary_for_legacy_rows_without_summary():
    app = create_app(testing=True)
    with TestClient(app) as client:
        client.post("/api/watchlist", json={"query": "600519"})
        app.state.announcement_service.fetch_for("600519.SH", since="2026-01-01")

        with connect(app.state.settings.db_path) as conn:
            conn.execute("UPDATE announcements SET summary = NULL WHERE secucode = ?", ("600519.SH",))
            conn.commit()

        response = client.get("/api/announcements/600519.SH", params={"days": 365})

    assert response.status_code == 200
    assert response.json()["data"][0]["summary"]


def test_get_announcements_filters_by_recent_days():
    app = create_app(testing=True)
    with TestClient(app) as client:
        client.post("/api/watchlist", json={"query": "600519"})
        app.state.announcement_service.fetch_for("600519.SH", since="2026-01-01")

        recent_response = client.get("/api/announcements/600519.SH", params={"days": 30})
        year_response = client.get("/api/announcements/600519.SH", params={"days": 365})

    assert recent_response.status_code == 200
    assert year_response.status_code == 200
    assert len(recent_response.json()["data"]) == 1
    assert len(year_response.json()["data"]) == 2


def test_get_announcement_detail_returns_summary_and_raw_payload():
    app = create_app(testing=True)
    with TestClient(app) as client:
        client.post("/api/watchlist", json={"query": "600519"})
        app.state.announcement_service.fetch_for("600519.SH", since="2026-01-01")
        rows = client.get("/api/announcements/600519.SH", params={"days": 365}).json()["data"]

        response = client.get(f"/api/announcements/600519.SH/{rows[0]['ann_id']}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["ann_id"] == rows[0]["ann_id"]
    assert data["summary"]
    assert "raw_payload" in data


def test_refresh_announcements_for_selected_stock_inserts_rows():
    with TestClient(create_app(testing=True)) as client:
        created = client.post("/api/watchlist", json={"query": "德福科技"}).json()["data"]

        refresh_response = client.post(f"/api/announcements/{created['secucode']}/refresh")
        list_response = client.get(f"/api/announcements/{created['secucode']}")

    assert refresh_response.status_code == 200
    assert refresh_response.json()["data"]["inserted"] >= 1
    rows = list_response.json()["data"]
    assert rows
    assert rows[0]["secucode"] == "301511.SZ"
def test_get_admin_db_table_rows_returns_watchlist_rows():
    with TestClient(create_app(testing=True)) as client:
        client.post("/api/watchlist", json={"query": "600519"})

        response = client.get("/api/admin/db/tables/watchlist/rows")

    assert response.status_code == 200
    rows = response.json()["data"]
    assert any(row["secucode"] == "600519.SH" for row in rows)


def test_get_announcements_filters_business_bucket_and_limit():
    app = create_app(testing=True)
    with TestClient(app) as client:
        client.post("/api/watchlist", json={"query": "600519"})
        app.state.announcement_service.fetch_for("600519.SH", since="2026-01-01")

        response = client.get(
            "/api/announcements/600519.SH",
            params={"bucket": "business", "days": 365, "limit": 1},
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["category_bucket"] == "business"


def test_refresh_api_accepts_manual_refresh_in_testing():
    with TestClient(create_app(testing=True)) as client:
        response = client.post("/api/admin/refresh/fetch_announcements")

    assert response.status_code == 202
    payload = response.json()["data"]
    assert payload["accepted"] is True
    assert payload["run_at"]
    assert "测试模式" in payload["message"]


def test_announcements_limit_rejects_out_of_range_values():
    with TestClient(create_app(testing=True)) as client:
        response = client.get("/api/announcements/600519.SH", params={"limit": -1})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_admin_db_table_rows_rejects_quoted_table_name():
    with TestClient(create_app(testing=True)) as client:
        response = client.get('/api/admin/db/tables/watchlist" WHERE 1=1 --/rows')

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_non_testing_app_starts_scheduler(monkeypatch):
    events = []

    class FakeScheduler:
        running = False

        def start(self):
            events.append("start")
            self.running = True

        def shutdown(self, wait=False):
            events.append(("shutdown", wait))
            self.running = False

    def fake_create_scheduler():
        events.append("create")
        return FakeScheduler()

    def fake_register_jobs(app):
        events.append(("register", app.state.scheduler))

    monkeypatch.setattr("tiance.main.create_scheduler", fake_create_scheduler)
    monkeypatch.setattr("tiance.main.register_jobs", fake_register_jobs)

    app = create_app(testing=False)
    with TestClient(app):
        assert app.state.admin_service.scheduler is app.state.scheduler
        assert app.state.scheduler.running is True

    assert events == ["create", ("register", app.state.scheduler), "start", ("shutdown", False)]


def test_web_root_serves_browser_workspace():
    with TestClient(create_app(testing=True)) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "天策" in response.text
    assert 'id="watchlist"' in response.text
    assert 'id="chart"' in response.text
    assert 'id="adjust-forward"' in response.text
    assert 'id="sync-announcements"' in response.text
    assert 'id="announcement-range"' in response.text
    assert 'id="announcement-detail"' in response.text


def test_web_assets_are_served():
    with TestClient(create_app(testing=True)) as client:
        css_response = client.get("/styles.css")
        js_response = client.get("/app.js")

    assert css_response.status_code == 200
    assert "grid-template-columns" in css_response.text
    assert js_response.status_code == 200
    assert "loadWatchlist" in js_response.text
    assert "removeStock" in js_response.text
    assert "axisPointer" in js_response.text
    assert "link" in js_response.text
