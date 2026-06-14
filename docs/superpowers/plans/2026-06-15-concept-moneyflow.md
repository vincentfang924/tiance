# Concept Moneyflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single-column related concept moneyflow module below the volume chart.

**Architecture:** The Tianyan client exposes concept membership and concept moneyflow aggregation methods. A new `MoneyflowService` filters/sorts the data, a new API router serves it, and the existing web app renders a compact list below the chart.

**Tech Stack:** Python, FastAPI, pytest, vanilla JavaScript, ECharts, SQLite-ready service boundary.

---

### Task 1: Tests

**Files:**
- Modify: `tests/test_api.py`
- Create: `tests/test_moneyflow.py`

- [ ] Add service tests for filtering noisy concepts and sorting by selected window.
- [ ] Add API test for `GET /api/moneyflow/{secucode}/concepts`.
- [ ] Add web shell test for the `concept-moneyflow` panel.

### Task 2: Backend

**Files:**
- Modify: `tiance/clients/tianyan.py`
- Modify: `tiance/clients/mock_tianyan.py`
- Create: `tiance/services/moneyflow.py`
- Create: `tiance/api/moneyflow.py`
- Modify: `tiance/main.py`

- [ ] Add `get_stock_concepts(secucode)`.
- [ ] Add `get_concept_moneyflow(concept_codes, as_of=None)`.
- [ ] Add `MoneyflowService.get_concept_moneyflow(secucode, sort_window, limit)`.
- [ ] Wire API route into the app.

### Task 3: Frontend

**Files:**
- Modify: `tiance/web/index.html`
- Modify: `tiance/web/styles.css`
- Modify: `tiance/web/app.js`

- [ ] Add panel below the chart.
- [ ] Add 今日 / 5日 / 20日 sort tags.
- [ ] Load data after selecting stock.
- [ ] Render red/green flow cards in one column.

### Task 4: Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/technical-and-operations-guide.md`

- [ ] Document the module and API.
- [ ] Run focused tests and full `pytest -q`.
- [ ] Verify real data for `300502.SZ`.
- [ ] Restart local app and browser-smoke the panel.
- [ ] Commit and push.
