# Watchlist, Kline, And Announcements Design

## Goal

完善天策现有自选、K 线和公告体验：自选支持删除，K 线展示涨跌幅与成交量变化，公告支持时间筛选、详情打开和本地 AI 摘要展示。

## Architecture

沿用现有 FastAPI + SQLite + 原生前端结构。后端在现有服务中补充可测试字段和查询能力，前端在当前单页应用内扩展交互，不引入新框架。

## Scope

- 自选列表每行增加删除操作，调用已有 `DELETE /api/watchlist/{secucode}`。
- K 线接口为每个点返回 `pct_change` 和 `volume_change_pct`，前端用 ECharts 双网格显示蜡烛图和成交量柱。
- 公告列表默认近 30 天，支持 90、180、365 天筛选。
- 公告同步按当前时间筛选拉取；公告入库时生成 `summary`。
- 公告详情接口返回单条公告，前端点击列表项展示标题、摘要、发布时间、分类、链接和可用正文。

## Summary Strategy

当前先使用本地摘要服务生成稳定摘要：优先基于公告标题、分类和可用原始字段压缩成一段中文摘要。接口边界保留在 `AnnouncementSummaryService`，后续可以替换为真实大模型调用。

## Testing

- API 测试覆盖 K 线新增字段、公告时间筛选、公告详情和摘要字段。
- 静态页面测试覆盖删除按钮、公告时间标签和详情容器。
- 现有测试继续覆盖真实天研/Mock 双链路。
