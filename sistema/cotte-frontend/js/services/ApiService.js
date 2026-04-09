/**
 * ApiService.js - Serviço central de API do COTTE
 * Compatível com contrato legado de `api.js` e respostas `sucesso/success`.
 */
var ApiService = (function() {
  var instance = null;

  function normalizePayload(payload) {
    if (!payload || typeof payload !== 'object') return payload;
    if (typeof payload.success !== 'boolean' && typeof payload.sucesso === 'boolean') {
      payload.success = payload.sucesso;
    }
    if (typeof payload.data === 'undefined' && typeof payload.dados !== 'undefined') {
      payload.data = payload.dados;
    }
    return payload;
  }

  function extractErrorMessage(responseData, response) {
    if (responseData && typeof responseData.detail === 'string') return responseData.detail;
    if (responseData && responseData.error && typeof responseData.error.message === 'string') {
      return responseData.error.message;
    }
    if (responseData && typeof responseData.error === 'string') return responseData.error;
    if (responseData && typeof responseData.message === 'string') return responseData.message;
    if (responseData && Array.isArray(responseData.detail)) {
      return responseData.detail.map(function(item) {
        return item && item.msg ? item.msg : String(item);
      }).join(', ');
    }
    return 'Erro ' + response.status + ': ' + response.statusText;
  }

  function getApiUrl(endpoint) {
    var ep = endpoint && endpoint.charAt(0) === '/' ? endpoint : '/' + endpoint;
    if (typeof window.buildApiRequestUrl === 'function') {
      return window.buildApiRequestUrl(ep);
    }
    return '/api/v1' + ep;
  }

  function createInstance() {
    var retryAttempts = 3;
    var cache = new Map();

    function getToken() {
      return localStorage.getItem('cotte_token') || '';
    }

    async function fetchNative(method, endpoint, body, options) {
      var opts = options || {};
      var headers = Object.assign({
        'Content-Type': 'application/json'
      }, opts.headers || {});
      var token = getToken();
      if (token) headers.Authorization = 'Bearer ' + token;

      var fetchOptions = {
        method: method,
        headers: headers
      };
      if (typeof body !== 'undefined' && body !== null) {
        fetchOptions.body = typeof body === 'string' ? body : JSON.stringify(body);
      }

      var url = getApiUrl(endpoint);
      if (typeof window.finalizeFetchUrlForMixedContent === 'function') {
        url = window.finalizeFetchUrlForMixedContent(url);
      }

      var lastError = null;
      for (var attempt = 1; attempt <= retryAttempts; attempt++) {
        try {
          var response = await fetch(url, fetchOptions);
          var text = await response.text();
          var data = null;
          try {
            data = text ? JSON.parse(text) : null;
          } catch (_) {
            data = null;
          }
          data = normalizePayload(data);

          if (response.status === 401 && !opts.bypassAutoLogout && typeof window.logout === 'function') {
            window.logout();
          }

          if (!response.ok) {
            throw new Error(extractErrorMessage(data, response));
          }

          if (method === 'GET') {
            cache.set(endpoint, { data: data, timestamp: Date.now() });
          }
          return data;
        } catch (err) {
          lastError = err;
          if (attempt === retryAttempts) break;
          await new Promise(function(resolve) { setTimeout(resolve, 300 * attempt); });
        }
      }

      window.dispatchEvent(new CustomEvent('api-error', { detail: (lastError && lastError.message) || 'Erro na API' }));
      throw lastError || new Error('Erro na API');
    }

    async function request(method, endpoint, body, options) {
      var m = String(method || 'GET').toLowerCase();
      var opts = options || {};

      // Paridade máxima: quando disponível, delega para cliente legado `api`.
      if (!opts.forceNative && window.api && typeof window.api[m] === 'function') {
        var result;
        if (m === 'get' || m === 'delete') {
          result = await window.api[m](endpoint, opts);
        } else {
          result = await window.api[m](endpoint, body, opts);
        }
        return normalizePayload(result);
      }

      return fetchNative(m.toUpperCase(), endpoint, body, opts);
    }

    return {
      setToken: function(newToken) {
        localStorage.setItem('cotte_token', newToken);
      },
      get: function(endpoint, options) {
        return request('GET', endpoint, undefined, options);
      },
      post: function(endpoint, body, options) {
        return request('POST', endpoint, body, options);
      },
      put: function(endpoint, body, options) {
        return request('PUT', endpoint, body, options);
      },
      patch: function(endpoint, body, options) {
        return request('PATCH', endpoint, body, options);
      },
      delete: function(endpoint, options) {
        return request('DELETE', endpoint, undefined, options);
      },
      clearCache: function() {
        cache.clear();
      }
    };
  }

  return {
    getInstance: function() {
      if (!instance) instance = createInstance();
      return instance;
    }
  };
})();

window.ApiService = ApiService.getInstance();