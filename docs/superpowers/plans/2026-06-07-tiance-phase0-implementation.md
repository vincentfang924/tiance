# Tiance Phase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 0 local A-share watchlist, K-line, announcement, scheduler, SQLite, admin, and raw-data inspection system described in `docs/superpowers/specs/2026-06-07-tiance-phase0-design.md`.

**Architecture:** A single local FastAPI app serves both JSON APIs and static browser UI. Business logic lives in focused service modules, persistence uses SQLite through repository helpers, and Tianyan access is isolated behind a client interface with a mock fallback for development.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Pydantic, APScheduler, pandas, pytest, SQLite, plain HTML/CSS/JavaScript, ECharts CDN.

---

## File Structure

Create this structure under the workspace root:

```text
tiance/
  __init__.py
  main.py
  config.py
  errors.py
  models.py
  api/
    __init__.py
    admin.py
    announcements.py
    market.py
    watchlist.py
  clients/
    __init__.py
    mock_tianyan.py
    tianyan.py
  db/
    __init__.py
    migrations.py
    sqlite.py
  scheduler/
    __init__.py
    jobs.py
    runtime.py
  services/
    __init__.py
    admin.py
    announcement.py
    concepts.py
    indicators.py
    market.py
    moneyflow.py
    watchlist.py
  web/
    index.html
    app.js
    styles.css
tests/
  conftest.py
  test_admin.py
  test_api.py
  test_db.py
  test_indicators.py
  test_watchlist.py
data/
  .gitkeep
requirements.txt
run_tiance.ps1
```

Responsibility map:

- `tiance/main.py`: FastAPI app factory, static file mounting, lifecycle startup/shutdown.
- `tiance/config.py`: paths and runtime mode.
- `tiance/errors.py`: domain exceptions and FastAPI handlers.
- `tiance/models.py`: Pydantic DTOs shared by API and services.
- `tiance/db/*`: SQLite connection and schema migrations.
- `tiance/clients/*`: Tianyan abstraction and mock data.
- `tiance/services/*`: watchlist, market, announcement, moneyflow, concepts, admin logic.
- `tiance/api/*`: thin HTTP routes that call services.
- `tiance/scheduler/*`: APScheduler jobs, task-run tracking, manual refresh.
- `tiance/web/*`: first usable browser UI.

## Task 1: Project Skeleton And Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `run_tiance.ps1`
- Create: package directories and `__init__.py` files
- Create: `data/.gitkeep`

- [ ] **Step 1: Create dependencies file**

Create `requirements.txt`:

```text
fastapi==0.115.12
uvicorn[standard]==0.34.3
pydantic==2.11.5
apscheduler==3.11.0
pandas==2.2.3
pytest==8.4.0
httpx==0.28.1
```

- [ ] **Step 2: Create package skeleton**

Create every directory listed in File Structure and add empty `__init__.py` files in Python packages.

- [ ] **Step 3: Add local runner**

Create `run_tiance.ps1`:

```powershell
$ErrorActionPreference = "Stop"
python -m uvicorn tiance.main:create_app --factory --host 127.0.0.1 --port 8000
```

- [ ] **Step 4: Install dependencies**

Run:

```powershell
python -m pip install -r requirements.txt
```

Expected: packages install successfully.

- [ ] **Step 5: Commit**

Skip commit if this workspace is not a git repository. If it is a git repository, run:

```powershell
git add requirements.txt run_tiance.ps1 tiance tests data
git commit -m "chore: scaffold tiance phase0 app"
```

## Task 2: Config, Errors, Models, And API Response Shape

**Files:**
- Create: `tiance/config.py`
- Create: `tiance/errors.py`
- Create: `tiance/models.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write failing tests for error response format**

Create `tests/test_api.py`:

```python
from fastapi.testclient import TestClient

from tiance.main import create_app


def test_health_response_is_wrapped():
    client = TestClient(create_app(testing=True))
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok"}}


def test_business_error_is_wrapped():
    client = TestClient(create_app(testing=True))
    response = client.get("/api/watchlist/000000.SH")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "STOCK_NOT_FOUND"
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
pytest tests/test_api.py -v
```

Expected: fails because `tiance.main` and routes do not exist yet.

- [ ] **Step 3: Implement shared config**

Create `tiance/config.py`:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    data_dir: Path
    db_path: Path
    use_mock_tianyan: bool = True


def default_settings(testing: bool = False) -> Settings:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / ("work" if testing else "data")
    data_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        root_dir=root,
        data_dir=data_dir,
        db_path=data_dir / ("tiance_test.db" if testing else "tiance.db"),
        use_mock_tianyan=True,
    )
```

- [ ] **Step 4: Implement domain errors**

Create `tiance/errors.py`:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class TianceError(Exception):
    status_code = 400
    code = "TIANCE_ERROR"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class StockNotFound(TianceError):
    status_code = 404
    code = "STOCK_NOT_FOUND"


class AlreadyWatching(TianceError):
    status_code = 409
    code = "ALREADY_WATCHING"


class TaskRunning(TianceError):
    status_code = 409
    code = "TASK_RUNNING"


class TianyanUnavailable(TianceError):
    status_code = 503
    code = "TIANYAN_UNAVAILABLE"


class InvalidFreq(TianceError):
    status_code = 400
    code = "INVALID_FREQ"


