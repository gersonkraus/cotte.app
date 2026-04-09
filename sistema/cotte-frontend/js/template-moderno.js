/**
 * Template Moderno para orçamento público
 * Carregado quando orc.empresa.template === 'moderno'
 */
function renderizarTemplateModerno(orc, token, API) {
  const cor = (orc.empresa && orc.empresa.cor_primaria) || '#00e5a0';
  const emp = orc.empresa || {};
  const itens = orc.itens || [];
  const desc = orc.desconto || 0;
  const descTipo = orc.desconto_tipo || 'percentual';
  const subtotal = itens.reduce((s, i) => s + (i.total || 0), 0);
  const aceiteJaRegistrado = Boolean(orc.aceite_nome && orc.aceite_em);

  function fmtMoeda(v) {
    return 'R$ ' + Number(v || 0).toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  function fmtData(d) {
    if (!d) return '\u2014';
    return new Date(d).toLocaleDateString('pt-BR');
  }

  function dataVencimento(criadoEm, dias) {
    var d = new Date(criadoEm);
    d.setDate(d.getDate() + (dias || 7));
    return d.toLocaleDateString('pt-BR');
  }

  function escHtml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function whatsappLink(telefone) {
    if (!telefone || typeof telefone !== 'string') return null;
    var dig = telefone.replace(/\D/g, '');
    if (dig.length < 10) return null;
    var num = dig.startsWith('55') ? dig : '55' + dig;
    return 'https://wa.me/' + num;
  }

  var STATUS_BADGE = {
    rascunho: { bg: '#f3f4f6', color: '#374151', icone: '\uD83D\uDCDD', texto: 'Rascunho' },
    enviado:  { bg: '#fef9c3', color: '#854d0e', icone: '\u23F3', texto: 'Aguardando aprova\u00e7\u00e3o' },
    aprovado: { bg: '#dcfce7', color: '#166534', icone: '\u2705', texto: 'Aprovado \u2713' },
    recusado: { bg: '#fee2e2', color: '#991b1b', icone: '\u274C', texto: 'Recusado' },
    expirado: { bg: '#f3f4f6', color: '#6b7280', icone: '\u231B', texto: 'Expirado' },
  };

  var FORMA_LABELS = {
    pix: 'PIX', a_vista: '\u00C0 vista', '2x': '2x', '3x': '3x', '4x': '4x',
  };

  var badge = STATUS_BADGE[orc.status] || STATUS_BADGE.rascunho;

  function getMetodoLabel(metodo) {
    var map = {
      pix: 'PIX',
      dinheiro: 'Dinheiro',
      cartao: 'Cartao',
      boleto: 'Boleto',
      transferencia: 'Transferencia',
      na_execucao: 'Na execucao',
      na_entrega: 'Na entrega',
      outro: 'Outro',
    };
    return map[metodo] || metodo || '-';
  }

  function normStatusConta(s) {
    return (s || '').toString().toLowerCase().trim();
  }

  /** Entrada/sinal confirmada: prioriza contas_financeiras_publico, depois pagamentos_financeiros. */
  function entradaEstaPaga(orcamento) {
    var contas = Array.isArray(orcamento.contas_financeiras_publico)
      ? orcamento.contas_financeiras_publico
      : [];
    var porConta = contas.some(function(c) {
      if (!c) return false;
      var tl = (c.tipo_lancamento || '').toLowerCase();
      if (tl !== 'entrada') return false;
      return normStatusConta(c.status) === 'pago';
    });
    if (porConta) return true;

    var pags = Array.isArray(orcamento.pagamentos_financeiros)
      ? orcamento.pagamentos_financeiros
      : [];
    return pags.some(function(p) {
      if (!p) return false;
      var tipo = (p.tipo || '').toLowerCase();
      var okTipo = tipo === 'sinal' || tipo === 'entrada';
      return okTipo && normStatusConta(p.status) === 'confirmado';
    });
  }

  function fmtVencConta(d) {
    if (!d) return '\u2014';
    var s = String(d).slice(0, 10);
    if (s.length >= 10) return s.split('-').reverse().join('/');
    return fmtData(d);
  }

  function badgeContaStatus(st) {
    var n = normStatusConta(st);
    if (n === 'pago') {
      return { bg: '#d1fae5', color: '#065f46', label: 'Pago' };
    }
    if (n === 'pendente') {
      return { bg: '#dbeafe', color: '#1d4ed8', label: 'Pendente' };
    }
    if (n === 'vencido') {
      return { bg: '#fee2e2', color: '#991b1b', label: 'Vencido' };
    }
    if (n === 'parcial') {
      return { bg: '#fef3c7', color: '#92400e', label: 'Parcial' };
    }
    if (n === 'cancelado') {
      return { bg: '#f3f4f6', color: '#6b7280', label: 'Cancelado' };
    }
    return { bg: '#f3f4f6', color: '#374151', label: st ? String(st).charAt(0).toUpperCase() + String(st).slice(1) : '\u2014' };
  }

  function rotuloLinhaConta(c, metodoEntrada, metodoSaldo) {
    var tl = (c.tipo_lancamento || '').toLowerCase();
    var me = (metodoEntrada || 'pix').toLowerCase();
    var ms = (metodoSaldo || 'pix').toLowerCase();
    if (tl === 'entrada') {
      return '\ud83d\udd11 Entrada ' + getMetodoLabel(me);
    }
    if (tl === 'saldo') {
      return '\ud83d\udcb0 Saldo ' + getMetodoLabel(ms);
    }
    if (tl === 'integral') {
      return '\ud83d\udccb Pagamento unico';
    }
    return escHtml(c.descricao || '\u2014');
  }

  function montarContasGeradasHtml(orcamento, corPrimaria) {
    var contas = Array.isArray(orcamento.contas_financeiras_publico)
      ? orcamento.contas_financeiras_publico.slice()
      : [];
    var metEnt = (orcamento.regra_entrada_metodo || 'pix').toString();
    var metSal = (orcamento.regra_saldo_metodo || 'pix').toString();

    contas.sort(function(a, b) {
      var order = { saldo: 0, entrada: 1, integral: 2 };
      var oa = order[(a.tipo_lancamento || '').toLowerCase()];
      var ob = order[(b.tipo_lancamento || '').toLowerCase()];
      oa = oa === undefined ? 9 : oa;
      ob = ob === undefined ? 9 : ob;
      return oa - ob;
    });

    var total = Number(orcamento.total || 0);
    var pags = Array.isArray(orcamento.pagamentos_financeiros)
      ? orcamento.pagamentos_financeiros
      : [];
    var pago = pags
      .filter(function(p) {
        return p && normStatusConta(p.status) === 'confirmado';
      })
      .reduce(function(sum, p) {
        return sum + Number(p.valor || 0);
      }, 0);
    var saldoDev = Math.max(total - pago, 0);
    var pct = total > 0 ? Math.round((pago / total) * 100) : 0;

    var linhasHtml = '';
    if (contas.length > 0) {
      linhasHtml = contas
        .map(function(c) {
          var badge = badgeContaStatus(c.status);
          var rotulo = rotuloLinhaConta(c, metEnt, metSal);
          var venc = fmtVencConta(c.data_vencimento);
          return (
            '<div style="display:flex;align-items:center;gap:10px;font-size:13px;padding:10px 0;border-bottom:1px solid #f1f5f9;flex-wrap:wrap">' +
              '<span style="flex:1;min-width:120px;font-weight:600;color:#374151">' +
                rotulo +
              '</span>' +
              '<span style="color:#9ca3af;font-size:12px">vence ' + escHtml(venc) + '</span>' +
              '<span style="font-weight:700;color:#111;min-width:88px;text-align:right">' +
                fmtMoeda(c.valor) +
              '</span>' +
              '<span style="padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;background:' +
                badge.bg +
                ';color:' +
                badge.color +
                '">' +
                escHtml(badge.label) +
              '</span>' +
            '</div>'
          );
        })
        .join('');
    } else if (pags.length > 0) {
      linhasHtml = pags
        .map(function(p) {
          var conf = normStatusConta(p.status) === 'confirmado';
          var nomeForma = p.forma_pagamento_nome || 'PIX';
          var dataStr = p.data_pagamento
            ? String(p.data_pagamento).slice(0, 10).split('-').reverse().join('/')
            : '\u2014';
          return (
            '<div style="display:flex;align-items:center;gap:10px;font-size:13px;padding:10px 0;border-bottom:1px solid #f1f5f9;opacity:' +
              (conf ? '1' : '0.55') +
              '">' +
              '<span style="flex:1;font-weight:600;color:#374151">' +
                escHtml((p.tipo || '').charAt(0).toUpperCase() + (p.tipo || '').slice(1)) +
                ' \u2014 ' +
                fmtMoeda(p.valor) +
                ' <span style="font-weight:400;color:#9ca3af">\u2022 ' +
                escHtml(nomeForma) +
                '</span>' +
              '</span>' +
              '<span style="color:#9ca3af;font-size:12px">' +
                escHtml(dataStr) +
              '</span>' +
            '</div>'
          );
        })
        .join('');
      if (saldoDev > 0) {
        linhasHtml +=
          '<div style="display:flex;align-items:center;gap:10px;font-size:13px;padding:10px 0;opacity:0.65">' +
            '<span style="flex:1;font-weight:600;color:#374151">Saldo pendente</span>' +
            '<span style="font-weight:700">' +
              fmtMoeda(saldoDev) +
            '</span>' +
          '</div>';
      }
    } else {
      return '';
    }

    return (
      '<div style="background:white;border-radius:16px;box-shadow:0 4px 15px rgba(0,0,0,0.06);padding:18px 20px;margin:20px 0;border:1px solid #e5e7eb">' +
        '<p style="font-size:11px;color:#64748b;font-weight:700;margin:0 0 14px 0;letter-spacing:0.06em;text-transform:uppercase">Contas geradas na aprovacao</p>' +
        linhasHtml +
        '<div style="margin-top:14px;padding-top:14px;border-top:1px solid #f1f5f9">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;color:#64748b;margin-bottom:8px;flex-wrap:wrap;gap:8px">' +
            '<span>' +
              fmtMoeda(pago) +
              ' de ' +
              fmtMoeda(total) +
              ' \u00b7 ' +
              pct +
              '% pago' +
            '</span>' +
            '<span style="font-weight:700;color:' +
              (saldoDev > 0 ? '#ea580c' : '#10b981') +
              '">' +
              (saldoDev > 0 ? 'Saldo: ' + fmtMoeda(saldoDev) : 'Quitado') +
            '</span>' +
          '</div>' +
          '<div style="background:rgba(0,0,0,0.08);border-radius:99px;height:8px;overflow:hidden">' +
            '<div style="height:100%;border-radius:99px;width:' +
              pct +
              '%;background:' +
              (corPrimaria || '#00e5a0') +
              ';transition:width .4s ease"></div>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  // Itens HTML
  var itensHtml = '';
  if (itens.length === 0) {
    itensHtml = '<tr><td colspan="4" style="padding:20px;text-align:center;color:#94a3b8">Nenhum item.</td></tr>';
  } else {
    itensHtml = itens.map(function(item, idx) {
      var qNum = Number(item.quantidade);
      var qtd = (Number.isFinite(qNum) && qNum === Math.floor(qNum)) ? String(Math.floor(qNum)) : (Number.isFinite(qNum) ? qNum.toFixed(2) : '0');
      var bg = idx % 2 === 0 ? '#ffffff' : '#fafbfc';
      return '<tr style="background:' + bg + '">' +
        '<td style="padding:14px 20px;border-bottom:1px solid #f1f5f9">' + escHtml(item.descricao) + '</td>' +
        '<td style="padding:14px 20px;border-bottom:1px solid #f1f5f9;text-align:center">' + qtd + '</td>' +
        '<td style="padding:14px 20px;border-bottom:1px solid #f1f5f9">' + fmtMoeda(item.valor_unit) + '</td>' +
        '<td style="padding:14px 20px;border-bottom:1px solid #f1f5f9;font-weight:600">' + fmtMoeda(item.total) + '</td>' +
      '</tr>';
    }).join('');
  }

  // Tfoot (subtotal/desconto)
  var tfootHtml = '';
  if (desc > 0) {
    var descVal = descTipo === 'percentual' ? subtotal * desc / 100 : desc;
    var descLabel = descTipo === 'percentual' ? 'Desconto (' + desc + '%)' : 'Desconto';
    tfootHtml =
      '<tr><td colspan="3" style="padding:12px 20px;text-align:right;color:#64748b;font-size:14px">Subtotal</td>' +
      '<td style="padding:12px 20px;font-weight:600;color:#64748b">' + fmtMoeda(subtotal) + '</td></tr>' +
      '<tr><td colspan="3" style="padding:12px 20px;text-align:right;color:#ef4444;font-size:14px">' + escHtml(descLabel) + '</td>' +
      '<td style="padding:12px 20px;font-weight:600;color:#ef4444">- ' + fmtMoeda(descVal) + '</td></tr>';
  }

  // Observações
  var obsHtml = '';
  if (orc.observacoes) {
    obsHtml =
      '<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:12px;padding:18px;margin-bottom:24px">' +
        '<h3 style="font-size:14px;color:#92400e;margin-bottom:6px;font-weight:700">Observa\u00e7\u00f5es</h3>' +
        '<p style="color:#78350f;font-size:14px;line-height:1.6">' + escHtml(orc.observacoes) + '</p>' +
      '</div>';
  }

  // Botões de ação
  var acoesHtml = '';
  if (orc.status === 'enviado' && !aceiteJaRegistrado) {
    acoesHtml =
      '<button id="btn-aceitar" style="width:100%;background:' + cor + ';color:white;font-weight:700;padding:16px;border:none;border-radius:12px;font-size:16px;cursor:pointer;box-shadow:0 4px 15px ' + cor + '44;transition:transform .15s" onmouseover="this.style.transform=\'scale(1.02)\'" onmouseout="this.style.transform=\'scale(1)\'">' +
        '\u2705 Aceitar este or\u00e7amento' +
      '</button>' +
      '<button id="btn-ajuste" style="width:100%;background:white;color:#374151;font-weight:600;padding:14px;border:1px solid #e2e8f0;border-radius:12px;font-size:15px;cursor:pointer;transition:background .15s" onmouseover="this.style.background=\'#f8fafc\'" onmouseout="this.style.background=\'white\'">' +
        '\u270F\uFE0F Solicitar ajuste' +
      '</button>' +
      '<button id="btn-recusar" style="width:100%;background:white;color:#dc2626;font-weight:600;padding:14px;border:1px solid #fecaca;border-radius:12px;font-size:15px;cursor:pointer;transition:background .15s" onmouseover="this.style.background=\'#fef2f2\'" onmouseout="this.style.background=\'white\'">' +
        '\u2715 Recusar proposta' +
      '</button>';
  }

  // Card de aceite já registrado
  var aceiteHtml = '';
  if (aceiteJaRegistrado) {
    aceiteHtml =
      '<div id="card-aceite" style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:18px;margin-bottom:24px">' +
        '<div style="display:flex;align-items:center;gap:12px">' +
          '<span style="font-size:28px">\u2705</span>' +
          '<div>' +
            '<p style="font-weight:700;color:#166534;font-size:15px">Or\u00e7amento aceito!</p>' +
            '<p style="color:#15803d;font-size:13px;margin-top:2px">Aceite registrado por: <strong id="aceite-nome">' + escHtml(orc.aceite_nome) + '</strong></p>' +
            '<p style="color:#16a34a;font-size:12px" id="aceite-em">Em ' + fmtData(orc.aceite_em) + '</p>' +
          '</div>' +
        '</div>' +
        (orc.aceite_mensagem
          ? '<div id="aceite-msg-wrap" style="margin-top:12px;padding-top:12px;border-top:1px solid #bbf7d0"><p style="font-size:12px;color:#15803d;font-weight:600;margin-bottom:4px">Mensagem enviada:</p><p id="aceite-msg-texto" style="font-size:13px;color:#166534;font-style:italic">' + escHtml(orc.aceite_mensagem) + '</p></div>'
          : '') +
      '</div>';
  }

  // Card de recusa
  var recusaHtml = '';
  if (orc.status === 'recusado') {
    recusaHtml =
      '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:12px;padding:18px;margin-bottom:24px">' +
        '<div style="display:flex;align-items:center;gap:12px">' +
          '<span style="font-size:28px">\u274C</span>' +
          '<div>' +
            '<p style="font-weight:700;color:#991b1b;font-size:15px">Or\u00e7amento recusado</p>' +
            '<p style="color:#b91c1c;font-size:13px;margin-top:2px">O cliente optou por n\u00e3o aceitar esta proposta.</p>' +
          '</div>' +
        '</div>' +
        (orc.recusa_motivo
          ? '<div style="margin-top:12px;padding-top:12px;border-top:1px solid #fecaca"><p style="font-size:12px;color:#991b1b;font-weight:600;margin-bottom:4px">Motivo informado:</p><p style="font-size:13px;color:#7f1d1d;font-style:italic">' + escHtml(orc.recusa_motivo) + '</p></div>'
          : '') +
      '</div>';
  }

  // Card expirado
  var expiradoHtml = '';
  if (orc.status === 'expirado') {
    expiradoHtml =
      '<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:12px;padding:18px;margin-bottom:24px">' +
        '<div style="display:flex;align-items:center;gap:12px">' +
          '<span style="font-size:28px">\u231B</span>' +
          '<div>' +
            '<p style="font-weight:700;color:#374151;font-size:15px">Or\u00e7amento expirado</p>' +
            '<p style="color:#6b7280;font-size:13px;margin-top:2px">O prazo de validade desta proposta se encerrou. Entre em contato com a empresa para solicitar um novo or\u00e7amento.</p>' +
          '</div>' +
        '</div>' +
      '</div>';
  }

  // WhatsApp link
  var telWhatsapp = emp.telefone_operador || emp.telefone;
  var linkWa = whatsappLink(telWhatsapp);
  var mostrarBotaoWa = emp.mostrar_botao_whatsapp !== false;
  var waBtnHtml = '';
  if (linkWa && mostrarBotaoWa) {
    waBtnHtml =
      '<a href="' + linkWa + '" target="_blank" rel="noopener" style="display:flex;align-items:center;justify-content:center;gap:10px;width:100%;background:' + cor + ';color:white;font-weight:700;padding:16px;border-radius:12px;font-size:16px;text-decoration:none;box-shadow:0 4px 15px ' + cor + '44;transition:transform .15s;box-sizing:border-box" onmouseover="this.style.transform=\'scale(1.02)\'" onmouseout="this.style.transform=\'scale(1)\'">' +
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>' +
        'Tirar d\u00favidas pelo WhatsApp' +
      '</a>';
  }

  // Sobre empresa
  var descricaoSobre = (emp.descricao_publica_empresa && emp.descricao_publica_empresa.trim())
    ? emp.descricao_publica_empresa.trim()
    : 'Profissional comprometido com qualidade e prazo. Este or\u00e7amento foi elaborado com aten\u00e7\u00e3o aos detalhes para atender sua necessidade.';
  var logoUrlSobre = (typeof api !== 'undefined' && emp.logo_url) ? api.resolveUrl(emp.logo_url) : (emp.logo_url || '');
  var logoSobreHtml = '';
  if (logoUrlSobre) {
    logoSobreHtml = '<img src="' + escHtml(logoUrlSobre) + '" alt="' + escHtml(emp.nome || 'Logo') + '" style="width:64px;height:64px;object-fit:contain;border-radius:12px;border:1px solid #f1f5f9;flex-shrink:0" onerror="this.style.display=\'none\'">';
  }

  // Assinatura
  var labelAssinatura = (emp.texto_assinatura_proposta && emp.texto_assinatura_proposta.trim())
    ? emp.texto_assinatura_proposta.trim()
    : 'Proposta elaborada por';

  var contasGeradasHtml = '';
  var entradaPaga = false;
  if (orc.status === 'aprovado') {
    entradaPaga = entradaEstaPaga(orc);
    contasGeradasHtml = montarContasGeradasHtml(orc, cor);
  }

  var pagamentoHtml = '';
  if (orc.status === 'aprovado') {
    var total = Number(orc.total || 0);
    var valorSinalPix = Number(orc.valor_sinal_pix || 0);
    var temSinalPix = Number.isFinite(valorSinalPix) && valorSinalPix > 0;
    var mostrarQrSinal = !!(orc.pix_chave && temSinalPix && !entradaPaga);
    var entradaPct = Number(orc.regra_entrada_percentual || 0);
    var saldoPct = Number(orc.regra_saldo_percentual || 0);
    var valorEntrada = total * entradaPct / 100;
    var valorSaldo = total * saldoPct / 100;
    var pagamentos = Array.isArray(orc.pagamentos_financeiros) ? orc.pagamentos_financeiros : [];
    var pago = pagamentos
      .filter(function(p){ return p && p.status === 'confirmado'; })
      .reduce(function(sum, p){ return sum + Number(p.valor || 0); }, 0);
    var saldoAtual = Math.max(total - pago, 0);

    pagamentoHtml =
      '<div style="background:white;border-radius:16px;box-shadow:0 4px 15px rgba(0,0,0,0.08);padding:20px;margin:20px 0;border:1px solid #f1f5f9">' +
        '<p style="font-size:12px;color:#64748b;font-weight:700;margin-bottom:10px;text-transform:uppercase;letter-spacing:.04em">Pagamento</p>' +
        '<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px">' +
          '<div style="background:#f8fafc;border-radius:10px;padding:12px"><p style="font-size:11px;color:#64748b">Forma principal</p><p style="font-size:14px;font-weight:700;color:#1f2937;margin-top:3px">' + escHtml(FORMA_LABELS[orc.forma_pagamento] || orc.forma_pagamento || 'PIX') + '</p></div>' +
          '<div style="background:#f8fafc;border-radius:10px;padding:12px"><p style="font-size:11px;color:#64748b">Pago ate agora</p><p style="font-size:14px;font-weight:700;color:#166534;margin-top:3px">' + fmtMoeda(pago) + '</p></div>' +
          '<div style="background:#f8fafc;border-radius:10px;padding:12px"><p style="font-size:11px;color:#64748b">Entrada</p><p style="font-size:14px;font-weight:700;color:#1f2937;margin-top:3px">' + (entradaPct > 0 ? fmtMoeda(valorEntrada) + ' (' + entradaPct + '%)' : 'Nao configurada') + '</p></div>' +
          '<div style="background:#f8fafc;border-radius:10px;padding:12px"><p style="font-size:11px;color:#64748b">Saldo restante</p><p style="font-size:14px;font-weight:700;color:#ea580c;margin-top:3px">' + fmtMoeda(saldoAtual) + '</p></div>' +
        '</div>' +
        ((entradaPct > 0 || saldoPct > 0)
          ? '<div style="margin-top:12px;padding-top:12px;border-top:1px dashed #e2e8f0;font-size:13px;color:#475569;line-height:1.6">' +
              (entradaPct > 0 ? '<div><strong>Entrada:</strong> ' + getMetodoLabel(orc.regra_entrada_metodo) + '</div>' : '') +
              (saldoPct > 0 ? '<div><strong>Saldo:</strong> ' + getMetodoLabel(orc.regra_saldo_metodo) + '</div>' : '') +
            '</div>'
          : '') +
        (orc.pix_chave
          ? '<div style="margin-top:12px;padding:12px;background:#ecfeff;border:1px solid #a5f3fc;border-radius:10px">' +
              '<p style="font-size:12px;color:#0f766e;font-weight:700;margin-bottom:8px">PIX disponivel</p>' +
              '<p style="font-size:12px;color:#155e75"><strong>Titular:</strong> ' + escHtml(orc.pix_titular || '-') + '</p>' +
              '<p style="font-size:12px;color:#155e75"><strong>Chave:</strong> ' + escHtml(orc.pix_chave) + '</p>' +
              (mostrarQrSinal
                ? '<div style="margin-top:10px;background:#fff;border:1px solid #bae6fd;border-radius:10px;padding:10px">' +
                    '<p style="font-size:11px;color:#64748b;margin:0 0 8px 0;text-align:center">QR do sinal (' + fmtMoeda(valorSinalPix) + ')</p>' +
                    '<div style="display:flex;justify-content:center">' +
                      '<img id="moderno-pix-inicial-qr" src="" alt="QR Code PIX sinal" style="width:170px;height:170px;object-fit:contain;display:block">' +
                    '</div>' +
                  '</div>'
                : (entradaPaga
                ? '<p style="margin-top:10px;font-size:12px;color:#065f46;font-weight:600">' +
                    '\u2713 Sinal/entrada confirmado pela empresa. O QR acima foi ocultado.' +
                    (saldoAtual > 0 ? ' Use o botao abaixo para pagar o saldo restante.' : '') +
                  '</p>'
                : (!temSinalPix && orc.pix_qrcode
                ? '<div style="margin-top:10px;background:#fff;border:1px solid #bae6fd;border-radius:10px;padding:10px;display:flex;justify-content:center">' +
                    '<img src="data:image/png;base64,' + escHtml(orc.pix_qrcode) + '" alt="QR Code PIX" style="width:170px;height:170px;object-fit:contain;display:block">' +
                  '</div>'
                : (!temSinalPix
                ? '<p style="margin-top:8px;font-size:11px;color:#0e7490">QR Code indisponivel no momento. Utilize a chave PIX acima.</p>'
                : '')))) +
            '</div>'
          : '') +
        ((saldoAtual > 0 && orc.pix_chave)
          ? '<button id="moderno-fin-btn-pix-saldo" style="width:100%;margin-top:12px;background:' + cor + ';color:white;font-weight:700;padding:12px;border:none;border-radius:10px;cursor:pointer;font-size:14px">💳 Pagar Saldo ' + fmtMoeda(saldoAtual) + ' via PIX</button>' +
            '<div id="moderno-fin-pix-saldo-card" style="display:none;margin-top:12px;padding:12px;background:#f8fafc;border:1px solid #dbeafe;border-radius:10px">' +
              '<div style="display:flex;flex-direction:column;align-items:center">' +
                '<div style="padding:8px;background:#fff;border:1px solid #bae6fd;border-radius:10px;margin-bottom:8px">' +
                  '<img id="moderno-fin-pix-saldo-qr" src="" alt="QR Code PIX saldo" style="width:150px;height:150px;object-fit:contain;display:block">' +
                '</div>' +
                '<p style="font-size:12px;color:#64748b;margin:0">Valor do saldo</p>' +
                '<p id="moderno-fin-pix-saldo-valor" style="font-size:20px;font-weight:700;color:' + cor + ';margin:4px 0 10px 0"></p>' +
                '<button id="moderno-fin-pix-saldo-copiar" style="width:100%;background:' + cor + ';color:white;font-weight:700;padding:10px;border:none;border-radius:8px;cursor:pointer;font-size:13px">📋 Copiar Codigo PIX</button>' +
                '<p id="moderno-fin-pix-copiado" style="display:none;font-size:11px;color:#10b981;font-weight:700;margin-top:8px">✓ Codigo copiado!</p>' +
              '</div>' +
            '</div>'
          : '') +
      '</div>';
  }

  var proximosPassosHtml = '';
  if (orc.status === 'aprovado') {
    proximosPassosHtml =
      '<div style="background:white;border-radius:16px;box-shadow:0 4px 15px rgba(0,0,0,0.08);padding:20px;margin:20px 0;border:1px solid #f1f5f9">' +
        '<p style="font-size:12px;color:#64748b;font-weight:700;margin-bottom:10px;text-transform:uppercase;letter-spacing:.04em">Proximos passos</p>' +
        '<div style="display:flex;flex-direction:column;gap:8px">' +
          '<div style="display:flex;align-items:center;gap:8px;font-size:13px;color:#334155"><span style="width:8px;height:8px;border-radius:999px;background:#22c55e;display:inline-block"></span>Notificacao enviada ao responsavel</div>' +
          '<div style="display:flex;align-items:center;gap:8px;font-size:13px;color:#334155"><span style="width:8px;height:8px;border-radius:999px;background:#94a3b8;display:inline-block"></span>Agendamento no cronograma da equipe</div>' +
          '<div style="display:flex;align-items:center;gap:8px;font-size:13px;color:#334155"><span style="width:8px;height:8px;border-radius:999px;background:#94a3b8;display:inline-block"></span>Inicio da execucao do servico/entrega</div>' +
        '</div>' +
      '</div>';
  }

  var conteudo =
    '<style>' +
      '@media(max-width:600px){' +
        '.info-grid-mp{grid-template-columns:1fr !important}' +
        '.moderno-actions button,.moderno-actions a{font-size:14px !important;padding:12px !important}' +
      '}' +
    '</style>' +
    '<div style="max-width:900px;margin:0 auto;padding:16px">' +

      // Header
      '<header style="background:white;padding:24px 20px;border-radius:16px;box-shadow:0 4px 15px rgba(0,0,0,0.08);margin-bottom:24px;text-align:center">' +
        '<div style="font-size:32px;font-weight:700;color:' + cor + ';margin-bottom:8px">' + escHtml(emp.nome || 'Empresa') + '</div>' +
        '<h1 style="font-size:18px;color:#334155;margin:8px 0">Or\u00e7amento N\u00BA ' + escHtml(orc.numero || '\u2014') + '</h1>' +
        '<div id="badge-status" style="display:inline-flex;align-items:center;gap:8px;padding:10px 20px;border-radius:9999px;font-weight:600;margin:12px 0;font-size:15px;background:' + badge.bg + ';color:' + badge.color + '">' +
          badge.icone + ' ' + badge.texto +
        '</div>' +
        '<p style="color:#64748b;font-size:14px"><strong>Cliente:</strong> ' + escHtml((orc.cliente && orc.cliente.nome) || '\u2014') + '</p>' +
      '</header>' +

      // Info cards
      '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:32px" class="info-grid-mp">' +
        '<div style="background:white;padding:18px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.06)">' +
          '<h3 style="font-size:14px;color:#64748b;margin-bottom:6px">Data de Emiss\u00e3o</h3>' +
          '<p style="font-weight:600;font-size:15.5px">' + fmtData(orc.criado_em) + '</p>' +
        '</div>' +
        '<div style="background:white;padding:18px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.06)">' +
          '<h3 style="font-size:14px;color:#64748b;margin-bottom:6px">Validade</h3>' +
          '<p style="font-weight:600;font-size:15.5px">' + dataVencimento(orc.criado_em, orc.validade_dias) + '</p>' +
        '</div>' +
        '<div style="background:white;padding:18px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.06)">' +
          '<h3 style="font-size:14px;color:#64748b;margin-bottom:6px">Forma de Pagamento</h3>' +
          '<p style="font-weight:600;font-size:15.5px">' + escHtml(FORMA_LABELS[orc.forma_pagamento] || orc.forma_pagamento || 'PIX') + '</p>' +
        '</div>' +
      '</div>' +

      // Tabela de itens
      '<div style="background:white;border-radius:16px;overflow:hidden;box-shadow:0 4px 15px rgba(0,0,0,0.08);margin-bottom:32px">' +
        '<table style="width:100%;border-collapse:collapse">' +
          '<thead>' +
            '<tr>' +
              '<th style="background:#f1f5f9;padding:16px 20px;text-align:left;font-weight:600;color:#334155">Descri\u00e7\u00e3o</th>' +
              '<th style="background:#f1f5f9;padding:16px 20px;text-align:center;font-weight:600;color:#334155">Qtd</th>' +
              '<th style="background:#f1f5f9;padding:16px 20px;text-align:left;font-weight:600;color:#334155">Valor Unit.</th>' +
              '<th style="background:#f1f5f9;padding:16px 20px;text-align:left;font-weight:600;color:#334155">Total</th>' +
            '</tr>' +
          '</thead>' +
          '<tbody>' + itensHtml + '</tbody>' +
          '<tfoot>' + tfootHtml + '</tfoot>' +
        '</table>' +
      '</div>' +

      // Total grande
      '<div style="font-size:2.1em;font-weight:700;color:' + cor + ';text-align:center;margin:24px 0">' +
        fmtMoeda(orc.total) +
      '</div>' +

      // Observações
      obsHtml +

      // Aceite / Recusa / Expirado
      aceiteHtml + recusaHtml + expiradoHtml +
      contasGeradasHtml +
      pagamentoHtml +
      proximosPassosHtml +

      '<div id="timeline-container"></div>' +

      // Botões de ação
      '<div style="display:flex;flex-direction:column;gap:14px;margin:32px 0" class="moderno-actions">' +
        acoesHtml +
      '</div>' +

      // WhatsApp e PDF
      '<div style="display:flex;flex-direction:column;gap:14px;margin:24px 0" class="moderno-actions">' +
        waBtnHtml +
        '<a href="' + API + '/api/v1/o/' + token + '/pdf" target="_blank" style="display:flex;align-items:center;justify-content:center;gap:8px;width:100%;background:white;color:#374151;font-weight:600;padding:14px;border:1px solid #e2e8f0;border-radius:12px;font-size:15px;text-decoration:none;transition:background .15s;box-sizing:border-box" onmouseover="this.style.background=\'#f8fafc\'" onmouseout="this.style.background=\'white\'">' +
          '\uD83D\uDCC4 Baixar PDF' +
        '</a>' +
      '</div>' +

      // Sobre a empresa
      '<div style="background:white;border-radius:16px;box-shadow:0 2px 8px rgba(0,0,0,0.06);padding:20px;margin:32px 0">' +
        '<p style="font-size:14px;color:#64748b;font-weight:700;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.04em">Sobre a empresa</p>' +
        '<div style="display:flex;align-items:flex-start;gap:16px">' +
          logoSobreHtml +
          '<div style="min-width:0;flex:1">' +
            '<p style="font-weight:700;color:#111827;font-size:17px">' + escHtml(emp.nome || 'Empresa') + '</p>' +
            '<p style="color:#4b5563;font-size:14px;margin-top:6px;line-height:1.6">' + escHtml(descricaoSobre) + '</p>' +
          '</div>' +
        '</div>' +
      '</div>' +

      // Assinatura
      '<div style="background:#f9fafb;border-radius:12px;border:1px solid #f1f5f9;padding:16px;display:flex;align-items:center;gap:14px;margin:24px 0">' +
        (logoUrlSobre ? '<img src="' + escHtml(logoUrlSobre) + '" alt="' + escHtml(emp.nome || 'Logo') + '" style="width:48px;height:48px;object-fit:contain;border-radius:8px;flex-shrink:0" onerror="this.style.display=\'none\'">' : '') +
        '<div style="min-width:0;flex:1">' +
          '<p style="font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:0.04em;font-weight:600">' + escHtml(labelAssinatura) + '</p>' +
          '<p style="font-weight:700;color:#1f2937;margin-top:2px">' + escHtml(emp.nome || 'Empresa') + '</p>' +
          (linkWa ? '<a href="' + linkWa + '" target="_blank" rel="noopener" style="font-size:13px;font-weight:500;margin-top:4px;display:inline-flex;align-items:center;gap:4px;color:' + cor + ';text-decoration:none">Fale conosco pelo WhatsApp \u2192</a>' : '') +
        '</div>' +
      '</div>' +

      // Footer
      '<footer style="text-align:center;color:#64748b;font-size:14px;margin-top:40px;padding:0 16px">' +
        '<p>Or\u00e7amento gerado por <strong>COTTE</strong></p>' +
        '<p>Qualquer d\u00favidas, \u00e9 s\u00f3 chamar no WhatsApp.</p>' +
      '</footer>' +

    '</div>';

  // Injetar no DOM
  var container = document.getElementById('conteudo');
  if (!container) return;
  container.innerHTML = conteudo;

  // Configurar event listeners para botões de ação
  var btnAceitar = document.getElementById('btn-aceitar');
  if (btnAceitar) {
    btnAceitar.addEventListener('click', function() {
      if (typeof abrirModalAceite === 'function') abrirModalAceite();
    });
  }

  var btnAjuste = document.getElementById('btn-ajuste');
  if (btnAjuste) {
    btnAjuste.addEventListener('click', function() {
      if (typeof abrirModalAjuste === 'function') abrirModalAjuste();
    });
  }

  var btnRecusar = document.getElementById('btn-recusar');
  if (btnRecusar) {
    btnRecusar.addEventListener('click', function() {
      if (typeof abrirModalRecusa === 'function') abrirModalRecusa();
    });
  }

  var imgQrInicial = document.getElementById('moderno-pix-inicial-qr');
  if (imgQrInicial && orc.pix_chave && !entradaPaga) {
    var valorSinal = Number(orc.valor_sinal_pix || 0);
    if (Number.isFinite(valorSinal) && valorSinal > 0) {
      fetch(API + '/api/v1/o/' + token + '/pix/gerar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ valor: valorSinal }),
      })
      .then(function(res) {
        if (!res.ok) throw new Error('Falha ao gerar QR do sinal');
        return res.json();
      })
      .then(function(data) {
        if (data && data.qrcode) {
          imgQrInicial.src = 'data:image/png;base64,' + data.qrcode;
        } else if (orc.pix_qrcode) {
          imgQrInicial.src = 'data:image/png;base64,' + orc.pix_qrcode;
        }
      })
      .catch(function() {
        if (orc.pix_qrcode) {
          imgQrInicial.src = 'data:image/png;base64,' + orc.pix_qrcode;
        }
      });
    }
  }

  var btnPixSaldo = document.getElementById('moderno-fin-btn-pix-saldo');
  if (btnPixSaldo) {
    btnPixSaldo.addEventListener('click', async function() {
      var valorTotal = Number(orc.total || 0);
      var pagamentos = Array.isArray(orc.pagamentos_financeiros) ? orc.pagamentos_financeiros : [];
      var valorPago = pagamentos
        .filter(function(p){ return p && p.status === 'confirmado'; })
        .reduce(function(sum, p){ return sum + Number(p.valor || 0); }, 0);
      var saldo = Math.max(valorTotal - valorPago, 0);
      if (saldo <= 0) return;

      var textoOriginal = btnPixSaldo.textContent;
      btnPixSaldo.disabled = true;
      btnPixSaldo.textContent = 'Gerando QR Code...';

      try {
        var res = await fetch(API + '/api/v1/o/' + token + '/pix/gerar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ valor: saldo }),
        });
        if (!res.ok) throw new Error('Erro ao gerar PIX do saldo.');
        var data = await res.json();

        var qrEl = document.getElementById('moderno-fin-pix-saldo-qr');
        var valorEl = document.getElementById('moderno-fin-pix-saldo-valor');
        var cardEl = document.getElementById('moderno-fin-pix-saldo-card');
        var copyBtn = document.getElementById('moderno-fin-pix-saldo-copiar');

        if (qrEl) qrEl.src = 'data:image/png;base64,' + (data.qrcode || '');
        if (valorEl) valorEl.textContent = fmtMoeda(data.valor || saldo);
        if (copyBtn) copyBtn.dataset.payload = data.payload || '';
        if (cardEl) cardEl.style.display = '';

        btnPixSaldo.textContent = '🔄 Atualizar QR do saldo';
      } catch (_e) {
        btnPixSaldo.textContent = textoOriginal;
      } finally {
        btnPixSaldo.disabled = false;
      }
    });
  }

  var btnCopiarSaldo = document.getElementById('moderno-fin-pix-saldo-copiar');
  if (btnCopiarSaldo) {
    btnCopiarSaldo.addEventListener('click', function() {
      var payload = btnCopiarSaldo.dataset.payload || '';
      if (!payload) return;
      var feedbackEl = document.getElementById('moderno-fin-pix-copiado');

      navigator.clipboard.writeText(payload).then(function() {
        if (!feedbackEl) return;
        feedbackEl.style.display = '';
        setTimeout(function() { feedbackEl.style.display = 'none'; }, 2500);
      }).catch(function() {
        var ta = document.createElement('textarea');
        ta.value = payload;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        if (!feedbackEl) return;
        feedbackEl.style.display = '';
        setTimeout(function() { feedbackEl.style.display = 'none'; }, 2500);
      });
    });
  }
}
