# Concept Moneyflow Design

## Goal

在 K 线成交量下方增加“相关概念资金流”模块。选中股票后，仅统计该股票所属概念/板块在当日、5 日、20 日的净资金流入流出情况。

## Scope

- 不做参考图里的左右资金迁移关系图。
- 不做全市场板块扫描。
- 只展示当前股票所属的有效业务概念。
- 当前版本实时查询天研；后续可在同一服务层增加 SQLite 缓存和历史回看。

## Data Source

遵守天研白名单，只使用：

- `jydb.lc_coconcept`：股票与概念关系。
- `jydb.lc_conceptlist`：概念名称和分类。
- `jydb.secumain`：成分股证券代码映射。
- `wind_admin.ASHAREMONEYFLOW`：个股资金流，使用 `S_MFD_INFLOW` 作为净主动流入金额，单位万元。

## Calculation

1. 根据当前股票 `INNERCODE` 查询有效概念。
2. 过滤非业务概念：`其他`、`地域`、`政策` 这类分类，以及融资融券、转融券、深股通、高价股等噪声标签。
3. 获取 `ASHAREMONEYFLOW` 最新 20 个交易日。
4. 对每个概念的当前成分股汇总：
   - `flow_1d`：最新交易日净流入。
   - `flow_5d`：最近 5 个交易日净流入。
   - `flow_20d`：最近 20 个交易日净流入。
5. 前端按用户选定窗口排序，金额显示为亿元。

## API

新增：

`GET /api/moneyflow/{secucode}/concepts?sort_window=20&limit=12`

返回：

- `secucode`
- `latest_trade_date`
- `sort_window`
- `items[]`
  - `concept_code`
  - `concept_name`
  - `class_name`
  - `subclass_name`
  - `stock_count`
  - `flow_1d`
  - `flow_5d`
  - `flow_20d`

## UI

在中间 K 线区域下方，成交量图下面增加单列模块：

- 标题：相关概念资金流。
- 右侧标签：今日 / 5日 / 20日，用于切换排序口径。
- 每条概念卡片展示概念名、分类、成分股数量、三个窗口净流入。
- 正值红色，负值绿色。

## Future Cache

后续缓存时新增表即可：

- `concept_moneyflow_snapshots`
- 主键可为 `(secucode, concept_code, latest_trade_date)`
- 当前 API 响应结构不变。