def data_response(data):
    return {"data": data}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(TianceError)
    async def handle_tiance_error(_: Request, exc: TianceError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
```

- [ ] **Step 5: Implement shared DTOs**

Create `tiance/models.py` with DTOs used by early APIs:

```python
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
    ma: dict[str, float | None] = {}
    macd: dict[str, float | None] = {}


class KlineData(BaseModel):
    secucode: str
    freq: Freq
    points: list[KlinePoint]
```

- [ ] **Step 6: Implement app factory and minimal routes**

Create `tiance/main.py`:

```python
from fastapi import FastAPI

from tiance.config import default_settings
from tiance.errors import StockNotFound, data_response, install_error_handlers


def create_app(testing: bool = False) -> FastAPI:
    app = FastAPI(title="Tiance", version="0.1.0")
    app.state.settings = default_settings(testing=testing)
    install_error_handlers(app)

    @app.get("/api/health")
    def health():
        return data_response({"status": "ok"})

    @app.get("/api/watchlist/{secucode}")
    def placeholder_stock_detail(secucode: str):
        raise StockNotFound(f"未找到股票 {secucode}")

    return app
```

- [ ] **Step 7: Run tests**

Run:

```powershell
pytest tests/test_api.py -v
```

Expected: both tests pass.

## Task 3: SQLite Migration And Repository Helpers

**Files:**
- Create: `tiance/db/sqlite.py`
- Create: `tiance/db/migrations.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write migration tests**

Create `tests/test_db.py`:

```python
import sqlite3

from tiance.db.migrations import migrate


def test_migration_is_idempotent(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    migrate(db_path)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()

    table_names = {row[0] for row in rows}
    assert "watchlist" in table_names
    assert "announcements" in table_names
    assert "task_runs" in table_names


def test_raw_payload_columns_exist(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    with sqlite3.connect(db_path) as conn:
        announcement_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(announcements)")
        }
        money_cols = {row[1] for row in conn.execute("PRAGMA table_info(money_flows)")}
    assert "raw_payload" in announcement_cols
    assert "raw_payload" in money_cols
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
pytest tests/test_db.py -v
```

Expected: fails because migration modules do not exist.

- [ ] **Step 3: Implement SQLite connection helper**

Create `tiance/db/sqlite.py`:

```python
import sqlite3
from pathlib import Path


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def rows_to_dicts(rows) -> list[dict]:
    return [dict(row) for row in rows]
```

- [ ] **Step 4: Implement migrations**

Create `tiance/db/migrations.py` with the schema from the spec:

```python
from pathlib import Path

from tiance.db.sqlite import connect


SCHEMA = """
CREATE TABLE IF NOT EXISTS groups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist (
  secucode TEXT PRIMARY KEY,
  secuname TEXT NOT NULL,
  group_id INTEGER REFERENCES groups(id),
  note TEXT,
  sort_order INTEGER NOT NULL DEFAULT 0,
  added_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS concepts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  source TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_concepts (
  secucode TEXT NOT NULL REFERENCES watchlist(secucode) ON DELETE CASCADE,
  concept_id INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
  added_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY(secucode, concept_id)
);

CREATE TABLE IF NOT EXISTS announcements (
  ann_id TEXT PRIMARY KEY,
  secucode TEXT NOT NULL,
  title TEXT NOT NULL,
  ann_type TEXT,
  category_l1 TEXT,
  category_l1_label TEXT,
  category_bucket TEXT NOT NULL,
  is_keyword_hit INTEGER NOT NULL DEFAULT 0,
  publish_at TEXT NOT NULL,
  source TEXT NOT NULL,
  url TEXT,
  local_path TEXT,
  raw_payload TEXT,
  is_read INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS money_flows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  secucode TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  main_net_inflow REAL,
  main_net_inflow_pct REAL,
  raw_payload TEXT,
  UNIQUE(secucode, trade_date)
);

CREATE TABLE IF NOT EXISTS rank_list_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  secucode TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  reason TEXT,
  amount REAL,
  raw_payload TEXT,
  UNIQUE(secucode, trade_date, reason)
);

CREATE TABLE IF NOT EXISTS task_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_name TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  rows_affected INTEGER,
  error TEXT
);

CREATE INDEX IF NOT EXISTS idx_announcements_secucode_publish
  ON announcements(secucode, publish_at DESC);
CREATE INDEX IF NOT EXISTS idx_task_runs_task_started
  ON task_runs(task_name, started_at DESC);
"""


def migrate(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
```

- [ ] **Step 5: Run migration tests**

Run:

```powershell
pytest tests/test_db.py -v
```

Expected: both tests pass.

## Task 4: Mock Tianyan Client

**Files:**
- Create: `tiance/clients/mock_tianyan.py`
- Create: `tiance/clients/tianyan.py`

- [ ] **Step 1: Implement client interface and mock data**

Create `tiance/clients/mock_tianyan.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class Security:
    secucode: str
    secuname: str


class MockTianyanClient:
    def __init__(self):
        self.securities = [
            Security("600519.SH", "贵州茅台"),
            Security("300750.SZ", "宁德时代"),
            Security("000001.SZ", "平安银行"),
        ]

    def search_security(self, query: str) -> Security | None:
        normalized = query.strip().upper()
        for security in self.securities:
            if normalized in {
                security.secucode,
                security.secucode[:6],
                security.secuname.upper(),
            }:
                return security
        for security in self.securities:
            if query.strip() and query.strip() in security.secuname:
                return security
        return None

    def list_securities(self) -> list[Security]:
        return list(self.securities)

    def get_daily_kline(self, secucode: str, start: date, end: date) -> list[dict]:
        points = []
        cursor = start
        base = 100.0 + len(secucode)
        i = 0
        while cursor <= end:
            if cursor.weekday() < 5:
                open_price = base + i * 0.3
                close_price = open_price + ((i % 5) - 2) * 0.4
                points.append(
                    {
                        "date": cursor,
                        "open": round(open_price, 2),
                        "close": round(close_price, 2),
                        "low": round(min(open_price, close_price) - 0.8, 2),
                        "high": round(max(open_price, close_price) + 0.8, 2),
                        "volume": 1000000 + i * 10000,
                    }
                )
                i += 1
            cursor += timedelta(days=1)
        return points

    def get_announcements(self, secucode: str, since: datetime) -> list[dict]:
        now = datetime.now()
        rows = [
            {
                "ann_id": f"{secucode}-demo-1",
                "secucode": secucode,
                "title": "关于签订重大合同的公告",
                "ann_type": "重大事项",
                "category_l1": "business",
                "category_l1_label": "重大事项",
                "publish_at": now.isoformat(timespec="seconds"),
                "source": "mock",
                "url": "",
            }
        ]
        return [row for row in rows if datetime.fromisoformat(row["publish_at"]) >= since]
```

Create `tiance/clients/tianyan.py`:

```python
from tiance.clients.mock_tianyan import MockTianyanClient
from tiance.config import Settings


def create_tianyan_client(settings: Settings):
    return MockTianyanClient()
```

- [ ] **Step 2: Manual smoke check**

Run:

```powershell
python -c "from tiance.clients.mock_tianyan import MockTianyanClient; c=MockTianyanClient(); print(c.search_security('茅台').secucode)"
```

Expected: `600519.SH`.

## Task 5: Watchlist Service And Routes

**Files:**
- Create: `tiance/services/watchlist.py`
- Create: `tiance/api/watchlist.py`
- Modify: `tiance/main.py`
- Create: `tests/test_watchlist.py`

- [ ] **Step 1: Write failing watchlist service tests**

Create `tests/test_watchlist.py`:

```python
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
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
pytest tests/test_watchlist.py -v
```

Expected: fails because `WatchlistService` does not exist.

- [ ] **Step 3: Implement watchlist service**

Create `tiance/services/watchlist.py`:

```python
from datetime import datetime
from pathlib import Path

from tiance.db.sqlite import connect, rows_to_dicts
from tiance.errors import AlreadyWatching, StockNotFound
from tiance.models import WatchlistRow


class WatchlistService:
    def __init__(self, db_path: Path, tianyan_client):
        self.db_path = db_path
        self.tianyan_client = tianyan_client

    def add_stock(self, query: str, group_id: int | None = None) -> WatchlistRow:
        security = self.tianyan_client.search_security(query)
        if security is None:
            raise StockNotFound(f"未找到股票 {query}")
        now = datetime.now().isoformat(timespec="seconds")
        with connect(self.db_path) as conn:
            exists = conn.execute(
                "SELECT 1 FROM watchlist WHERE secucode = ?",
                (security.secucode,),
            ).fetchone()
            if exists:
                raise AlreadyWatching(f"{security.secuname} 已在关注列表")
            max_order = conn.execute(
                "SELECT COALESCE(MAX(sort_order), 0) FROM watchlist"
            ).fetchone()[0]
            conn.execute(
                """
                INSERT INTO watchlist(secucode, secuname, group_id, note, sort_order, added_at)
                VALUES (?, ?, ?, NULL, ?, ?)
                """,
                (security.secucode, security.secuname, group_id, max_order + 1, now),
            )
            conn.commit()
        return self.get_stock(security.secucode)

    def get_stock(self, secucode: str) -> WatchlistRow:
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM watchlist WHERE secucode = ?",
                (secucode,),
            ).fetchone()
        if row is None:
            raise StockNotFound(f"未找到股票 {secucode}")
        return WatchlistRow(**dict(row), unread_count=0, range_pct=None)

    def list_watchlist(self) -> list[WatchlistRow]:
        with connect(self.db_path) as conn:
            rows = rows_to_dicts(
                conn.execute("SELECT * FROM watchlist ORDER BY sort_order, added_at")
            )
        return [WatchlistRow(**row, unread_count=0, range_pct=None) for row in rows]

    def remove_stock(self, secucode: str) -> None:
        with connect(self.db_path) as conn:
            result = conn.execute("DELETE FROM watchlist WHERE secucode = ?", (secucode,))
            conn.commit()
        if result.rowcount == 0:
            raise StockNotFound(f"未找到股票 {secucode}")
```

- [ ] **Step 4: Run service tests**

Run:

```powershell
pytest tests/test_watchlist.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Add watchlist API routes**

Create `tiance/api/watchlist.py`:

```python
from fastapi import APIRouter, Request

from tiance.errors import data_response
from tiance.models import AddStockRequest

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("")
def list_watchlist(request: Request):
    service = request.app.state.watchlist_service
    return data_response([row.model_dump(mode="json") for row in service.list_watchlist()])


@router.post("")
def add_stock(payload: AddStockRequest, request: Request):
    service = request.app.state.watchlist_service
    row = service.add_stock(payload.query, payload.group_id)
    return data_response(row.model_dump(mode="json"))


@router.get("/{secucode}")
def get_stock(secucode: str, request: Request):
    service = request.app.state.watchlist_service
    return data_response(service.get_stock(secucode).model_dump(mode="json"))


@router.delete("/{secucode}")
def remove_stock(secucode: str, request: Request):
    service = request.app.state.watchlist_service
    service.remove_stock(secucode)
    return data_response({"removed": secucode})
```

- [ ] **Step 6: Wire app startup**

Modify `tiance/main.py` to migrate the database, create services, and include routes:

```python
from fastapi import FastAPI

from tiance.api import watchlist
from tiance.clients.tianyan import create_tianyan_client
from tiance.config import default_settings
from tiance.db.migrations import migrate
from tiance.errors import data_response, install_error_handlers
from tiance.services.watchlist import WatchlistService


def create_app(testing: bool = False) -> FastAPI:
    app = FastAPI(title="Tiance", version="0.1.0")
    app.state.settings = default_settings(testing=testing)
    migrate(app.state.settings.db_path)
    app.state.tianyan_client = create_tianyan_client(app.state.settings)
    app.state.watchlist_service = WatchlistService(
        app.state.settings.db_path,
        app.state.tianyan_client,
    )
    install_error_handlers(app)

    @app.get("/api/health")
    def health():
        return data_response({"status": "ok"})

    app.include_router(watchlist.router)
    return app
```

- [ ] **Step 7: Run API tests**

Run:

```powershell
pytest tests/test_api.py tests/test_watchlist.py -v
```

Expected: tests pass, and `test_business_error_is_wrapped` receives `STOCK_NOT_FOUND` from the real watchlist route.

## Task 6: Indicators And Market Service

**Files:**
- Create: `tiance/services/indicators.py`
- Create: `tiance/services/market.py`
- Create: `tiance/api/market.py`
- Modify: `tiance/main.py`
- Create: `tests/test_indicators.py`

- [ ] **Step 1: Write indicator tests**

Create `tests/test_indicators.py`:

```python
import pandas as pd

from tiance.services.indicators import add_macd, add_ma, resample_ohlcv


def test_add_ma_adds_expected_column():
    df = pd.DataFrame({"close": [1, 2, 3, 4, 5]})
    result = add_ma(df, [3])
    assert result["ma3"].tolist() == [None, None, 2.0, 3.0, 4.0]


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
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
pytest tests/test_indicators.py -v
```

Expected: fails because indicator module does not exist.

- [ ] **Step 3: Implement indicators**

Create `tiance/services/indicators.py`:

```python
import pandas as pd


def _nullable_float(value):
    if pd.isna(value):
        return None
    return round(float(value), 6)


def add_ma(df: pd.DataFrame, periods: list[int]) -> pd.DataFrame:
    result = df.copy()
    for period in periods:
        result[f"ma{period}"] = (
            result["close"].rolling(period).mean().map(_nullable_float)
        )
    return result


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    result = df.copy()
    ema_fast = result["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = result["close"].ewm(span=slow, adjust=False).mean()
    result["dif"] = ema_fast - ema_slow
    result["dea"] = result["dif"].ewm(span=signal, adjust=False).mean()
    result["macd"] = (result["dif"] - result["dea"]) * 2
    for column in ["dif", "dea", "macd"]:
        result[column] = result[column].map(_nullable_float)
    return result


def resample_ohlcv(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    if freq == "D":
        return df.copy()
    rule = {"W": "W-FRI", "M": "ME"}[freq]
    indexed = df.copy()
    indexed["date"] = pd.to_datetime(indexed["date"])
    indexed = indexed.set_index("date")
    result = (
        indexed.resample(rule)
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
        .reset_index()
    )
    return result
```

- [ ] **Step 4: Run indicator tests**

Run:

```powershell
pytest tests/test_indicators.py -v
```

Expected: tests pass.

- [ ] **Step 5: Implement market service and route**

Create `tiance/services/market.py`:

```python
from datetime import date, timedelta

import pandas as pd

from tiance.errors import InvalidFreq
from tiance.models import KlineData, KlinePoint
from tiance.services.indicators import add_ma, add_macd, resample_ohlcv


class MarketService:
    def __init__(self, tianyan_client):
        self.tianyan_client = tianyan_client

    def get_kline(
        self,
        secucode: str,
        start: date | None = None,
        end: date | None = None,
        freq: str = "D",
        ma: list[int] | None = None,
    ) -> KlineData:
        if freq not in {"D", "W", "M"}:
            raise InvalidFreq(f"不支持的周期 {freq}")
        end = end or date.today()
        start = start or (end - timedelta(days=365))
        ma = ma or [5, 10, 20, 60]
        raw = self.tianyan_client.get_daily_kline(secucode, start, end)
        df = pd.DataFrame(raw)
        if df.empty:
            return KlineData(secucode=secucode, freq=freq, points=[])
        df = resample_ohlcv(df, freq)
        df = add_ma(df, ma)
        df = add_macd(df)
        points = []
        for row in df.to_dict(orient="records"):
            ma_values = {f"ma{period}": row.get(f"ma{period}") for period in ma}
            macd_values = {key: row.get(key) for key in ["dif", "dea", "macd"]}
            points.append(
                KlinePoint(
                    date=row["date"].date() if hasattr(row["date"], "date") else row["date"],
                    open=row["open"],
                    close=row["close"],
                    low=row["low"],
                    high=row["high"],
                    volume=row["volume"],
                    ma=ma_values,
                    macd=macd_values,
                )
            )
        return KlineData(secucode=secucode, freq=freq, points=points)
```

Create `tiance/api/market.py`:

```python
from datetime import date

from fastapi import APIRouter, Query, Request

from tiance.errors import data_response

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/{secucode}/kline")
def get_kline(
    secucode: str,
    request: Request,
    start: date | None = None,
    end: date | None = None,
    freq: str = "D",
    ma: str = Query("5,10,20,60"),
):
    periods = [int(item) for item in ma.split(",") if item.strip()]
    service = request.app.state.market_service
    result = service.get_kline(secucode, start=start, end=end, freq=freq, ma=periods)
    return data_response(result.model_dump(mode="json"))
```

- [ ] **Step 6: Wire market service**

Modify `tiance/main.py` to create `MarketService` and include `market.router`.

- [ ] **Step 7: Run tests**

Run:

```powershell
pytest tests/test_indicators.py tests/test_api.py -v
```

Expected: tests pass.

## Task 7: Announcements, Admin, And Scheduler Runtime

**Files:**
- Create: `tiance/services/announcement.py`
- Create: `tiance/services/admin.py`
- Create: `tiance/scheduler/runtime.py`
- Create: `tiance/api/admin.py`
- Create: `tiance/api/announcements.py`
- Modify: `tiance/main.py`
- Create: `tests/test_admin.py`

- [ ] **Step 1: Write admin tests**

Create `tests/test_admin.py`:

```python
from datetime import datetime

from tiance.db.migrations import migrate
from tiance.db.sqlite import connect
from tiance.services.admin import AdminService


def test_data_sources_include_source_tables(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    service = AdminService(db_path, scheduler=None)
    rows = service.list_data_sources()
    names = {row["section_name"] for row in rows}
    assert "公告" in names
    assert any("jydb.lc_announcementinfo" in table for row in rows for table in row["source_tables"])


def test_recent_task_status_is_attached(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO task_runs(task_name, started_at, finished_at, status, rows_affected, error) VALUES (?, ?, ?, ?, ?, ?)",
            ("fetch_announcements", datetime.now().isoformat(), datetime.now().isoformat(), "success", 3, None),
        )
        conn.commit()
    service = AdminService(db_path, scheduler=None)
    announcement = next(row for row in service.list_data_sources() if row["task_name"] == "fetch_announcements")
    assert announcement["last_status"] == "success"
    assert announcement["last_rows_affected"] == 3
```

- [ ] **Step 2: Implement announcement classifier and fetcher**

Create `tiance/services/announcement.py`:

```python
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from tiance.db.sqlite import connect, rows_to_dicts

BUSINESS_PATTERN = re.compile("订单|合作|涨价|人事|业绩|年报|半年报|季报|预告|增持|减持|回购|签订|中标|重大合同")
CAPITAL_PATTERN = re.compile("大宗交易|龙虎榜|异动")


def classify_announcement(title: str, category_l1_label: str | None = None) -> str:
    text = f"{title} {category_l1_label or ''}"
    if CAPITAL_PATTERN.search(text):
        return "capital_flow"
    if BUSINESS_PATTERN.search(text):
        return "business"
    return "other"


class AnnouncementService:
    def __init__(self, db_path: Path, tianyan_client):
        self.db_path = db_path
        self.tianyan_client = tianyan_client

    def fetch_all_watchlist(self, since: datetime | None = None) -> int:
        since = since or (datetime.now() - timedelta(days=7))
        with connect(self.db_path) as conn:
            codes = [row["secucode"] for row in conn.execute("SELECT secucode FROM watchlist")]
        total = 0
        for secucode in codes:
            total += self.fetch_for(secucode, since)
        return total

    def fetch_for(self, secucode: str, since: datetime) -> int:
        rows = self.tianyan_client.get_announcements(secucode, since)
        inserted = 0
        now = datetime.now().isoformat(timespec="seconds")
        with connect(self.db_path) as conn:
            for row in rows:
                bucket = classify_announcement(row["title"], row.get("category_l1_label"))
                result = conn.execute(
                    """
                    INSERT OR IGNORE INTO announcements(
                      ann_id, secucode, title, ann_type, category_l1, category_l1_label,
                      category_bucket, is_keyword_hit, publish_at, source, url, local_path,
                      raw_payload, is_read, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, 0, ?)
                    """,
                    (
                        row["ann_id"], secucode, row["title"], row.get("ann_type"),
                        row.get("category_l1"), row.get("category_l1_label"), bucket,
                        1 if bucket == "business" else 0, row["publish_at"], row.get("source", "tianyan"),
                        row.get("url"), json.dumps(row, ensure_ascii=False), now,
                    ),
                )
                inserted += result.rowcount
            conn.commit()
        return inserted

    def list_for_stock(self, secucode: str, bucket: str | None = None, limit: int = 50) -> list[dict]:
        sql = "SELECT * FROM announcements WHERE secucode = ?"
        params: list[object] = [secucode]
        if bucket:
            sql += " AND category_bucket = ?"
            params.append(bucket)
        sql += " ORDER BY publish_at DESC LIMIT ?"
        params.append(limit)
        with connect(self.db_path) as conn:
            return rows_to_dicts(conn.execute(sql, params))
```

- [ ] **Step 3: Implement admin service**

Create `tiance/services/admin.py`:

```python
from pathlib import Path

from tiance.db.sqlite import connect, rows_to_dicts

DATA_SOURCES_META = [
    {"section_name": "公告", "source_tables": ["jydb.lc_announcementinfo (公告元数据)"], "task_name": "fetch_announcements", "schedule_desc": "每小时（每整点 +5 分钟）", "can_refresh": True},
    {"section_name": "龙虎榜", "source_tables": ["jydb.lc_7percentchange (沪深主板/创业板)", "jydb.lc_stiboptradinfo (科创板)"], "task_name": "fetch_rank_list", "schedule_desc": "每交易日 16:30", "can_refresh": True},
    {"section_name": "主力资金流（T-1）", "source_tables": ["wind_admin.ASHAREMONEYFLOW"], "task_name": "fetch_money_flow", "schedule_desc": "每交易日 16:30", "can_refresh": True},
    {"section_name": "K线行情", "source_tables": ["wind_admin.ASHAREEODPRICES"], "task_name": None, "schedule_desc": "按需实时拉取", "can_refresh": False},
    {"section_name": "概念标签", "source_tables": ["jydb.lc_coconcept", "jydb.lc_conceptlist"], "task_name": None, "schedule_desc": "添加股票时自动打标", "can_refresh": False},
    {"section_name": "证券基础信息", "source_tables": ["jydb.secumain"], "task_name": "reload_securities", "schedule_desc": "服务启动时加载到内存", "can_refresh": True},
]


class AdminService:
    def __init__(self, db_path: Path, scheduler):
        self.db_path = db_path
        self.scheduler = scheduler

    def list_data_sources(self) -> list[dict]:
        output = []
        for meta in DATA_SOURCES_META:
            status = self._last_run(meta["task_name"]) if meta["task_name"] else {}
            output.append(
                {
                    **meta,
                    "last_success_at": status.get("finished_at") if status.get("status") == "success" else None,
                    "last_status": status.get("status", "never_run"),
                    "last_rows_affected": status.get("rows_affected"),
                    "last_error": status.get("error"),
                    "next_scheduled_at": None,
                }
            )
        return output

    def _last_run(self, task_name: str | None) -> dict:
        if not task_name:
            return {}
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM task_runs WHERE task_name = ? ORDER BY started_at DESC LIMIT 1",
                (task_name,),
            ).fetchone()
        return dict(row) if row else {}

    def list_tables(self) -> list[str]:
        with connect(self.db_path) as conn:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            return [row["name"] for row in rows]

    def get_table_rows(self, table_name: str, limit: int = 200, offset: int = 0) -> list[dict]:
        if table_name not in self.list_tables():
            return []
        with connect(self.db_path) as conn:
            return rows_to_dicts(
                conn.execute(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (limit, offset))
            )
```

- [ ] **Step 4: Run admin tests**

Run:

```powershell
pytest tests/test_admin.py -v
```

Expected: tests pass.

- [ ] **Step 5: Implement admin and announcement routes**

Create `tiance/api/admin.py` and `tiance/api/announcements.py` with routes from the spec that call `AdminService` and `AnnouncementService`. Every route returns `data_response(...)`.

Minimum required routes for Phase 0 demo:

```python
# tiance/api/admin.py
from fastapi import APIRouter, Request
from tiance.errors import data_response

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/data-sources")
def data_sources(request: Request):
    return data_response(request.app.state.admin_service.list_data_sources())

@router.get("/db/tables")
def tables(request: Request):
    return data_response(request.app.state.admin_service.list_tables())

@router.get("/db/tables/{table_name}/rows")
def table_rows(table_name: str, request: Request, limit: int = 200, offset: int = 0):
    return data_response(request.app.state.admin_service.get_table_rows(table_name, limit, offset))
```

```python
# tiance/api/announcements.py
from fastapi import APIRouter, Request
from tiance.errors import data_response

router = APIRouter(prefix="/api/announcements", tags=["announcements"])

@router.get("/{secucode}")
def list_announcements(secucode: str, request: Request, bucket: str | None = None, limit: int = 50):
    return data_response(request.app.state.announcement_service.list_for_stock(secucode, bucket, limit))
```

- [ ] **Step 6: Wire services and routes in app**

Modify `tiance/main.py` to instantiate `AnnouncementService`, `AdminService`, and include the new routers.

- [ ] **Step 7: Run tests**

Run:

```powershell
pytest -v
```

Expected: all tests pass.

## Task 8: Scheduler Runtime And Manual Refresh

**Files:**
- Create: `tiance/scheduler/runtime.py`
- Create: `tiance/scheduler/jobs.py`
- Modify: `tiance/services/admin.py`
- Modify: `tiance/api/admin.py`
- Modify: `tiance/main.py`
- Modify: `tests/test_admin.py`

- [ ] **Step 1: Add running-task conflict test**

Append to `tests/test_admin.py`:

```python
import pytest

from tiance.errors import TaskRunning


def test_trigger_refresh_rejects_running_task(tmp_path):
    db_path = tmp_path / "tiance.db"
    migrate(db_path)
    service = AdminService(db_path, scheduler=None)
    service.running_tasks.add("fetch_announcements")
    with pytest.raises(TaskRunning):
        service.trigger_refresh("fetch_announcements")
```

- [ ] **Step 2: Implement task-run wrapper**

Create `tiance/scheduler/runtime.py`:

```python
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from tiance.db.sqlite import connect


def run_tracked(db_path: Path, task_name: str, work: Callable[[], int]) -> int:
    started_at = datetime.now().isoformat(timespec="seconds")
    with connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO task_runs(task_name, started_at, status) VALUES (?, ?, ?)",
            (task_name, started_at, "running"),
        )
        run_id = cursor.lastrowid
        conn.commit()
    try:
        rows = work()
    except Exception as exc:
        with connect(db_path) as conn:
            conn.execute(
                "UPDATE task_runs SET finished_at = ?, status = ?, error = ? WHERE id = ?",
                (datetime.now().isoformat(timespec="seconds"), "failed", str(exc), run_id),
            )
            conn.commit()
        raise
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE task_runs SET finished_at = ?, status = ?, rows_affected = ? WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), "success", rows, run_id),
        )
        conn.commit()
    return rows


