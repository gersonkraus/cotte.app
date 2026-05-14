/**
 * Seleção individual de produtos para geração de portfólio (catálogo).
 * Depende de: utils.js (escapeHtml, formatarMoeda), api.js (api).
 */
(function () {
  var selecionados = new Set();
  var cache = [];
  var carregouGrade = false;

  function gridEl() {
    return document.getElementById('portfolio-produtos-grid');
  }

  function contadorEl() {
    return document.getElementById('portfolio-contador');
  }

  function atualizarContador() {
    var el = contadorEl();
    if (el) {
      el.textContent = selecionados.size + ' produto(s) selecionado(s)';
    }
  }

  function renderizarGrade() {
    var container = gridEl();
    if (!container) return;

    if (!cache.length) {
      container.innerHTML =
        '<div style="grid-column:1/-1;text-align:center;padding:20px;color:var(--muted);font-size:13px">Nenhum produto ativo encontrado.</div>';
      atualizarContador();
      return;
    }

    container.innerHTML = cache
      .map(function (p) {
        var sel = selecionados.has(p.id);
        var nome = typeof escapeHtml === 'function' ? escapeHtml(p.nome || '') : String(p.nome || '');
        var preco =
          typeof formatarMoeda === 'function'
            ? formatarMoeda(p.preco_padrao)
            : String(p.preco_padrao);
        var imgUrl = p.imagem_url ? (typeof api !== 'undefined' && api.resolveUrl ? api.resolveUrl(p.imagem_url) : p.imagem_url) : '';
        var imgBlock = imgUrl
          ? '<img src="' +
            String(imgUrl).replace(/"/g, '&quot;') +
            '" alt="' +
            nome.replace(/"/g, '&quot;') +
            '" loading="lazy" decoding="async">'
          : '<div class="portfolio-produto-sem-imagem">Sem foto</div>';
        return (
          '<div class="portfolio-produto-card' +
          (sel ? ' is-selected' : '') +
          '" data-pid="' +
          p.id +
          '" role="checkbox" aria-checked="' +
          (sel ? 'true' : 'false') +
          '">' +
          '<div class="portfolio-produto-imagem">' +
          imgBlock +
          '<div class="portfolio-produto-check">✓</div></div>' +
          '<div class="portfolio-produto-info">' +
          '<div class="portfolio-produto-nome">' +
          nome +
          '</div>' +
          '<div class="portfolio-produto-preco">' +
          preco +
          '</div></div></div>'
        );
      })
      .join('');

    container.querySelectorAll('.portfolio-produto-card').forEach(function (card) {
      card.addEventListener('click', function () {
        var id = parseInt(card.getAttribute('data-pid'), 10);
        if (!id) return;
        if (selecionados.has(id)) selecionados.delete(id);
        else selecionados.add(id);
        renderizarGrade();
      });
    });

    atualizarContador();
  }

  function preencherFiltroCategorias(lista) {
    var sel = document.getElementById('portfolio-filtro-categoria');
    if (!sel || !lista) return;
    var atual = sel.value;
    var opts = '<option value="">Todas as categorias</option>';
    lista.forEach(function (c) {
      var nome = typeof escapeHtml === 'function' ? escapeHtml(c.nome || '') : String(c.nome || '');
      opts += '<option value="' + c.id + '">' + nome + '</option>';
    });
    sel.innerHTML = opts;
    if (atual) sel.value = atual;
  }

  async function carregarProdutos(categoriaId) {
    var params = new URLSearchParams();
    if (categoriaId) params.set('categoria_id', String(categoriaId));
    var q = params.toString();
    var path = '/catalogo/portfolio/produtos' + (q ? '?' + q : '');
    var data = await api.get(path);
    cache = Array.isArray(data) ? data : [];
    renderizarGrade();
  }

  function selecionarTodosVisiveis() {
    cache.forEach(function (p) {
      selecionados.add(p.id);
    });
    renderizarGrade();
  }

  function limparSelecao() {
    selecionados.clear();
    renderizarGrade();
  }

  function getProdutosSelecionados() {
    return Array.from(selecionados);
  }

  function reset() {
    selecionados.clear();
    cache = [];
    carregouGrade = false;
    var container = gridEl();
    if (container) container.innerHTML = '';
    atualizarContador();
  }

  function aoAbrirModal(categoriasLista) {
    reset();
    preencherFiltroCategorias(categoriasLista || []);
    setPortfolioTab('categorias', true);
  }

  window.portfolioTabAtiva = function () {
    var b = document.querySelector('.portfolio-tab-btn.is-active');
    return (b && b.getAttribute('data-tab')) || 'categorias';
  };

  window.setPortfolioTab = function (tab, silent) {
    var botoes = document.querySelectorAll('.portfolio-tab-btn');
    var wrapCat = document.getElementById('portfolio-wrap-categorias');
    var wrapProd = document.getElementById('portfolio-wrap-produtos');
    botoes.forEach(function (btn) {
      var t = btn.getAttribute('data-tab');
      var on = t === tab;
      btn.classList.toggle('is-active', on);
      btn.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    if (wrapCat) {
      wrapCat.classList.toggle('is-hidden', tab === 'produtos');
    }
    if (wrapProd) {
      wrapProd.classList.toggle('is-visible', tab === 'produtos');
      wrapProd.setAttribute('aria-hidden', tab === 'produtos' ? 'false' : 'true');
    }
    if (tab === 'produtos' && !carregouGrade) {
      carregouGrade = true;
      carregarProdutos(null).catch(function (e) {
        carregouGrade = false;
        if (!silent && typeof showNotif === 'function') {
          showNotif('❌', 'Erro', e.message || String(e), 'error');
        }
      });
    }
  };

  window.PortfolioSelector = {
    carregarProdutos: carregarProdutos,
    selecionarTodos: selecionarTodosVisiveis,
    limparSelecao: limparSelecao,
    getProdutosSelecionados: getProdutosSelecionados,
    reset: reset,
    aoAbrirModal: aoAbrirModal,
  };

  document.addEventListener('change', function (ev) {
    var t = ev.target;
    if (t && t.id === 'portfolio-filtro-categoria') {
      carregarProdutos(t.value || null).catch(function (e) {
        if (typeof showNotif === 'function') {
          showNotif('❌', 'Erro', e.message || String(e), 'error');
        }
      });
    }
  });
})();
