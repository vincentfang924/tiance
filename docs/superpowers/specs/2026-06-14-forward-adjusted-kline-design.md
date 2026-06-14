# Forward Adjusted Kline Design

## Goal

为天策 K 线增加前复权模式，并让鼠标移动到任意一天时，价格 K 线图和成交量图使用同一条纵向虚线联动。

## Data Source

前复权优先使用 `wind_admin.ASHAREEODPRICES`：

- `S_DQ_ADJCLOSE_BACKWARD`：前复权收盘价。
- `S_DQ_CLOSE`：未复权收盘价。
- `S_DQ_ADJFACTOR`：复权因子，作为后续排障参考。

计算方式：

```text
adjust_ratio = S_DQ_ADJCLOSE_BACKWARD / S_DQ_CLOSE
adjusted_open = S_DQ_OPEN * adjust_ratio
adjusted_high = S_DQ_HIGH * adjust_ratio
adjusted_low = S_DQ_LOW * adjust_ratio
adjusted_close = S_DQ_ADJCLOSE_BACKWARD
```

成交量保持未复权原始值。

## API

`GET /api/market/{secucode}/kline` 增加参数：

- `adjust=none`：默认，未复权。
- `adjust=forward`：前复权。

响应增加：

- `adjust`：当前复权模式。
- `adjust_ratio`：每根 K 线使用的价格复权比例。

## UI

K 线工具栏增加“前复权”切换按钮。开启时重新请求 `adjust=forward`，关闭时请求 `adjust=none`。

ECharts 使用两个 grid：价格和成交量。配置 `axisPointer.link` 关联两个 xAxis，并使用虚线 cross/line 指针，让鼠标移动到 K 线或成交量任一图上时，纵向虚线贯穿两个图。

## Verification

- 服务层测试前复权 OHLC 计算。
- API 测试 `adjust=forward` 返回复权模式和比例。
- Web 静态测试前复权按钮和 axisPointer 配置存在。
- 浏览器冒烟验证切换按钮、K 线渲染和联动配置。
