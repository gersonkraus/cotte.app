/**
 * Serviço de Cache - Gerenciamento de cache em memória com TTL
 */

class CacheService {
  static cache = new Map();
  static defaultTTL = 5 * 60 * 1000; // 5 minutos em milissegundos

  static setDefaultTTL(ttl) {
    this.defaultTTL = ttl;
  }

  /**
   * Armazena um valor no cache
   * @param {string} key - Chave do cache
   * @param {any} value - Valor a ser armazenado
   * @param {number} ttl - Time to live em milissegundos (opcional)
   */
  static set(key, value, ttl = this.defaultTTL) {
    const expiresAt = Date.now() + ttl;
    this.cache.set(key, {
      value,
      expiresAt,
      createdAt: Date.now(),
      ttl
    });
    
    console.log(`[CacheService] Cache set: ${key} (expira em ${new Date(expiresAt).toLocaleTimeString()})`);
    
    // Limpar automaticamente após expiração
    setTimeout(() => {
      if (this.cache.has(key) && this.cache.get(key).expiresAt <= Date.now()) {
        this.cache.delete(key);
        console.log(`[CacheService] Cache expirado: ${key}`);
      }
    }, ttl + 1000); // +1 segundo para garantir
    
    return value;
  }

  /**
   * Obtém um valor do cache
   * @param {string} key - Chave do cache
   * @returns {any|null} Valor armazenado ou null se expirado/não existir
   */
  static get(key) {
    if (!this.cache.has(key)) {
      console.log(`[CacheService] Cache miss: ${key}`);
      return null;
    }

    const entry = this.cache.get(key);
    
    // Verificar se expirou
    if (Date.now() > entry.expiresAt) {
      this.cache.delete(key);
      console.log(`[CacheService] Cache expirado: ${key}`);
      return null;
    }

    console.log(`[CacheService] Cache hit: ${key} (${Math.round((entry.expiresAt - Date.now()) / 1000)}s restantes)`);
    return entry.value;
  }

  /**
   * Remove um item do cache
   * @param {string} key - Chave do cache
   */
  static delete(key) {
    const existed = this.cache.delete(key);
    if (existed) {
      console.log(`[CacheService] Cache deleted: ${key}`);
    }
    return existed;
  }

  /**
   * Limpa todo o cache
   */
  static clear() {
    const size = this.cache.size;
    this.cache.clear();
    console.log(`[CacheService] Cache cleared (${size} itens removidos)`);
  }

  /**
   * Verifica se uma chave existe no cache (não verifica expiração)
   * @param {string} key - Chave do cache
   * @returns {boolean}
   */
  static has(key) {
    return this.cache.has(key);
  }

  /**
   * Obtém informações sobre um item do cache
   * @param {string} key - Chave do cache
   * @returns {object|null} Informações do cache ou null se não existir
   */
  static getInfo(key) {
    if (!this.cache.has(key)) return null;
    
    const entry = this.cache.get(key);
    const now = Date.now();
    const expired = now > entry.expiresAt;
    const remaining = expired ? 0 : entry.expiresAt - now;
    
    return {
      key,
      value: entry.value,
      createdAt: new Date(entry.createdAt),
      expiresAt: new Date(entry.expiresAt),
      ttl: entry.ttl,
      remainingMs: remaining,
      remainingSeconds: Math.round(remaining / 1000),
      expired,
      ageMs: now - entry.createdAt,
      ageSeconds: Math.round((now - entry.createdAt) / 1000)
    };
  }

  /**
   * Obtém estatísticas do cache
   * @returns {object} Estatísticas do cache
   */
  static getStats() {
    const now = Date.now();
    let valid = 0;
    let expired = 0;
    let totalSize = 0;
    
    for (const [key, entry] of this.cache.entries()) {
      const size = this.estimateSize(entry.value);
      totalSize += size;
      
      if (now > entry.expiresAt) {
        expired++;
      } else {
        valid++;
      }
    }
    
    return {
      totalItems: this.cache.size,
      validItems: valid,
      expiredItems: expired,
      estimatedSizeKB: Math.round(totalSize / 1024 * 100) / 100,
      defaultTTL: this.defaultTTL,
      memoryUsage: this.getMemoryUsage()
    };
  }

