# 天策 Phase 0 设计说明

日期：2026-06-07

## 目标

天策是面向 A 股的本地股票信息收集与分析系统。Phase 0 先实现最小可用闭环：

- 手动添加股票到关注列表，并维护分组、备注、排序。
- 基于天研数据展示 K 线、均线、MACD、成交量和多股归一化对比。
- 定时同步关注股票的公告、龙虎榜、主力资金流等信息，并保存到本地。
- 提供 admin 页面展示每个板块的数据来源、最近更新时间、任务状态，并支持手动刷新。
- 使用本地 SQLite 保存用户数据、公告元数据、调度记录和可排查的原始响应。

不进入 Phase 0 的能力：

- 雪球/股吧热度与情绪分析。
- 国内外宏观新闻聚合。
- AI 综合评分、买入/卖出建议。
- 逐个公司官网爬取。Phase 0 使用天研/巨潮/交易所公告数据作为官方公告来源。

## 已确认取舍

系统按 Phase 0 / Phase 1 / Phase 2 分期建设。Phase 0 做基础设施与最小闭环；Phase 1 接入论坛情绪和宏观新闻；Phase 2 基于前两期数据做 AI 综合分析。

UI 采用本地 Web 应用。后端使用 FastAPI，前端用浏览器打开本地服务。推荐监听 `127.0.0.1`，不开放外网访问，Phase 0 不做登录鉴权。

运行模式采用一个常驻 Python 服务，Web 与调度在同一进程内。Windows 开机自启使用任务计划程序，触发条件为“用户登录时启动”。进程内使用 APScheduler 注册定时任务。

本地存储采用 SQLite。Python 标准库自带 `sqlite3`，用户不需要额外安装 SQLite 服务。数据库文件是普通本地文件，默认路径为 `data/tiance.db`。

行情 K 线不做持久化缓存，按需从天研实时查询，并在进程内做短期 LRU 缓存。这样避免缓存失效复杂度，优先保证数据新鲜和逻辑简单。

## 架构

Phase 0 使用单体本地 Web 架构：

```text
Browser UI
  |
FastAPI routes
  |
Service layer
  |-- watchlist
  |-- concepts
  |-- market
  |-- announcement
  |-- moneyflow
  |-- admin
  |
SQLite repository + Tianyan client + Scheduler
```

分层职责：

- `api/`：HTTP 路由、请求校验、响应封装。
- `services/`：业务逻辑，不直接处理 HTTP。
- `repositories/`：SQLite 读写。
- `clients/`：天研命令/SQL 封装。
- `scheduler/`：APScheduler 任务注册、运行记录、手动触发。
- `web/`：前端页面与静态资源。

## 数据库设计

核心表：

```sql
watchlist(
  secucode TEXT PRIMARY KEY,
  secuname TEXT NOT NULL,
  group_id INTEGER,
  note TEXT,
  sort_order INTEGER NOT NULL DEFAULT 0,
  added_at TEXT NOT NULL
)

groups(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
)

concepts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  source TEXT NOT NULL,
  created_at TEXT NOT NULL
)

stock_concepts(
  secucode TEXT NOT NULL,
  concept_id INTEGER NOT NULL,
  added_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY(secucode, concept_id)
)

announcements(
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
)

money_flows(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  secucode TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  main_net_inflow REAL,
  main_net_inflow_pct REAL,
  raw_payload TEXT,
  UNIQUE(secucode, trade_date)
)

rank_list_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  secucode TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  reason TEXT,
  amount REAL,
  raw_payload TEXT,
  UNIQUE(secucode, trade_date, reason)
)

task_runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_name TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  rows_affected INTEGER,
  error TEXT
)
```

用户可以在 admin 页面直查数据库表的前 200 行，便于排查。`raw_payload` 字段保存关键原始数据片段，避免只存加工结果后无法追踪问题。

## 天研数据源

数据源白名单只使用 `jydb` 和 `wind_admin`。所有 SQL 必须带库名，避免误查其他 schema。

