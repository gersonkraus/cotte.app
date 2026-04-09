/**
 * Componente ChartsGrid - Gráficos do dashboard
 */

export default class ChartsGrid {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.charts = {
      faturamento: null,
      status: null
    };
    this.orcamentos = [];
    this.agora = new Date();
    
    if (!this.container) {
      console.error(`[ChartsGrid] Container não encontrado: ${containerId}`);
      throw new Error(`Container ${containerId} não encontrado`);
    }
  }

  /**
   * Carrega dados e inicializa os gráficos
   * @param {Array} orcamentos - Lista de orçamentos
   */
  async load(orcamentos = []) {
    console.log('[ChartsGrid] Carregando gráficos...');
    
    this.orcamentos = orcamentos || [];
    
    // Renderizar estrutura HTML
    this.render();
    
    // Inicializar gráficos
    await this.initCharts();
    
    // Atualizar gráficos com dados
    this.updateCharts();
    
    console.log('[ChartsGrid] Gráficos carregados');
  }

  /**
   * Renderiza a estrutura HTML dos gráficos
   */
  render() {
    this.container.innerHTML = `
      <div class="card">
        <div class="card-header">
          <div class="card-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="20" x2="18" y2="10"></line>
              <line x1="12" y1="20" x2="12" y2="4"></line>
              <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>
            Faturamento mensal
          </div>
          <div class="card-actions">
            <select id="chart-period" onchange="window.AppState.components.chartsGrid?.updatePeriod(this.value)" style="font-size:12px;padding:4px 8px">
              <option value="6m">Últimos 6 meses</option>
              <option value="3m">Últimos 3 meses</option>
              <option value="1y">Último ano</option>
            </select>
          </div>
        </div>
        <div class="card-body" style="height:260px">
          <canvas id="chart-faturamento"></canvas>
          <div id="chart-faturamento-empty" class="chart-empty" style="display:none">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"
              stroke-linecap="round" stroke-linejoin="round" style="opacity:0.4">
              <line x1="18" y1="20" x2="18" y2="10"></line>
              <line x1="12" y1="20" x2="12" y2="4"></line>
              <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>
            <div>Sem dados de faturamento</div>
          </div>
        </div>
      </div>
      
      <div class="card">
        <div class="card-header">
          <div class="card-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            Status dos orçamentos
          </div>
          <div class="card-actions">
            <button class="btn-icon" onclick="window.AppState.components.chartsGrid?.exportChart('status')" title="Exportar gráfico">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
            </button>
          </div>
        </div>
        <div class="card-body" style="height:260px">
          <canvas id="chart-status"></canvas>
          <div id="chart-status-empty" class="chart-empty" style="display:none">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"
              stroke-linecap="round" stroke-linejoin="round" style="opacity:0.4">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <div>Sem dados de status</div>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Inicializa os gráficos Chart.js
   */
  async initCharts() {
    // Carregar Chart.js dinamicamente se não estiver disponível
    if (typeof Chart === 'undefined') {
      await this.loadChartJS();
    }
    
    // Configurar fontes padrão
    Chart.defaults.font.family = "'DM Sans', sans-serif";
    Chart.defaults.color = 'var(--muted)';
    
    // Inicializar gráfico de faturamento
    this.initFaturamentoChart();
    
    // Inicializar gráfico de status
    this.initStatusChart();
  }

  /**
   * Carrega a biblioteca Chart.js dinamicamente
   */
  async loadChartJS() {
    return new Promise((resolve, reject) => {
      if (typeof Chart !== 'undefined') {
        resolve();
        return;
      }
      
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
      script.onload = () => {
        console.log('[ChartsGrid] Chart.js carregado');
        resolve();
      };
      script.onerror = () => {
        console.error('[ChartsGrid] Falha ao carregar Chart.js');
        reject(new Error('Falha ao carregar Chart.js'));
      };
      
      document.head.appendChild(script);
    });
  }

  /**
   * Inicializa o gráfico de faturamento
   */
  initFaturamentoChart() {
    const ctx = document.getElementById('chart-faturamento');
    if (!ctx) return;
    
    const labels = this.generateMonthLabels(6); // Últimos 6 meses
    
    this.charts.faturamento = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Faturamento',
          data: new Array(labels.length).fill(0),
          backgroundColor: 'rgba(6,182,212,0.1)',
          borderColor: '#06b6d4',
          borderWidth: 2,
          borderRadius: 6,
          borderSkipped: false,
          hoverBackgroundColor: 'rgba(6,182,212,0.2)',
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#ffffff',
            titleColor: '#0f172a',
            bodyColor: '#64748b',
            borderColor: '#e1e7f0',
            borderWidth: 1,
            padding: 10,
            cornerRadius: 8,
            callbacks: {
              label: (context) => {
                const value = context.parsed.y;
                return `Faturamento: R$ ${value.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(100,116,139,0.08)',
              drawBorder: false
            },
            ticks: {
              color: '#94a3b8',
              font: { size: 10 },
              callback: (value) => {
                if (value >= 1000) {
                  return 'R$' + (value / 1000).toFixed(0) + 'k';
                }
                return 'R$' + value;
              }
            },
            border: { display: false }
          },
          x: {
            grid: { display: false },
            ticks: {
              color: '#94a3b8',
              font: { size: 11 }
            },
            border: { display: false }
          }
        }
      }
    });
  }

  /**
   * Inicializa o gráfico de status
   */
  initStatusChart() {
    const ctx = document.getElementById('chart-status');
    if (!ctx) return;
    
    this.charts.status = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Aprovado', 'Enviado', 'Pendente', 'Rascunho', 'Expirado'],
        datasets: [{
          data: [1, 1, 1, 1, 0], // Dados iniciais
          backgroundColor: ['#10b981', '#06b6d4', '#f59e0b', '#94a3b8', '#ef4444'],
          borderWidth: 3,
          borderColor: '#ffffff',
          hoverOffset: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '68%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#64748b',
              font: { size: 10 },
              usePointStyle: true,
              pointStyleWidth: 8,
              padding: 10
            }
          },
          tooltip: {
            backgroundColor: '#ffffff',
            titleColor: '#0f172a',
            bodyColor: '#64748b',
            borderColor: '#e1e7f0',
            borderWidth: 1,
            padding: 10,
            cornerRadius: 8,
            callbacks: {
              label: (context) => {
                const label = context.label || '';
                const value = context.parsed;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                return `${label}: ${value} (${percentage}%)`;
              }
            }
          }
        }
      }
    });
  }

  /**
   * Atualiza os gráficos com dados reais
   */
  updateCharts() {
    if (this.orcamentos.length === 0) {
      this.showEmptyStates();
      return;
    }
    
    this.hideEmptyStates();
    
    // Atualizar gráfico de faturamento
    this.updateFaturamentoChart();
    
    // Atualizar gráfico de status
    this.updateStatusChart();
  }

  /**
   * Atualiza o gráfico de faturamento
   */
  updateFaturamentoChart() {
    if (!this.charts.faturamento) return;
    
    const period = document.getElementById('chart-period')?.value || '6m';
    const months = period === '6m' ? 6 : period === '3m' ? 3 : 12;
    const labels = this.generateMonthLabels(months);
    
    // Calcular faturamento por mês
    const dados = [];
    for (let i = months - 1; i >= 0; i--) {
      const inicio = new Date(this.agora.getFullYear(), this.agora.getMonth() - i, 1);
      const fim = new Date(this.agora.getFullYear(), this.agora.getMonth() - i + 1, 0, 23, 59, 59);
      
      const total = this.orcamentos
        .filter(o => o.status === 'aprovado' && new Date(o.criado_em) >= inicio && new Date(o.criado_em) <= fim)
        .reduce((s, o) => s + (o.total || 0), 0);
      
      dados.push(total);
    }
    
    // Atualizar dados do gráfico
    this.charts.faturamento.data.labels = labels;
    this.charts.faturamento.data.datasets[0].data = dados;
    this.charts.faturamento.update('none');
  }

  /**
   * Atualiza o gráfico de status
   */
  updateStatusChart() {
    if (!this.charts.status) return;
    
    // Contar orçamentos por status
    const statusCount = {
      'aprovado': 0,
      'enviado': 0,
      'pendente': 0,
      'rascunho': 0,
      'expirado': 0
    };
    
    this.orcamentos.forEach(o => {
      const status = o.status || 'rascunho';
      if (statusCount[status] !== undefined) {
        statusCount[status]++;
      } else {
        statusCount['rascunho']++;
      }
    });
    
    // Atualizar dados do gráfico
    this.charts.status.data.datasets[0].data = [
      statusCount.aprovado,
      statusCount.enviado,
      statusCount.pendente,
      statusCount.rascunho,
      statusCount.expirado
    ];
    
    this.charts.status.update('none');
  }

  /**
   * Gera labels de meses para os gráficos
   * @param {number} months - Número de meses
   * @returns {Array} Labels formatados
   */
  generateMonthLabels(months) {
    const labels = [];
    for (let i = months - 1; i >= 0; i--) {
      const d = new Date(this.agora.getFullYear(), this.agora.getMonth() - i, 1);
      labels.push(d.toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' }));
    }
    return labels;
  }

  /**
   * Mostra estados vazios quando não há dados
   */
  showEmptyStates() {
    const emptyFaturamento = document.getElementById('chart-faturamento-empty');
    const emptyStatus = document.getElementById('chart-status-empty');
    
    if (emptyFaturamento) emptyFaturamento.style.display = 'flex';
    if (emptyStatus) emptyStatus.style.display = 'flex';
    
    // Esconder canvases
    const canvasFaturamento = document.getElementById('chart-faturamento');
    const canvasStatus = document.getElementById('chart-status');
    
    if (canvasFaturamento) canvasFaturamento.style.display = 'none';
    if (canvasStatus) canvasStatus.style.display = 'none';
  }

  /**
   * Esconde estados vazios
   */
  hideEmptyStates() {
    const emptyFaturamento = document.getElementById('chart-faturamento-empty');
    const emptyStatus = document.getElementById('chart-status-empty');
    
    if (emptyFaturamento) emptyFaturamento.style.display = 'none';
    if (emptyStatus) emptyStatus.style.display = 'none';
    
    // Mostrar canvases
    const canvasFaturamento = document.getElementById('chart-faturamento');
    const canvasStatus = document.getElementById('chart-status');
    
    if (canvasFaturamento) canvasFaturamento.style.display = 'block';
    if (canvasStatus) canvasStatus.style.display = 'block';
  }

  /**
   * Atualiza o período do gráfico
   * @param {string} period - Período (6m, 3m, 1y)
   */
  updatePeriod(period) {
    console.log('[ChartsGrid] Atualizando período:', period);
    this.updateFaturamentoChart();
  }

  /**
   * Exporta um gráfico como imagem
   * @param {string} chartType - Tipo de gráfico (faturamento, status)
   */
  exportChart(chartType) {
    const chart = this.charts[chartType];
    if (!chart) {
      console.warn(`[ChartsGrid] Gráfico ${chartType} não encontrado`);
      return;
    }
    
    const link = document.createElement('a');
    link.download = `grafico-${chartType}-${new Date().toISOString().split('T')[0]}.png`;
    link.href = chart.toBase64Image();
    link.click();
    
    console.log(`[ChartsGrid] Gráfico ${chartType} exportado`);
  }

  /**
   * Atualiza os dados dos gráficos
   * @param {Array} newOrcamentos - Novos orçamentos
   */
  update(newOrcamentos) {
    if (newOrcamentos) {
      this.orcamentos = newOrcamentos;
    }
    
    this.updateCharts();
    console.log('[ChartsGrid] Gráficos atualizados');
  }

  /**
   * Destroi os gráficos e limpa recursos
   */
  destroy() {
    // Destruir instâncias do Chart.js
    Object.values(this.charts).forEach(chart => {
      if (chart && typeof chart.destroy === 'function') {
        chart.destroy();
      }
    });
    
    this.charts = {
      faturamento: null,
      status: null
    };
    
    this.container.innerHTML = '';
    console.log('[ChartsGrid] Componente destruído');
  }
}

// Exportar para uso global (opcional)
window.ChartsGrid = ChartsGrid;