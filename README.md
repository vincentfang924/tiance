# 天策

天策是一个本地运行的股票观察工作台。当前版本默认通过天研拉取真实 A 股数据，包含自选股、K 线行情、公告聚合、管理端数据源状态、调度任务记录、手动刷新和静态浏览器 UI。

## 快速开始

```powershell
pip install -r requirements.txt
pytest -q
python -m uvicorn tiance.main:create_app --factory --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000`，添加 `600519`、`贵州茅台` 或 `德福科技` 后即可查看 K 线与公告。测试或离线演示可设置 `$env:TIANCE_USE_MOCK_TIANYAN='1'` 使用 mock 数据源。

## 文档

- [技术文档与操作指南](docs/technical-and-operations-guide.md)

## 当前能力

- 自选股增删查与详情，页面支持直接删除自选。
- 日/周/月 K 线、前复权切换、均线、MACD、价格涨跌幅、成交量与成交量环比。
- 当前股票相关概念板块的今日、5 日、20 日净资金流，默认实时查询天研，后续可切换本地快照表。
- 公告抓取、分类、去重、近 1 月到近 1 年筛选、详情查看和本地 AI 摘要。
- 管理端数据源状态、SQLite 表浏览和手动刷新接口。
- APScheduler 定时任务框架与 `task_runs` 运行记录。
- 无前端构建链的静态工作台 UI。

## 已知限制

- 非测试模式默认使用真实 `TianyanClient`；如天研未登录，真实行情和公告同步会返回认证错误。
- 本地运行数据写入 `data/tiance.db`，其中自选在 `watchlist`，K 线备份在 `market_bars`，公告在 `announcements`；测试数据写入 `work/tiance_test.db`，两者不会提交到仓库。
