const params = new URLSearchParams(
  window.location.search
);

const pluginId =
  params.get("plugin") || "dummy";

const stateEl = document.querySelector("#state");
const nameEl = document.querySelector("#plugin-name");
const descriptionEl = document.querySelector("#plugin-description");
const statusListEl = document.querySelector("#status-list");
const metricsEl = document.querySelector("#metrics");
const actionsEl = document.querySelector("#actions");
const actionsEmptyEl = document.querySelector("#actions-empty");
const logsEl = document.querySelector("#logs");
const connectionEl = document.querySelector("#connection");
const minersCardEl = document.querySelector("#miners-card");
const minersBodyEl = document.querySelector("#miners-body");
const minersEmptyEl = document.querySelector("#miners-empty");
const minersSummaryEl = document.querySelector("#miners-summary");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatUptime(seconds) {
  const s = Math.floor(seconds || 0);
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  const clock = `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  return days > 0 ? `${days}d ${clock}` : clock;
}

function formatHashrate(value) {
  const n = Number(value || 0);
  const units = [
    [1e15, "PH/s"],
    [1e12, "TH/s"],
    [1e9, "GH/s"],
    [1e6, "MH/s"],
    [1e3, "kH/s"],
    [1, "H/s"],
  ];
  for (const [scale, unit] of units) {
    if (Math.abs(n) >= scale) {
      return `${(n / scale).toFixed(2)} ${unit}`;
    }
  }
  return "0 H/s";
}

function formatDifficulty(value) {
  const n = Number(value || 0);
  const units = [
    [1e12, "T"],
    [1e9, "G"],
    [1e6, "M"],
    [1e3, "k"],
    [1, ""],
  ];
  for (const [scale, unit] of units) {
    if (Math.abs(n) >= scale) {
      return `${(n / scale).toFixed(2)}${unit}`;
    }
  }
  return "0";
}

function formatAge(timestampSeconds) {
  if (timestampSeconds === null || timestampSeconds === undefined) {
    return "-";
  }
  const age = Math.max(0, Date.now() / 1000 - Number(timestampSeconds));
  if (age < 60) return `${age.toFixed(age < 10 ? 1 : 0)}s ago`;
  if (age < 3600) return `${Math.floor(age / 60)}m ago`;
  return `${Math.floor(age / 3600)}h ago`;
}

function renderMiners(snapshot) {
  const runtime = snapshot.data?.runtime || {};
  const miners = Array.isArray(runtime.miners) ? runtime.miners : [];

  // Only the BCH Stratum status-file adapter currently exposes runtime.miners.
  minersCardEl.hidden = pluginId !== "bch-stratum-proxy";
  if (minersCardEl.hidden) return;

  minersSummaryEl.textContent = `${miners.length} connected`;
  minersEmptyEl.hidden = miners.length > 0;

  minersBodyEl.innerHTML = miners.map(miner => {
    const shares = miner.shares || {};
    const hashrate = miner.hashrate || {};
    const worker = miner.worker_name || "(unauthorized)";
    return `
      <tr>
        <td class="worker-name">${escapeHtml(worker)}</td>
        <td>${escapeHtml(miner.remote_ip || "-")}</td>
        <td>${escapeHtml(formatHashrate(hashrate["5m_hs"]))}</td>
        <td>${escapeHtml(miner.difficulty ?? "-")}</td>
        <td>${escapeHtml(formatDifficulty(miner.best_difficulty))}</td>
        <td>${escapeHtml(formatAge(miner.last_submit_at))}</td>
        <td>${escapeHtml(shares.accepted ?? 0)}</td>
        <td>${escapeHtml(shares.rejected ?? 0)}</td>
      </tr>
    `;
  }).join("");
}

function renderSnapshot(snapshot) {
  const status = snapshot.status;
  const source = snapshot.data?.source || {};

  stateEl.textContent = String(status.state || "unknown").toUpperCase();
  stateEl.className = `state ${status.state}`;

  const sourceAge = Number.isFinite(Number(source.age_seconds))
    ? `${Number(source.age_seconds).toFixed(1)}s`
    : "-";

  statusListEl.innerHTML = `
    <div><dt>Plugin ID</dt><dd>${escapeHtml(status.plugin_id)}</dd></div>
    <div><dt>Uptime</dt><dd>${escapeHtml(formatUptime(status.uptime_seconds))}</dd></div>
    <div><dt>PID</dt><dd>${escapeHtml(status.pid ?? "-")}</dd></div>
    <div><dt>Status age</dt><dd>${escapeHtml(sourceAge)}</dd></div>
    <div><dt>Last error</dt><dd>${escapeHtml(status.last_error ?? "None")}</dd></div>
  `;

  metricsEl.innerHTML = snapshot.metrics.map(metric => `
    <div class="metric">
      <span class="metric-label">${escapeHtml(metric.label)}</span>
      <strong>${escapeHtml(metric.value)}${metric.unit ? ` ${escapeHtml(metric.unit)}` : ""}</strong>
    </div>
  `).join("");

  actionsEl.innerHTML = snapshot.actions.map(action => `
    <button class="${action.dangerous ? "danger" : ""}" data-action="${escapeHtml(action.key)}" title="${escapeHtml(action.description)}">
      ${escapeHtml(action.label)}
    </button>
  `).join("");
  actionsEmptyEl.hidden = snapshot.actions.length > 0;

  for (const button of actionsEl.querySelectorAll("button")) {
    button.addEventListener("click", () => runAction(button.dataset.action));
  }

  logsEl.textContent = snapshot.logs.map(log => {
    const time = new Date(log.timestamp).toLocaleTimeString();
    return `${time} [${log.level}] ${log.message}`;
  }).join("\n");
  logsEl.scrollTop = logsEl.scrollHeight;

  renderMiners(snapshot);
}

async function runAction(actionKey) {
  try {
    const response = await fetch(`/api/plugins/${pluginId}/actions/${actionKey}`, {
      method: "POST"
    });
    if (!response.ok) {
      const body = await response.json();
      throw new Error(body.detail || `HTTP ${response.status}`);
    }
  } catch (error) {
    alert(`Action failed: ${error.message}`);
  }
}

async function loadPluginInfo() {
  const response = await fetch("/api/plugins");
  const plugins = await response.json();
  const plugin = plugins.find(item => item.plugin_id === pluginId);
  if (plugin) {
    nameEl.textContent = plugin.name;
    descriptionEl.textContent = plugin.description;
  } else {
    nameEl.textContent = `Unknown plugin: ${pluginId}`;
  }
}

function connectWebSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${location.host}/api/ws/plugins/${pluginId}`);

  ws.addEventListener("open", () => {
    connectionEl.textContent = "live";
    connectionEl.className = "connected";
  });

  ws.addEventListener("message", event => {
    renderSnapshot(JSON.parse(event.data));
  });

  ws.addEventListener("close", () => {
    connectionEl.textContent = "disconnected; retrying…";
    connectionEl.className = "muted";
    setTimeout(connectWebSocket, 1500);
  });
}

loadPluginInfo().catch(console.error);
connectWebSocket();