def create_scheduler() -> BackgroundScheduler:
    return BackgroundScheduler(timezone="Asia/Shanghai")
```

- [ ] **Step 3: Implement scheduled job registration**

Create `tiance/scheduler/jobs.py`:

```python
from tiance.scheduler.runtime import run_tracked


def register_jobs(app) -> None:
    scheduler = app.state.scheduler
    db_path = app.state.settings.db_path

    scheduler.add_job(
        lambda: run_tracked(db_path, "fetch_announcements", app.state.announcement_service.fetch_all_watchlist),
        trigger="cron",
        minute=5,
        id="fetch_announcements",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: run_tracked(db_path, "fetch_rank_list", lambda: 0),
        trigger="cron",
        day_of_week="mon-fri",
        hour=16,
        minute=30,
        id="fetch_rank_list",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: run_tracked(db_path, "fetch_money_flow", lambda: 0),
        trigger="cron",
        day_of_week="mon-fri",
        hour=16,
        minute=30,
        id="fetch_money_flow",
        replace_existing=True,
    )
```

- [ ] **Step 4: Extend AdminService for manual refresh**

Update `tiance/services/admin.py`:

```python
from datetime import datetime
from pathlib import Path

from tiance.db.sqlite import connect, rows_to_dicts
from tiance.errors import TaskRunning

