# Forward Adjusted Kline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a front-adjusted K-line mode and linked vertical crosshair between price and volume charts.

**Architecture:** Extend the existing market API with an `adjust` parameter. The Tianyan client returns enough raw columns for forward adjustment, MarketService applies adjustment before aggregation/indicators, and the existing ECharts page adds a toggle plus linked axis pointer configuration.

**Tech Stack:** Python, FastAPI, SQLite, pytest, vanilla JavaScript, ECharts.

---

### Task 1: Tests

**Files:**
- Modify: `tests/test_indicators.py`
- Modify: `tests/test_api.py`

- [ ] Add a service test using a fake client that returns one unadjusted row and one forward-adjusted row, expecting OHLC to be scaled by `adj_close_backward / close`.
- [ ] Add an API test for `adjust=forward` expecting `data.adjust == "forward"` and point `adjust_ratio`.
- [ ] Add static web tests expecting `id="adjust-forward"` and `axisPointer.link`.

### Task 2: Backend

**Files:**
- Modify: `tiance/models.py`
- Modify: `tiance/clients/tianyan.py`
- Modify: `tiance/clients/mock_tianyan.py`
- Modify: `tiance/services/market.py`
- Modify: `tiance/api/market.py`

- [ ] Add `AdjustMode = Literal["none", "forward"]`.
- [ ] Add `adjust` to `KlineData` and `adjust_ratio` to `KlinePoint`.
- [ ] Query `S_DQ_ADJCLOSE_BACKWARD` and `S_DQ_ADJFACTOR` from Tianyan.
- [ ] Apply forward adjustment in MarketService before resampling.
- [ ] Parse and validate `adjust` in the market route.

### Task 3: Frontend

**Files:**
- Modify: `tiance/web/index.html`
- Modify: `tiance/web/styles.css`
- Modify: `tiance/web/app.js`

- [ ] Add a toggle button labelled `前复权`.
- [ ] Send `adjust=forward` when active.
- [ ] Display adjustment mode in the selected stock metadata.
- [ ] Configure `axisPointer.link` across both x axes and use dashed vertical pointer styling.

### Task 4: Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/technical-and-operations-guide.md`

- [ ] Document the new `adjust` query parameter.
- [ ] Run focused tests.
- [ ] Run full `pytest -q`.
- [ ] Restart local app and browser-smoke the chart toggle.
- [ ] Commit and push.