Phase 0 主要数据源：

- 证券基础信息：`jydb.secumain`
- K 线行情：`wind_admin.ASHAREEODPRICES`
- 公告元数据：`jydb.lc_announcementinfo`
- 概念标签：`jydb.lc_coconcept`、`jydb.lc_conceptlist`
- 龙虎榜：`jydb.lc_7percentchange`、`jydb.lc_stiboptradinfo`
- 主力资金流：`wind_admin.ASHAREMONEYFLOW`

证券基础信息在服务启动时加载到内存，用于股票代码、股票名称、市场后缀解析。

## Service 设计

`services/watchlist.py`：

- `add_stock(query, group_id=None)`：按代码或名称查证券基础信息，添加到关注列表，并自动拉取概念标签。
- `remove_stock(secucode)`
- `list_watchlist(sort_by, range_start, range_end)`：返回关注列表、概念、最新快照、区间涨跌幅、未读公告数。
- `update_stock(secucode, note=None, group_id=None, sort_order=None)`
- `reorder(group_id, ordered_codes)`

`services/concepts.py`：

- `auto_tag(secucode)`：添加股票时自动拉取概念。
- `refresh_for(secucode)`：详情页手动重新拉概念，保留用户手动添加的概念。
- `add_manual(secucode, concept_id)` / `remove(secucode, concept_id)`
- `stocks_with_concept(concept_id)`

`services/market.py`：

- `get_kline(secucode, start, end, freq, ma, macd)`：拉日线，按需聚合周线/月线，再计算 MA 与 MACD。
- `get_quote_snapshot(secucodes)`：批量获取最新价与当日涨跌幅。
- `get_range_pct(secucode, start, end)`：区间涨跌幅。
- `get_normalized_compare(secucodes, start, end, freq)`：多股归一化对比。

`services/announcement.py`：

- `fetch_for(secucode, since)`：拉取指定股票自 `since` 之后的公告，去重写库。
- `fetch_all_watchlist()`：调度任务，遍历关注列表并同步公告。
- `list_for_stock(secucode, bucket=None, limit=50)`
- `mark_read(ann_ids)`
- `unread_count(secucode)`

公告分类规则：

- `capital_flow`：标题含“大宗交易”“龙虎榜”“异动”等交易事件。
- `business`：业绩、财报、重大事项、重大合同、股东大会、订单、合作、涨价、人事、预告、增持、减持、回购、签订、中标等。
- `other`：兜底分类。

`services/moneyflow.py`：

- `fetch_rank_list(date_range)`：全市场拉取龙虎榜数据，再与关注列表内连接，仅保存关注股票。
- `fetch_money_flow(date_range)`：全市场拉取主力资金流，再与关注列表内连接。
- `get_rank_list_for(secucode, days=30)`
- `get_money_flow_for(secucode, days=30)`
- `get_recent_block_trades(secucode, days=30)`

`services/admin.py`：

- `list_data_sources()`：列出每个板块的数据来源、调度描述、最近状态、最近更新时间、下次运行时间。
- `trigger_refresh(task_name)`：手动触发可刷新任务，同名任务运行中时返回冲突。
- `list_tables()` / `get_table_rows(table_name, limit=200, offset=0)`
- `get_recent_runs(task_name=None, limit=50)`
- `get_scheduler_state()`

## 调度设计

APScheduler 任务：

- `fetch_announcements`：每小时整点 +5 分钟运行。
- `fetch_rank_list`：每个交易日 16:30 运行。
- `fetch_money_flow`：每个交易日 16:30 运行。
- `startup_backfill`：服务启动时检查 `task_runs`，如果公告任务距离上次成功超过 1 小时，则补跑一次。

每次任务运行都写 `task_runs`，包含开始时间、完成时间、状态、影响行数、错误信息。

手动刷新策略：

- 前端点击“立即刷新”后调用 `POST /api/admin/refresh/{task_name}`。
- 后端立即返回 `202`，任务后台运行。
- 如果同名任务已在运行，返回 `409 TASK_RUNNING`，不排队。
- 前端每 2 秒轮询 `GET /api/admin/data-sources`，直到任务状态不再是 `running`。

