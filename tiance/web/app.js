let selectedCode = null;
let selectedRow = null;
let activePanel = "announcements";
let announcementDays = 30;
let adjustMode = "none";
let moneyflowWindow = 20;

const chartElement = document.getElementById("chart");
const chart = echarts.init(chartElement);

function setStatus(message = "") {
  document.getElementById("status").textContent = message;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}

function formatPct(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  const number = Number(value);
  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toFixed(2)}%`;
}

function formatFlowYi(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  const number = Number(value) / 10000;
  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toFixed(2)}亿`;
}

function flowClass(value) {
  const number = Number(value || 0);
  if (number > 0) return "flow-positive";
  if (number < 0) return "flow-negative";
  return "";
}

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

async function withStatus(work) {
  try {
    setStatus("");
    return await work();
  } catch (error) {
    setStatus(error.message || "请求失败");
    throw error;
  }
}

async function loadWatchlist() {
  const rows = await api("/api/watchlist");
  const box = document.getElementById("watchlist");
  box.innerHTML = "";

  if (!rows.length) {
    box.innerHTML = '<div class="empty">添加 600519 或 贵州茅台开始。</div>';
    return;
  }

  rows.forEach((row) => {
    const item = document.createElement("div");
    item.className = "stock-row" + (row.secucode === selectedCode ? " active" : "");

    const main = document.createElement("button");
    main.type = "button";
    main.className = "stock-main";
    main.innerHTML = `<strong>${escapeHtml(row.secuname)}</strong><span class="stock-code">${escapeHtml(row.secucode)}</span>`;
    main.onclick = () => selectStock(row);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "stock-remove";
    remove.title = "删除自选";
    remove.setAttribute("aria-label", `删除 ${row.secuname}`);
    remove.textContent = "×";
    remove.onclick = (event) => {
      event.stopPropagation();
      withStatus(() => removeStock(row.secucode));
    };

    item.append(main, remove);
    box.appendChild(item);
  });
}

async function removeStock(secucode) {
  await api(`/api/watchlist/${encodeURIComponent(secucode)}`, { method: "DELETE" });
  if (selectedCode === secucode) {
    selectedCode = null;
    selectedRow = null;
    chart.clear();
    document.getElementById("selected-title").textContent = "选择一只股票";
    document.getElementById("selected-meta").textContent = "";
    document.getElementById("sync-announcements").disabled = true;
    document.getElementById("adjust-forward").disabled = true;
    document.getElementById("info-content").innerHTML = '<div class="empty">选择股票后显示公告。</div>';
    document.getElementById("announcement-detail").innerHTML = "";
    renderConceptMoneyflow(null);
  }
  await loadWatchlist();
}

async function selectStock(row) {
  setStatus("");
  selectedCode = row.secucode;
  selectedRow = row;
  document.getElementById("selected-title").textContent = `${row.secuname} ${row.secucode}`;
  updateSelectedMeta(row);
  document.getElementById("sync-announcements").disabled = false;
  document.getElementById("adjust-forward").disabled = false;
  await loadWatchlist();
  await loadKline();
  await loadConceptMoneyflow();
  await loadActivePanel();
}

function updateSelectedMeta(row = selectedRow) {
  const parts = [];
  if (row?.unread_count) parts.push(`未读公告 ${row.unread_count}`);
  if (adjustMode === "forward") parts.push("前复权");
  document.getElementById("selected-meta").textContent = parts.join(" · ");
}

function dateNDaysAgo(days) {
  const value = new Date();
  value.setDate(value.getDate() - days);
  return value.toISOString().slice(0, 10);
}