  /**
   * Limpa itens expirados do cache
   * @returns {number} Número de itens removidos
   */
  static cleanup() {
    const now = Date.now();
    let removed = 0;
    
    for (const [key, entry] of this.cache.entries()) {
      if (now > entry.expiresAt) {
        this.cache.delete(key);
        removed++;
      }
    }
    
    if (removed > 0) {
      console.log(`[CacheService] Cleanup removido ${removed} itens expirados`);
    }
    
    return removed;
  }

  /**
   * Cache com fallback - Tenta cache primeiro, depois busca se não tiver
   * @param {string} key - Chave do cache
   * @param {Function} fetchFn - Função para buscar dados se cache miss
   * @param {number} ttl - TTL em milissegundos (opcional)
   * @returns {Promise<any>} Dados do cache ou da fetchFn
   */
  static async withFallback(key, fetchFn, ttl = this.defaultTTL) {
    // Tentar cache primeiro
    const cached = this.get(key);
    if (cached !== null) {
      return cached;
    }
    
    // Se não tem cache, buscar
    console.log(`[CacheService] Cache miss, buscando: ${key}`);
    try {
      const data = await fetchFn();
      this.set(key, data, ttl);
      return data;
    } catch (error) {
      console.error(`[CacheService] Erro ao buscar dados para cache ${key}:`, error);
      throw error;
    }
  }

  /**
   * Cache para requisições de API
   * @param {string} endpoint - Endpoint da API
   * @param {Function} fetchFn - Função fetch (ApiService.get, etc.)
   * @param {number} ttl - TTL em milissegundos (opcional)
   * @returns {Promise<any>} Dados da API (com cache)
   */
  static async forApi(endpoint, fetchFn, ttl = this.defaultTTL) {
    const cacheKey = `api:${endpoint}`;
    return this.withFallback(cacheKey, fetchFn, ttl);
  }

  /**
   * Invalida cache baseado em padrão de chave
   * @param {string} pattern - Padrão de chave (usando includes)
   * @returns {number} Número de itens removidos
   */
  static invalidatePattern(pattern) {
    let removed = 0;
    
    for (const [key] of this.cache.entries()) {
      if (key.includes(pattern)) {
        this.cache.delete(key);
        removed++;
      }
    }
    
    if (removed > 0) {
      console.log(`[CacheService] Invalidado padrão "${pattern}": ${removed} itens`);
    }
    
    return removed;
  }

  /**
   * Invalida cache relacionado a orçamentos
   */
  static invalidateOrcamentos() {
    return this.invalidatePattern('orcamentos');
  }

  /**
   * Invalida cache relacionado a clientes
   */
  static invalidateClientes() {
    return this.invalidatePattern('clientes');
  }

  /**
   * Invalida cache relacionado a dashboard
   */
  static invalidateDashboard() {
    return this.invalidatePattern('dashboard');
  }

  // Métodos auxiliares privados
  static estimateSize(obj) {
    // Estimativa simples de tamanho em bytes
    try {
      const json = JSON.stringify(obj);
      return new Blob([json]).size;
    } catch {
      return 0;
    }
  }

  static getMemoryUsage() {
    if (window.performance && window.performance.memory) {
      return {
        usedJSHeapSize: window.performance.memory.usedJSHeapSize,
        totalJSHeapSize: window.performance.memory.totalJSHeapSize,
        jsHeapSizeLimit: window.performance.memory.jsHeapSizeLimit
      };
    }
    return null;
  }

  /**
   * Configura limpeza automática periódica
   * @param {number} intervalMs - Intervalo em milissegundos (padrão: 1 minuto)
   */
  static setupAutoCleanup(intervalMs = 60000) {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }
    
    this.cleanupInterval = setInterval(() => {
      const removed = this.cleanup();
      if (removed > 0) {
        console.log(`[CacheService] Auto-cleanup: ${removed} itens expirados removidos`);
      }
    }, intervalMs);
    
    console.log(`[CacheService] Auto-cleanup configurado a cada ${intervalMs / 1000}s`);
  }
}

// Inicializar auto-cleanup (1 minuto)
CacheService.setupAutoCleanup();

// Exportar singleton para uso global (opcional)
window.CacheService = CacheService;