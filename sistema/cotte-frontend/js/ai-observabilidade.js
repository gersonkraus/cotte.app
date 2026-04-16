(function () {
  var refreshBtn = null;
  var hoursEl = null;
  var engineEl = null;
  var companyEl = null;
  var autoRefreshEl = null;
  var alertEl = null;
  var enginesBodyEl = null;
  var metaEl = null;
  var intervalId = null;
  var loading = false;
  var tokenChart = null;

  var ENGINE_COLORS = {
    operational: "#3b82f6",
    internal_copilot: "#10b981",
    monitor: "#f59e0b",
    analytics: "#8b5cf6",
    documental: "#ec4899",
    unknown: "#9ca3af",
  };

  function engineColor(name) {
    return ENGINE_COLORS[String(name).toLowerCase()] || "#9ca3af";
  }

  function formatTokens(n) {
    if (typeof n !== "number") return "-";
    if (n >= 1000000) return (n / 1000000).toFixed(2) + "M";
    if (n >= 1000) return (n / 1000).toFixed(1) + "k";
    return String(n);
  }

  function renderTokenChart(daily, engines) {
    var canvas = document.getElementById("obs-token-chart");
    if (!canvas || typeof Chart === "undefined") return;

    var allEngines = Array.from(
      new Set(daily.flatMap(function (d) { return Object.keys(d).filter(function (k) { return k !== "date"; }); }))
    );

    var labels = daily.map(function (d) { return d.date; });
    var datasets = allEngines.map(function (eng) {
      return {
        label: eng,
        data: daily.map(function (d) { return d[eng] || 0; }),
        borderColor: engineColor(eng),
        backgroundColor: engineColor(eng) + "22",
        fill: true,
        tension: 0.35,
        pointRadius: 3,
      };
    });

    if (tokenChart) {
      tokenChart.destroy();
      tokenChart = null;
    }

    tokenChart = new Chart(canvas, {
      type: "line",
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true,
        plugins: {
          legend: { position: "top", labels: { boxWidth: 12, font: { size: 12 } } },
          tooltip: { mode: "index", intersect: false },
        },
        scales: {
          y: { beginAtZero: true, ticks: { callback: function (v) { return formatTokens(v); } } },
        },
      },
    });
  }

  async function carregarTokenStats() {
    var client = getClient();
    if (!client || typeof client.get !== "function") return;
    var hours = hoursEl && hoursEl.value ? hoursEl.value : "24";
    try {
      var resp = await client.get("/superadmin/monitor-ai/stats?hours=" + hours);
      var payload = resp && resp.data ? resp.data : resp;
      var data = payload && payload.data ? payload.data : payload;
      if (!data) return;

      var tokEl = document.getElementById("obs-kpi-tokens");
      var costEl = document.getElementById("obs-kpi-cost");
      if (tokEl) tokEl.textContent = formatTokens(data.total_tokens || 0);
      if (costEl) costEl.textContent = "$" + (data.cost_usd || 0).toFixed(4);

      if (Array.isArray(data.daily) && data.daily.length > 0) {
        renderTokenChart(data.daily, data.by_engine || {});
      }
    } catch (err) {
      console.warn("[obs] Falha ao carregar token stats:", err && err.message);
    }
  }

  function getClient() {
    return window.ApiService || window.api;
  }

  function isSuperadmin() {
    var user = (typeof getUsuario === "function" && getUsuario()) || null;
    return !!(user && user.is_superadmin);
  }

  function setAlert(message, isError) {
    if (!alertEl) return;
    alertEl.textContent = message || "";
    alertEl.className = isError ? "obs-alert error" : "obs-alert";
  }

  function healthBadge(health) {
    var value = String(health || "no_data").toLowerCase();
    var map = {
      healthy: "Saudavel",
      degraded: "Degradado",
      critical: "Critico",
      no_data: "Sem dados",
    };
    return '<span class="obs-status ' + value + '">' + (map[value] || value) + "</span>";
  }

  function setLoadingState(value) {
    loading = !!value;
    if (!refreshBtn) return;
    refreshBtn.disabled = loading;
    refreshBtn.textContent = loading ? "Atualizando..." : "Atualizar";
  }

  function formatMs(value) {
    if (typeof value !== "number") return "-";
    return value + " ms";
  }

  function renderOverview(overview) {
    var data = overview || {};
    document.getElementById("obs-kpi-calls").textContent = String(data.total_tool_calls || 0);
    document.getElementById("obs-kpi-errors").textContent = String(data.total_errors || 0);
    document.getElementById("obs-kpi-rate").textContent = String(data.error_rate_pct || 0) + "%";
    document.getElementById("obs-kpi-p95").textContent = formatMs(data.p95_latency_ms_max || 0);
    document.getElementById("obs-kpi-audit").textContent = String(data.audit_events || 0);
    document.getElementById("obs-kpi-health").innerHTML = healthBadge(data.health);
  }

  function renderEngines(engines) {
    if (!enginesBodyEl) return;
    var entries = Object.entries(engines || {});
    if (!entries.length) {
      enginesBodyEl.innerHTML = '<tr><td colspan="8" class="obs-muted">Sem dados para os filtros atuais.</td></tr>';
      return;
    }

    enginesBodyEl.innerHTML = entries
      .sort(function (a, b) { return String(a[0]).localeCompare(String(b[0])); })
      .map(function (entry) {
        var key = entry[0];
        var item = entry[1] || {};
        var tools = Array.isArray(item.top_tools) ? item.top_tools : [];
        var topTools = tools.length
          ? tools
              .slice(0, 3)
              .map(function (tool) {
                return String(tool.tool || "tool") + " (" + String(tool.total || 0) + ")";
              })
              .join(", ")
          : "-";

        return (
          "<tr>" +
          "<td><strong>" + key + "</strong></td>" +
          "<td>" + healthBadge(item.health) + "</td>" +
          "<td>" + String(item.total || 0) + "</td>" +
          "<td>" + String(item.errors || 0) + "</td>" +
          "<td>" + String(item.error_rate_pct || 0) + "%</td>" +
          "<td>" + formatMs(item.avg_latency_ms || 0) + "</td>" +
          "<td>" + formatMs(item.p95_latency_ms || 0) + "</td>" +
          "<td class='obs-muted'>" + topTools + "</td>" +
          "</tr>"
        );
      })
      .join("");
  }

  function buildQuery() {
    var params = new URLSearchParams();
    params.set("hours", String(hoursEl && hoursEl.value ? hoursEl.value : "24"));
    if (engineEl && engineEl.value) params.set("engine", String(engineEl.value));
    if (companyEl && companyEl.value) params.set("empresa_id", String(companyEl.value));
    return params.toString();
  }

  async function carregarResumo() {
    if (loading) return;
    var client = getClient();
    if (!client || typeof client.get !== "function") {
      setAlert("Cliente de API indisponivel.", true);
      return;
    }

    setAlert("", false);
    setLoadingState(true);
    try {
      var query = buildQuery();
      var resp = await client.get("/ai/observabilidade/resumo?" + query);
      var payload = resp && resp.data ? resp.data : resp;
      renderOverview(payload && payload.overview);
      renderEngines(payload && payload.engines);
      if (metaEl) {
        var ts = payload && payload.generated_at ? payload.generated_at : null;
        metaEl.textContent = ts
          ? "Atualizado em " + new Date(ts).toLocaleString("pt-BR")
          : "";
      }
    } catch (err) {
      setAlert((err && err.message) || "Falha ao carregar observabilidade.", true);
    } finally {
      setLoadingState(false);
    }
  }

  function configureAutoRefresh() {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
    var everySec = Number(autoRefreshEl && autoRefreshEl.value ? autoRefreshEl.value : 0);
    if (!everySec) return;
    intervalId = setInterval(function () {
      carregarResumo();
    }, everySec * 1000);
  }

  function bindEvents() {
    refreshBtn.addEventListener("click", function () { carregarResumo(); carregarTokenStats(); });
    hoursEl.addEventListener("change", function () { carregarResumo(); carregarTokenStats(); });
    engineEl.addEventListener("change", carregarResumo);
    companyEl.addEventListener("change", carregarResumo);
    autoRefreshEl.addEventListener("change", configureAutoRefresh);
  }

  function init() {
    if (!isSuperadmin()) {
      window.location.href = "./";
      return;
    }

    if (typeof inicializarLayout === "function") {
      inicializarLayout("ai-observabilidade");
    }

    refreshBtn = document.getElementById("obs-refresh-btn");
    hoursEl = document.getElementById("obs-hours");
    engineEl = document.getElementById("obs-engine");
    companyEl = document.getElementById("obs-company");
    autoRefreshEl = document.getElementById("obs-auto-refresh");
    alertEl = document.getElementById("obs-alert");
    enginesBodyEl = document.getElementById("obs-engines-body");
    metaEl = document.getElementById("obs-meta");

    if (!refreshBtn || !hoursEl || !engineEl || !companyEl || !autoRefreshEl || !enginesBodyEl) return;

    bindEvents();
    configureAutoRefresh();
    carregarResumo();
    carregarTokenStats();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