async function loadKline() {
  if (!selectedCode) return;
  const freq = document.getElementById("freq").value;
  const params = new URLSearchParams({
    start: dateNDaysAgo(180),
    end: new Date().toISOString().slice(0, 10),
    freq,
    adjust: adjustMode,
    ma: "5,10,20",
  });
  const data = await api(`/api/market/${selectedCode}/kline?${params.toString()}`);
  const dates = data.points.map((point) => point.date);
  const priceData = data.points.map((point) => [point.open, point.close, point.low, point.high]);
  const volumeData = data.points.map((point) => ({
    value: point.volume,
    itemStyle: { color: point.pct_change >= 0 ? "#c0362c" : "#21855b" },
  }));

  chart.setOption({
    animation: false,
    axisPointer: {
      link: [{ xAxisIndex: [0, 1] }],
      lineStyle: { type: "dashed", color: "#7b8794" },
    },
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "cross",
        crossStyle: { type: "dashed", color: "#7b8794" },
        lineStyle: { type: "dashed", color: "#7b8794" },
      },
      formatter(items) {
        const index = items[0]?.dataIndex ?? 0;
        const point = data.points[index];
        if (!point) return "";
        return [
          `<strong>${point.date}</strong>`,
          `开 ${formatNumber(point.open)} 高 ${formatNumber(point.high)}`,
          `低 ${formatNumber(point.low)} 收 ${formatNumber(point.close)}`,
          `模式 ${data.adjust === "forward" ? "前复权" : "未复权"}`,
          `涨跌幅 ${formatPct(point.pct_change)}`,
          `成交量 ${formatNumber(point.volume)}`,
          `量比前日 ${formatPct(point.volume_change_pct)}`,
        ].join("<br>");
      },
    },
    grid: [
      { left: 54, right: 20, top: 28, height: "60%" },
      { left: 54, right: 20, top: "73%", height: "15%" },
    ],
    xAxis: [
      {
        type: "category",
        data: dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: "#d9e0e8" } },
        axisPointer: { show: true, type: "line", lineStyle: { type: "dashed", color: "#7b8794" } },
      },
      {
        type: "category",
        gridIndex: 1,
        data: dates,
        boundaryGap: true,
        axisLabel: { show: false },
        axisPointer: { show: true, type: "line", lineStyle: { type: "dashed", color: "#7b8794" } },
      },
    ],
    yAxis: [
      { scale: true, splitLine: { lineStyle: { color: "#edf1f5" } } },
      { gridIndex: 1, scale: true, splitNumber: 2, axisLabel: { formatter: (value) => formatNumber(value) } },
    ],
    dataZoom: [
      { type: "inside", xAxisIndex: [0, 1] },
      { type: "slider", xAxisIndex: [0, 1], height: 22, bottom: 18 },
    ],
    series: [
      {
        name: "K线",
        type: "candlestick",
        data: priceData,
        itemStyle: { color: "#c0362c", color0: "#21855b", borderColor: "#c0362c", borderColor0: "#21855b" },
      },
      ...["ma5", "ma10", "ma20"].map((key) => ({
        name: key.toUpperCase(),
        type: "line",
        smooth: true,
        showSymbol: false,
        data: data.points.map((point) => point.ma?.[key] ?? null),
      })),
      {
        name: "成交量",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumeData,
      },
    ],
  });
}

async function loadAnnouncements() {
  const box = document.getElementById("info-content");
  const detail = document.getElementById("announcement-detail");
  if (!selectedCode) {
    box.innerHTML = '<div class="empty">选择股票后显示公告。</div>';
    detail.innerHTML = "";
    return;
  }

  const rows = await api(`/api/announcements/${selectedCode}?days=${announcementDays}&limit=80`);
  detail.innerHTML = "";
  box.innerHTML = rows.length
    ? rows.map((row) => `
      <div class="item" role="button" tabindex="0" data-ann-id="${escapeHtml(row.ann_id)}">
        <strong>${escapeHtml(row.title)}</strong>
        <div class="muted">${escapeHtml(row.publish_at)}</div>
        <div class="summary">${escapeHtml(row.summary || "暂无摘要")}</div>
        <span class="badge">${escapeHtml(row.category_bucket)}</span>
      </div>
    `).join("")
    : '<div class="empty">暂无公告。</div>';

  box.querySelectorAll(".item[data-ann-id]").forEach((item) => {
    item.addEventListener("click", () => withStatus(() => openAnnouncement(item.dataset.annId)));
    item.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        withStatus(() => openAnnouncement(item.dataset.annId));
      }
    });
  });
}

function renderConceptMoneyflow(data) {
  const box = document.getElementById("moneyflow-list");
  const date = document.getElementById("moneyflow-date");
  document.querySelectorAll(".moneyflow-tab").forEach((button) => {
    button.classList.toggle("active", Number(button.dataset.window) === moneyflowWindow);
  });

  if (!data) {
    date.textContent = "";
    box.innerHTML = '<div class="empty">选择股票后显示相关概念资金流。</div>';
    return;
  }

  date.textContent = data.latest_trade_date ? `更新 ${data.latest_trade_date}` : "";
  if (!data.items?.length) {
    box.innerHTML = '<div class="empty">暂无相关概念资金流。</div>';
    return;
  }

  box.innerHTML = data.items.map((row) => `
    <div class="moneyflow-row">
      <div class="moneyflow-title">
        <strong>${escapeHtml(row.concept_name)}</strong>
        <span class="muted">${escapeHtml(row.class_name || "-")} · ${escapeHtml(row.subclass_name || "-")}</span>
      </div>
      <div class="flow-cell">
        <span>今日</span>
        <strong class="${flowClass(row.flow_1d)}">${formatFlowYi(row.flow_1d)}</strong>
      </div>
      <div class="flow-cell">
        <span>5日</span>
        <strong class="${flowClass(row.flow_5d)}">${formatFlowYi(row.flow_5d)}</strong>
      </div>
      <div class="flow-cell">
        <span>20日</span>
        <strong class="${flowClass(row.flow_20d)}">${formatFlowYi(row.flow_20d)}</strong>
      </div>
      <div class="flow-cell">
        <span>成分股</span>
        <strong>${formatNumber(row.stock_count)}</strong>
      </div>
    </div>
  `).join("");
}

