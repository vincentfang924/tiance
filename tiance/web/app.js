let selectedCode = null;
let selectedRow = null;
let activePanel = "announcements";

const chartElement = document.getElementById("chart");
const chart = echarts.init(chartElement);

function setStatus(message = "") {
  document.getElementById("status").textContent = message;
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
    const button = document.createElement("button");
    button.type = "button";
    button.className = "stock-row" + (row.secucode === selectedCode ? " active" : "");
    button.innerHTML = `<strong>${row.secuname}</strong><span class="stock-code">${row.secucode}</span>`;
    button.onclick = () => selectStock(row);
    box.appendChild(button);
  });
}

async function selectStock(row) {
  selectedCode = row.secucode;
  selectedRow = row;
  document.getElementById("selected-title").textContent = `${row.secuname} ${row.secucode}`;
  document.getElementById("selected-meta").textContent = row.unread_count ? `未读公告 ${row.unread_count}` : "";
  await loadWatchlist();
  await loadKline();
  await loadActivePanel();
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
    ma: "5,10,20",
  });
  const data = await api(`/api/market/${selectedCode}/kline?${params.toString()}`);
  const dates = data.points.map((point) => point.date);

  chart.setOption({
    animation: false,
    tooltip: { trigger: "axis" },
    grid: { left: 48, right: 18, top: 28, bottom: 58 },
    xAxis: { type: "category", data: dates, boundaryGap: true },
    yAxis: { scale: true, splitLine: { lineStyle: { color: "#edf1f5" } } },
    dataZoom: [{ type: "inside" }, { type: "slider", height: 22, bottom: 18 }],
    series: [
      {
        name: "K线",
        type: "candlestick",
        data: data.points.map((point) => [point.open, point.close, point.low, point.high]),
      },
      ...["ma5", "ma10", "ma20"].map((key) => ({
        name: key.toUpperCase(),
        type: "line",
        smooth: true,
        showSymbol: false,
        data: data.points.map((point) => point.ma?.[key] ?? null),
      })),
    ],
  });
}

async function loadAnnouncements() {
  const box = document.getElementById("info-content");
  if (!selectedCode) {
    box.innerHTML = '<div class="empty">选择股票后显示公告。</div>';
    return;
  }

  const rows = await api(`/api/announcements/${selectedCode}?limit=30`);
  box.innerHTML = rows.length
    ? rows.map((row) => `
      <div class="item">
        <strong>${row.title}</strong>
        <div class="muted">${row.publish_at}</div>
        <span class="badge">${row.category_bucket}</span>
      </div>
    `).join("")
    : '<div class="empty">暂无公告。</div>';
}

async function loadAdmin() {
  const rows = await api("/api/admin/data-sources");
  const box = document.getElementById("info-content");
  box.innerHTML = rows.map((row) => `
    <div class="item">
      <strong>${row.section_name}</strong>
      <div class="muted">${row.schedule_desc}</div>
      <div class="muted">${row.source_tables.join("<br>")}</div>
      <span class="badge">${row.last_status || "never_run"}</span>
    </div>
  `).join("");
}

async function loadActivePanel() {
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
document.getElementById("tab-announcements").addEventListener("click", () => setPanel("announcements"));
document.getElementById("tab-admin").addEventListener("click", () => setPanel("admin"));
window.addEventListener("resize", () => chart.resize());

withStatus(async () => {
  await loadWatchlist();
  if (selectedRow) {
    await selectStock(selectedRow);
  } else {
    await loadActivePanel();
  }
});
