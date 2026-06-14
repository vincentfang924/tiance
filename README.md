# 天策

天策是一个本地运行的股票观察工作台。当前 Phase 0 使用 mock 天眼数据跑通端到端闭环，包括自选股、K 线行情、公告聚合、管理端数据源状态、调度任务记录、手动刷新和静态浏览器 UI。

## 快速开始

```powershell
pip install -r requirements.txt
pytest -q
python -m uvicorn tiance.main:create_app --factory --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000`，添加 `600519` 或 `贵州茅台` 后即可查看 K 线与公告。

## 文档

- [技术文档与操作指南](docs/technical-and-operations-guide.md)

## 当前能力

- 自选股增删查与详情。
- 日/周/月 K 线、均线与 MACD 指标服务。
- 公告抓取、分类、去重和列表接口。
- 管理端数据源状态、SQLite 表浏览和手动刷新接口。
- APScheduler 定时任务框架与 `task_runs` 运行记录。
- 无前端构建链的静态工作台 UI。

## 已知限制

- 当前默认使用 `MockTianyanClient`，真实天眼 SQL/接口映射是下一阶段集成任务。
- 本地运行数据写入 `data/tiance.db`，测试数据写入 `work/tiance_test.db`，两者不会提交到仓库。
