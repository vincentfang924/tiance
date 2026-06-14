# Watchlist Kline Announcements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add watchlist deletion UI, K-line percentage/volume-change display, and announcement filtering/detail/summary support.

**Architecture:** Extend the current FastAPI services and SQLite schema in place. Keep the browser app as a single HTML/CSS/JS surface using ECharts for both price and volume panes.

**Tech Stack:** Python, FastAPI, SQLite, pytest, vanilla JavaScript, ECharts.

---

### Task 1: API Coverage

**Files:**
- Modify: `tests/test_api.py`
- Modify: `tests/test_indicators.py`

- [ ] Add failing API tests for K-line `pct_change` and `volume_change_pct`.
- [ ] Add failing API tests for announcement `days` filtering, detail endpoint, and `summary`.
- [ ] Add failing web shell assertions for delete button class, announcement range controls, and detail panel.

### Task 2: Backend Implementation

**Files:**
- Modify: `tiance/models.py`
- Modify: `tiance/db/migrations.py`
- Modify: `tiance/services/market.py`
- Modify: `tiance/services/announcement.py`
- Modify: `tiance/api/announcements.py`

- [ ] Add optional percentage fields to K-line models.
- [ ] Add `summary` and `content` columns to `announcements`, including idempotent migration for existing DBs.
- [ ] Compute price and volume percentage changes after indicator calculation.
- [ ] Generate and persist local announcement summaries during fetch.
- [ ] Add `GET /api/announcements/{secucode}/{ann_id}` and `days` filtering on list.

### Task 3: Frontend Implementation

**Files:**
- Modify: `tiance/web/index.html`
- Modify: `tiance/web/styles.css`
- Modify: `tiance/web/app.js`

- [ ] Add delete controls to watchlist rows.
- [ ] Render price and volume in separate ECharts grids with tooltip percentage details.
- [ ] Add announcement time tags and detail panel.
- [ ] Load announcement summaries and details from the new API fields.

### Task 4: Verification And Delivery

**Files:**
- Modify: documentation if behavior changed.

- [ ] Run focused tests.
- [ ] Run full `pytest -q`.
- [ ] Restart local app if needed and browser-smoke the flow.
- [ ] Commit and push to GitHub.