# keep DATA_SOURCES_META from Task 7


class AdminService:
    def __init__(self, db_path: Path, scheduler):
        self.db_path = db_path
        self.scheduler = scheduler
        self.running_tasks: set[str] = set()

    def trigger_refresh(self, task_name: str) -> dict:
        if task_name in self.running_tasks:
            raise TaskRunning(f"任务 {task_name} 正在运行中")
        if self.scheduler is None:
            return {"accepted": True, "run_at": datetime.now().isoformat(timespec="seconds"), "message": "测试模式已接受"}
        self.scheduler.add_job(
            lambda: None,
            trigger="date",
            run_date=datetime.now(),
            id=f"manual_{task_name}_{datetime.now().timestamp()}",
        )
        return {"accepted": True, "run_at": datetime.now().isoformat(timespec="seconds"), "message": "已触发刷新"}

    # keep list_data_sources, _last_run, list_tables, get_table_rows from Task 7
```

When applying this step, merge the new `trigger_refresh` and `running_tasks` members into the existing class instead of removing the already implemented methods.

- [ ] **Step 5: Add refresh API route**

Append to `tiance/api/admin.py`:

```python
@router.post("/refresh/{task_name}", status_code=202)
def refresh(task_name: str, request: Request):
    return data_response(request.app.state.admin_service.trigger_refresh(task_name))
