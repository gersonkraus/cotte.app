/**
 * CapabilityFlagsService - Base de flags por tela/componente (Sprint 3).
 * Carrega capacidades do backend e expõe helpers simples para UI.
 */
(function () {
  var _cache = null;
  var _loading = null;

  function _fallbackPayload() {
    return {
      flags: {
        assistente_operacional: true,
        engine_analitica: false,
        engine_documental: false,
        copiloto_interno: false,
        code_rag_tecnico: false,
        sql_agent: false,
        langgraph_orchestration: false,
      },
      engines: {},
      components: {
        "nav.assistente_operacional": true,
        "nav.copiloto_interno": false,
        "screen.assistente_operacional": true,
        "screen.copiloto_interno": false,
      },
      available_engines: {
        operational: true,
        analytics: false,
        documental: false,
        internal_copilot: false,
      },
    };
  }

  async function fetchCapabilities() {
    if (_cache) return _cache;
    if (_loading) return _loading;

    var client = window.ApiService || window.api;
    if (!client || typeof client.get !== "function") {
      _cache = _fallbackPayload();
      return _cache;
    }

    _loading = client
      .get("/ai/assistente/capabilities")
      .then(function (resp) {
        var data = resp && resp.data ? resp.data : resp;
        _cache = data && data.flags ? data : _fallbackPayload();
        return _cache;
      })
      .catch(function () {
        _cache = _fallbackPayload();
        return _cache;
      })
      .finally(function () {
        _loading = null;
      });

    return _loading;
  }

  function isEnabledSync(flagName) {
    if (!_cache || !_cache.flags) {
      return flagName === "assistente_operacional";
    }
    return !!_cache.flags[flagName];
  }

  function isComponentEnabledSync(componentKey) {
    if (!_cache || !_cache.components) {
      return componentKey === "nav.assistente_operacional" || componentKey === "screen.assistente_operacional";
    }
    return !!_cache.components[componentKey];
  }

  function isEngineAvailableSync(engineKey) {
    if (!_cache || !_cache.available_engines) {
      return engineKey === "operational";
    }
    return !!_cache.available_engines[engineKey];
  }

  window.CapabilityFlagsService = {
    preload: fetchCapabilities,
    getAll: fetchCapabilities,
    isEnabledSync: isEnabledSync,
    isComponentEnabledSync: isComponentEnabledSync,
    isEngineAvailableSync: isEngineAvailableSync,
  };
})();