## API 设计

所有 API 使用 `/api/` 前缀，REST 风格，成功响应包为：

```json
{ "data": {} }
```

错误响应包为：

```json
{ "error": { "code": "STOCK_NOT_FOUND", "message": "未找到股票" } }
```

关键路由：

- `GET /api/watchlist`
- `POST /api/watchlist`
- `GET /api/watchlist/{secucode}`
- `PATCH /api/watchlist/{secucode}`
- `DELETE /api/watchlist/{secucode}`
- `GET /api/groups`
- `POST /api/groups`
- `GET /api/concepts`
- `POST /api/watchlist/{secucode}/concepts/refresh`
- `GET /api/market/{secucode}/kline`
- `GET /api/market/quotes`
- `GET /api/market/{secucode}/range_pct`
- `POST /api/market/compare`
- `GET /api/announcements/{secucode}`
- `POST /api/announcements/mark_read`
- `GET /api/moneyflow/{secucode}/rank_list`
- `GET /api/moneyflow/{secucode}/flow`
- `GET /api/moneyflow/{secucode}/block_trades`
- `GET /api/admin/data-sources`
- `POST /api/admin/refresh/{task_name}`
- `GET /api/admin/task-runs`
- `GET /api/admin/db/tables`
- `GET /api/admin/db/tables/{table_name}/rows`
- `GET /api/admin/scheduler`

业务错误：

- `STOCK_NOT_FOUND`：股票代码或名称无法解析。
- `ALREADY_WATCHING`：重复添加。
- `TASK_RUNNING`：同名刷新任务正在运行。
- `TIANYAN_UNAVAILABLE`：天研不可用。
- `INVALID_FREQ`：K 线周期参数非法。

## UI 设计

首屏是工作台，不做营销页。

主要视图：

- 左侧关注列表：分组、搜索添加、排序、未读公告数、区间涨跌幅。
- 中央股票详情：K 线图、成交量、MACD、均线开关、日期范围、D/W/M 切换。
- 右侧信息流：公告、资金动向、概念标签、备注。
- 全局对比页：选择多只关注股票，展示归一化收益曲线。
- Admin 页：数据源状态、手动刷新、任务历史、数据库直查。

前端用 ECharts 绘制 K 线和对比图。Phase 0 不做 WebSocket 或 SSE。

## 安全与边界

服务只监听 `127.0.0.1`。Phase 0 不做认证，不开放 CORS。

写接口必须做输入校验。股票代码标准格式为 `^\d{6}\.(SH|SZ|BJ)$`。SQL 使用参数化查询。

买卖建议不在 Phase 0 实现，避免在数据底座未稳定前输出投资建议。

## 测试与验收

后端测试：

- SQLite migration 可重复执行。
- `watchlist` 添加、删除、重复添加、排序。
- 公告分类关键词规则。
- MA、MACD、周/月线聚合为纯函数单测。
- `admin` 数据源状态聚合与运行中冲突处理。
- API 错误包格式。

前端验证：

- 能添加股票并显示在关注列表。
- 能打开股票详情页并看到 K 线图。
- 能切换日期范围、D/W/M、均线和 MACD。
- Admin 页面显示数据来源、最近更新、任务历史。
- 手动刷新按钮能触发后台任务，运行中重复点击返回提示。

首版验收标准：

- 本地启动服务后，浏览器可打开工作台。
- 不需要用户安装 SQLite。
- 至少可以在无天研连接时使用 mock 数据完成 UI 与基础 API 演示。
- 天研连接可用时，能查询真实证券基础信息和 K 线数据。

## 后续 Phase

Phase 1 接入雪球/股吧热度、讨论摘要、情绪比例、宏观新闻源。

Phase 2 在公告、资金、情绪、宏观数据稳定后，加入 AI 综合评分与观点摘要。该模块只作为研究辅助，不直接替代投资决策。