```

- [ ] **Step 6: Wire scheduler lifecycle**

Modify `tiance/main.py` so non-testing apps create and start the scheduler:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

from tiance.scheduler.jobs import register_jobs
from tiance.scheduler.runtime import create_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not getattr(app.state, "testing", False):
        app.state.scheduler = create_scheduler()
        register_jobs(app)
        app.state.scheduler.start()
    yield
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
```

Then initialize the app as:

```python
app = FastAPI(title="Tiance", version="0.1.0", lifespan=lifespan)
app.state.testing = testing
app.state.scheduler = None
```

- [ ] **Step 7: Run admin tests**

Run:

```powershell
pytest tests/test_admin.py -v
```

Expected: tests pass.

## Task 9: Browser UI

**Files:**
- Create: `tiance/web/index.html`
- Create: `tiance/web/styles.css`
- Create: `tiance/web/app.js`
- Modify: `tiance/main.py`

- [ ] **Step 1: Add static HTML**

Create `tiance/web/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>天策</title>
  <link rel="stylesheet" href="/styles.css">
  <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
</head>
<body>
  <aside class="sidebar">
    <header>
      <h1>天策</h1>
      <form id="add-form">
        <input id="stock-query" placeholder="代码或名称" autocomplete="off">
        <button type="submit">添加</button>
      </form>
    </header>
    <div id="watchlist" class="watchlist"></div>
  </aside>
  <main class="workspace">
    <section class="chart-toolbar">
      <strong id="selected-title">选择一只股票</strong>
      <select id="freq">
        <option value="D">日线</option>
        <option value="W">周线</option>
        <option value="M">月线</option>
      </select>
    </section>
    <section id="chart" class="chart"></section>
  </main>
  <aside class="info-panel">
    <nav>
      <button id="tab-announcements">公告</button>
      <button id="tab-admin">Admin</button>
    </nav>
    <div id="info-content"></div>
  </aside>
  <script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Add CSS**

Create `tiance/web/styles.css`:

```css
* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  display: grid;
  grid-template-columns: 280px minmax(420px, 1fr) 360px;
  color: #17202a;
  background: #f6f7f9;
  font-family: "Microsoft YaHei", Arial, sans-serif;
}
.sidebar, .info-panel { background: #ffffff; border-right: 1px solid #dde2e8; padding: 16px; overflow: auto; }
.info-panel { border-right: 0; border-left: 1px solid #dde2e8; }
h1 { margin: 0 0 12px; font-size: 24px; }
form { display: flex; gap: 8px; }
input, select, button { height: 34px; border: 1px solid #c8d0d9; border-radius: 6px; background: #fff; padding: 0 10px; }
button { cursor: pointer; background: #1f6feb; color: #fff; border-color: #1f6feb; }
.watchlist { margin-top: 16px; display: grid; gap: 8px; }
.stock-row { width: 100%; text-align: left; color: #17202a; background: #eef3f8; border-color: #d5dee8; }
.stock-row.active { background: #d8e8ff; border-color: #8bbcff; }
.workspace { min-width: 0; padding: 16px; display: grid; grid-template-rows: 44px 1fr; gap: 12px; }
.chart-toolbar { display: flex; align-items: center; justify-content: space-between; }
.chart { min-height: 520px; background: #fff; border: 1px solid #dde2e8; border-radius: 8px; }
nav { display: flex; gap: 8px; margin-bottom: 12px; }
.item { border-bottom: 1px solid #edf0f3; padding: 10px 0; }
.muted { color: #6b7785; font-size: 12px; }
@media (max-width: 960px) {
  body { grid-template-columns: 1fr; }
  .chart { min-height: 420px; }
}
```

- [ ] **Step 3: Add JavaScript**

Create `tiance/web/app.js`:

```javascript
let selectedCode = null;
const chart = echarts.init(document.getElementById("chart"));

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error?.message || "请求失败");
  }
  return payload.data;
}

async function loadWatchlist() {
  const rows = await api("/api/watchlist");
  const box = document.getElementById("watchlist");
  box.innerHTML = "";
  rows.forEach((row) => {
    const button = document.createElement("button");
    button.className = "stock-row" + (row.secucode === selectedCode ? " active" : "");
    button.textContent = `${row.secuname} ${row.secucode}`;
    button.onclick = () => selectStock(row);
    box.appendChild(button);
  });
}

async function selectStock(row) {
  selectedCode = row.secucode;
  document.getElementById("selected-title").textContent = `${row.secuname} ${row.secucode}`;
  await loadWatchlist();
  await loadKline();
  await loadAnnouncements();
}

async function loadKline() {
  if (!selectedCode) return;
  const freq = document.getElementById("freq").value;
  const data = await api(`/api/market/${selectedCode}/kline?freq=${freq}`);
  const dates = data.points.map((p) => p.date);
  chart.setOption({
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: dates },
    yAxis: { scale: true },
    dataZoom: [{ type: "inside" }, { type: "slider" }],
    series: [
      {
        type: "candlestick",
        data: data.points.map((p) => [p.open, p.close, p.low, p.high]),
      },
    ],
  });
}

async function loadAnnouncements() {
  if (!selectedCode) return;
  const rows = await api(`/api/announcements/${selectedCode}`);
  const box = document.getElementById("info-content");
  box.innerHTML = rows.map((row) => `<div class="item"><strong>${row.title}</strong><div class="muted">${row.publish_at} · ${row.category_bucket}</div></div>`).join("");
}

async function loadAdmin() {
  const rows = await api("/api/admin/data-sources");
  const box = document.getElementById("info-content");
  box.innerHTML = rows.map((row) => `<div class="item"><strong>${row.section_name}</strong><div class="muted">${row.source_tables.join("<br>")}</div><div>${row.last_status}</div></div>`).join("");
}

document.getElementById("add-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = document.getElementById("stock-query").value.trim();
  if (!query) return;
  await api("/api/watchlist", { method: "POST", body: JSON.stringify({ query }) });
  document.getElementById("stock-query").value = "";
  await loadWatchlist();
});

document.getElementById("freq").addEventListener("change", loadKline);
document.getElementById("tab-announcements").addEventListener("click", loadAnnouncements);
document.getElementById("tab-admin").addEventListener("click", loadAdmin);
window.addEventListener("resize", () => chart.resize());

loadWatchlist();
```

- [ ] **Step 4: Mount static files**

Modify `tiance/main.py` to mount static files after API routes:

```python
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory=app.state.settings.root_dir / "tiance" / "web", html=True), name="web")
```

- [ ] **Step 5: Manual UI smoke test**

Run:

```powershell
.\\run_tiance.ps1
```

Open `http://127.0.0.1:8000`.

Expected: the 天策 workspace opens, adding `茅台` shows `贵州茅台 600519.SH`, selecting it draws a candlestick chart.

## Task 10: Verification And Run Notes

**Files:**
- Modify: `docs/superpowers/plans/2026-06-07-tiance-phase0-implementation.md` only if execution reveals corrections needed.

- [ ] **Step 1: Run full backend tests**

Run:

```powershell
pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Run app smoke check**

Run:

```powershell
python -m uvicorn tiance.main:create_app --factory --host 127.0.0.1 --port 8000
```

Expected: Uvicorn reports it is running on `http://127.0.0.1:8000`.

- [ ] **Step 3: Check health endpoint**

In another terminal, run:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Expected:

```text
data
----
@{status=ok}
```

- [ ] **Step 4: Manual browser verification**

Open `http://127.0.0.1:8000`, add `茅台`, select the row, and confirm the K-line chart renders.

- [ ] **Step 5: Record known limitation**

If Tianyan real access is not implemented in this pass, document that the app currently uses `MockTianyanClient` by default and the real client is the next integration task.

## Self-Review Notes

Spec coverage:

- Watchlist: Tasks 5 and 8.
- K-line, MA, MACD, D/W/M: Task 6 and UI in Task 8.
- SQLite and raw table inspection: Tasks 3 and 7.
- Announcement ingest and classification: Task 7.
- Admin data sources and status: Task 7 and UI in Task 8.
- Scheduler framework: Task 8 registers APScheduler cron jobs, records task runs, and exposes manual refresh.
- Mock fallback for no Tianyan connection: Task 4.

Known execution choice:

- The first implementation should prioritize a runnable mock-data local app. Real Tianyan SQL mapping can be added once the UI, storage, and service boundaries are passing tests.