async function loadConceptMoneyflow() {
  if (!selectedCode) {
    renderConceptMoneyflow(null);
    return;
  }
  const params = new URLSearchParams({
    sort_window: String(moneyflowWindow),
    limit: "12",
  });
  const data = await api(`/api/moneyflow/${selectedCode}/concepts?${params.toString()}`);
  renderConceptMoneyflow(data);
}

async function openAnnouncement(annId) {
  if (!selectedCode || !annId) return;
  const row = await api(`/api/announcements/${selectedCode}/${encodeURIComponent(annId)}`);
  const detail = document.getElementById("announcement-detail");
  const link = row.url
    ? `<a class="detail-link" href="${escapeHtml(row.url)}" target="_blank" rel="noreferrer">打开原始公告</a>`
    : "";
  detail.innerHTML = `
    <article class="detail-card">
      <h2>${escapeHtml(row.title)}</h2>
      <div class="muted">${escapeHtml(row.publish_at)} · ${escapeHtml(row.category_bucket)}</div>
      <div class="summary">${escapeHtml(row.summary || "暂无摘要")}</div>
      <div class="detail-body">${escapeHtml(row.content || "当前数据源暂未返回公告正文，可通过原始链接查看。")}</div>
      ${link}
    </article>
  `;
}

async function syncAnnouncements() {
  if (!selectedCode) return;
  await withStatus(async () => {
    const result = await api(`/api/announcements/${selectedCode}/refresh?days=${announcementDays}`, { method: "POST" });
    setStatus(`公告同步完成，新增 ${result.inserted} 条`);
    await loadAnnouncements();
    await loadWatchlist();
  });
}

async function loadAdmin() {
  const rows = await api("/api/admin/data-sources");
  const box = document.getElementById("info-content");
  document.getElementById("announcement-detail").innerHTML = "";
  box.innerHTML = rows.map((row) => `
    <div class="item">
      <strong>${escapeHtml(row.section_name)}</strong>
      <div class="muted">${escapeHtml(row.schedule_desc)}</div>
      <div class="muted">${row.source_tables.map(escapeHtml).join("<br>")}</div>
      <span class="badge">${escapeHtml(row.last_status || "never_run")}</span>
    </div>
  `).join("");
}

async function loadActivePanel() {
  const range = document.getElementById("announcement-range");
  range.style.display = activePanel === "announcements" ? "grid" : "none";
  if (activePanel === "admin") {
    await loadAdmin();
  } else {
    await loadAnnouncements();
  }
}

function setPanel(panel) {
  activePanel = panel;
  document.getElementById("tab-announcements").classList.toggle("active", panel === "announcements");
  document.getElementById("tab-admin").classList.toggle("active", panel === "admin");
  withStatus(loadActivePanel);
}

document.getElementById("add-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.getElementById("stock-query");
  const query = input.value.trim();
  if (!query) return;

  await withStatus(async () => {
    const row = await api("/api/watchlist", { method: "POST", body: JSON.stringify({ query }) });
    input.value = "";
    await selectStock(row);
  });
});

document.getElementById("freq").addEventListener("change", () => withStatus(loadKline));
document.getElementById("sync-announcements").addEventListener("click", syncAnnouncements);
document.getElementById("adjust-forward").addEventListener("click", () => {
  adjustMode = adjustMode === "forward" ? "none" : "forward";
  const button = document.getElementById("adjust-forward");
  button.setAttribute("aria-pressed", String(adjustMode === "forward"));
  updateSelectedMeta();
  withStatus(loadKline);
});
document.getElementById("tab-announcements").addEventListener("click", () => setPanel("announcements"));
document.getElementById("tab-admin").addEventListener("click", () => setPanel("admin"));
document.querySelectorAll(".range-tab").forEach((button) => {
  button.addEventListener("click", () => {
    announcementDays = Number(button.dataset.days);
    document.querySelectorAll(".range-tab").forEach((item) => item.classList.toggle("active", item === button));
    withStatus(loadAnnouncements);
  });
});
document.querySelectorAll(".moneyflow-tab").forEach((button) => {
  button.addEventListener("click", () => {
    moneyflowWindow = Number(button.dataset.window);
    withStatus(loadConceptMoneyflow);
  });
});
window.addEventListener("resize", () => chart.resize());

withStatus(async () => {
  await loadWatchlist();
  if (selectedRow) {
    await selectStock(selectedRow);
  } else {
    await loadActivePanel();
  }
});
