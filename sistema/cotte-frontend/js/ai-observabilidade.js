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
    refreshBtn.addEventListener("click", carregarResumo);
    hoursEl.addEventListener("change", carregarResumo);
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
  }

  document.addEventListener("DOMContentLoaded", init);
})();
