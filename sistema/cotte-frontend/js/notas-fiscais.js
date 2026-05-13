(function NotasFiscaisPage() {
    var LS_VIEW = "cotte_nf_view";
    var VIEW_TABLE = "table";
    var VIEW_CARDS = "cards";

    var TIPO_LABELS = { nfse: "NFS-e", nfe: "NF-e", nfce: "NFC-e" };
    var STATUS_CLASSES = {
        pendente: "badge-warning",
        processando: "badge-info",
        emitida: "badge-success",
        cancelada: "badge-secondary",
        erro: "badge-danger",
    };
    var STATUS_LABELS = {
        pendente: "Pendente",
        processando: "Processando",
        emitida: "Emitida",
        cancelada: "Cancelada",
        erro: "Falha na emissão",
    };

    var ultimasNotas = [];
    var paginaAtual = 1;

    function _escHtml(s) {
        if (s == null || s === "") return "";
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function _fmtDataHora(iso) {
        if (!iso) return "—";
        try {
            return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
        } catch (_) {
            return "—";
        }
    }

    function getViewMode() {
        var v = localStorage.getItem(LS_VIEW);
        return v === VIEW_CARDS ? VIEW_CARDS : VIEW_TABLE;
    }

    function setViewMode(mode) {
        localStorage.setItem(LS_VIEW, mode === VIEW_CARDS ? VIEW_CARDS : VIEW_TABLE);
        _syncViewButtons();
        renderizarNotas(ultimasNotas);
    }

    function _syncViewButtons() {
        var m = getViewMode();
        var bTable = document.getElementById("nf-view-table");
        var bCards = document.getElementById("nf-view-cards");
        if (bTable) {
            bTable.classList.toggle("is-active", m === VIEW_TABLE);
            bTable.setAttribute("aria-pressed", m === VIEW_TABLE ? "true" : "false");
        }
        if (bCards) {
            bCards.classList.toggle("is-active", m === VIEW_CARDS);
            bCards.setAttribute("aria-pressed", m === VIEW_CARDS ? "true" : "false");
        }
    }

    function fecharMenusAcoes() {
        document.querySelectorAll(".nf-actions__menu").forEach(function (menu) {
            menu.hidden = true;
            var wrap = menu.closest(".nf-actions");
            var trig = wrap && wrap.querySelector(".nf-actions__trigger");
            if (trig) trig.setAttribute("aria-expanded", "false");
        });
    }

    function alternarMenuAcoes(btn) {
        var wrap = btn.closest(".nf-actions");
        var menu = wrap && wrap.querySelector(".nf-actions__menu");
        if (!menu) return;
        var willOpen = btn.getAttribute("aria-expanded") !== "true";
        fecharMenusAcoes();
        if (willOpen) {
            menu.hidden = false;
            btn.setAttribute("aria-expanded", "true");
        }
    }

    function _nfMetaRow(label, valueHtml) {
        return '<span class="nf-meta-label">' + _escHtml(label) + '</span><span class="nf-meta-value">' + valueHtml + "</span>";
    }

    function _nfMetaHint(texto) {
        return '<p class="nf-meta-hint">' + _escHtml(texto) + "</p>";
    }

    function _resumirErro(erroMensagem) {
        if (!erroMensagem) return "";
        var raw = String(erroMensagem).trim();
        try {
            var obj = JSON.parse(raw);
            if (obj && typeof obj.error === "string" && obj.error) {
                return obj.error.length > 200 ? obj.error.substring(0, 200) + "…" : obj.error;
            }
            if (obj && typeof obj.message === "string" && obj.message) {
                return obj.message.length > 200 ? obj.message.substring(0, 200) + "…" : obj.message;
            }
        } catch (_) {
            var m = raw.match(/"error"\s*:\s*"((?:[^"\\]|\\.)*)"/);
            if (m && m[1]) {
                var extr = m[1].replace(/\\n/g, "\n").replace(/\\"/g, '"').replace(/\\\\/g, "\\");
                return extr.length > 200 ? extr.substring(0, 200) + "…" : extr;
            }
        }
        return raw.length > 200 ? raw.substring(0, 200) + "…" : raw;
    }

    function _trunc(str, max) {
        var s = str == null ? "" : String(str);
        if (s.length <= max) return s;
        return s.substring(0, max - 1) + "…";
    }

    function _colDataNota(n) {
        var st = n.status || "";
        if (st === "emitida") return _fmtDataHora(n.emitida_em);
        if (st === "cancelada") return n.cancelada_em ? _fmtDataHora(n.cancelada_em) : _fmtDataHora(n.emitida_em);
        return _fmtDataHora(n.criado_em);
    }

    function _numeroHtml(n) {
        if (n.numero) return _escHtml(n.numero);
        if (n.status === "erro") return '— <span class="nf-card__numero-muted">(não emitida)</span>';
        return "—";
    }

    function _orcamentoCell(n) {
        if (!n.orcamento_id) return "—";
        return (
            '<a href="orcamento-view.html?id=' +
            encodeURIComponent(String(n.orcamento_id)) +
            '">#' +
            _escHtml(String(n.orcamento_id)) +
            "</a>"
        );
    }

    function _agruparPorOrcamento(notas) {
        var map = {};
        notas.forEach(function (n) {
            var key = n.orcamento_id != null && n.orcamento_id !== "" ? "o" + String(n.orcamento_id) : "s" + String(n.id);
            if (!map[key]) map[key] = [];
            map[key].push(n);
        });
        var grupos = Object.keys(map).map(function (k) {
            var arr = map[k].slice();
            arr.sort(function (a, b) {
                return new Date(b.criado_em || 0) - new Date(a.criado_em || 0);
            });
            return { key: k, orcamento_id: arr[0].orcamento_id, notas: arr };
        });
        grupos.sort(function (a, b) {
            return new Date(b.notas[0].criado_em || 0) - new Date(a.notas[0].criado_em || 0);
        });
        return grupos;
    }

    function _menuAcoesHtml(n) {
        var id = n.id;
        var items = [];

        if (n.danfe_url) {
            items.push(
                '<a role="menuitem" class="nf-menu-link" href="' +
                    _escHtml(n.danfe_url) +
                    '" target="_blank" rel="noopener noreferrer" onclick="NotasFiscaisPage.fecharMenusAcoes()">DANFE</a>'
            );
        }
        if (n.xml_url) {
            items.push(
                '<a role="menuitem" class="nf-menu-link" href="' +
                    _escHtml(n.xml_url) +
                    '" target="_blank" rel="noopener noreferrer" onclick="NotasFiscaisPage.fecharMenusAcoes()">XML</a>'
            );
        }
        if (n.qr_code) {
            items.push(
                '<a role="menuitem" class="nf-menu-link" href="' +
                    _escHtml(n.qr_code) +
                    '" target="_blank" rel="noopener noreferrer" onclick="NotasFiscaisPage.fecharMenusAcoes()">QR Code</a>'
            );
        }

        if (n.status === "emitida") {
            if (items.length) items.push('<div class="nf-actions__sep" role="separator"></div>');
            items.push(
                '<button type="button" role="menuitem" onclick="NotasFiscaisPage.fecharMenusAcoes();NotasFiscaisPage.sincronizarFocus(' +
                    id +
                    ')">Sincronizar</button>'
            );
            items.push(
                '<button type="button" role="menuitem" onclick="NotasFiscaisPage.fecharMenusAcoes();NotasFiscaisPage.reenviarHook(' +
                    id +
                    ')">Webhook</button>'
            );
            if (n.tipo === "nfe") {
                items.push(
                    '<button type="button" role="menuitem" onclick="NotasFiscaisPage.fecharMenusAcoes();NotasFiscaisPage.cartaCorrecao(' +
                        id +
                        ')">CC-e</button>'
                );
            }
            if (n.orcamento_id && (n.tipo === "nfe" || n.tipo === "nfce")) {
                var tipoPrev = String(n.tipo || "nfe").replace(/'/g, "");
                items.push(
                    '<button type="button" role="menuitem" onclick="NotasFiscaisPage.fecharMenusAcoes();NotasFiscaisPage.previaDanfe(' +
                        n.orcamento_id +
                        ",'" +
                        tipoPrev +
                        '\')">Prévia DANFE</button>'
                );
            }
            items.push('<div class="nf-actions__sep" role="separator"></div>');
            items.push(
                '<button type="button" role="menuitem" class="nf-actions__danger" onclick="NotasFiscaisPage.fecharMenusAcoes();NotasFiscaisPage.cancelar(' +
                    id +
                    ')">Cancelar nota</button>'
            );
        }
        if (n.status === "processando") {
            if (items.length) items.push('<div class="nf-actions__sep" role="separator"></div>');
            items.push(
                '<button type="button" role="menuitem" onclick="NotasFiscaisPage.fecharMenusAcoes();NotasFiscaisPage.sincronizarFocus(' +
                    id +
                    ')">Sincronizar</button>'
            );
        }
        if (n.status === "erro") {
            if (items.length) items.push('<div class="nf-actions__sep" role="separator"></div>');
            items.push(
                '<button type="button" role="menuitem" class="nf-btn-analisar btn-warning" style="background:transparent;border:none;padding:8px 10px;width:100%;text-align:left;font:inherit;color:inherit" onclick="NotasFiscaisPage.fecharMenusAcoes();NotasFiscaisPage.analisarErro(' +
                    id +
                    ')">Analisar e corrigir</button>'
            );
        }

        if (!items.length) {
            return '<span class="nf-muted">—</span>';
        }

        return (
            '<div class="nf-actions">' +
            '<button type="button" class="nf-actions__trigger btn btn-sm btn-secondary" aria-expanded="false" aria-haspopup="true">Ações</button>' +
            '<div class="nf-actions__menu" role="menu" hidden>' +
            items.join("") +
            "</div></div>"
        );
    }

    function _linhaTabelaHtml(n) {
        var nat = n.natureza_operacao || "—";
        var natEsc = _escHtml(nat);
        var natShort = _escHtml(_trunc(nat, 56));
        var erro = n.erro_mensagem ? _resumirErro(n.erro_mensagem) : "";
        var erroCell = erro
            ? '<span class="text-danger" title="' +
              _escHtml(erro) +
              '">' +
              _escHtml(_trunc(erro, 72)) +
              "</span>"
            : "—";

        return (
            '<tr class="nf-row" data-nota-id="' +
            n.id +
            '">' +
            '<td><span class="badge ' +
            (STATUS_CLASSES[n.status] || "") +
            '">' +
            _escHtml(STATUS_LABELS[n.status] || n.status) +
            "</span></td>" +
            '<td>' +
            _escHtml(TIPO_LABELS[n.tipo] || n.tipo) +
            "</td>" +
            '<td class="nf-col-numero">' +
            _numeroHtml(n) +
            "</td>" +
            '<td class="nf-col-natureza"><span class="nf-truncate" title="' +
            natEsc +
            '">' +
            natShort +
            "</span></td>" +
            '<td class="nf-col-orc">' +
            _orcamentoCell(n) +
            "</td>" +
            '<td class="nf-col-data">' +
            _escHtml(_colDataNota(n)) +
            "</td>" +
            '<td class="nf-col-erro" style="max-width:200px;font-size:12px">' +
            erroCell +
            "</td>" +
            "<td>" +
            _menuAcoesHtml(n) +
            "</td></tr>"
        );
    }

    function _theadTabelaHtml() {
        return (
            "<thead><tr>" +
            "<th>Status</th>" +
            "<th>Tipo</th>" +
            "<th>Número</th>" +
            "<th>Natureza</th>" +
            "<th>Orçamento</th>" +
            "<th>Data</th>" +
            "<th>Erro</th>" +
            "<th>Ações</th>" +
            "</tr></thead>"
        );
    }

    function _htmlGrupoErro(g, idx) {
        var latest = g.notas[0];
        var nTent = g.notas.length;
        var ultimoErro = latest.erro_mensagem ? _resumirErro(latest.erro_mensagem) : "—";
        var orcLabel = "";
        if (g.orcamento_id) {
            orcLabel =
                'Orçamento <a href="orcamento-view.html?id=' +
                encodeURIComponent(String(g.orcamento_id)) +
                '" onclick="event.stopPropagation()">#' +
                _escHtml(String(g.orcamento_id)) +
                "</a>";
        } else {
            orcLabel = "Sem orçamento vinculado";
        }
        var gid = "nf-ge-" + idx;
        var detalhes = g.notas
            .map(function (n) {
                var er = n.erro_mensagem ? _resumirErro(n.erro_mensagem) : "—";
                return (
                    '<tr class="nf-grupo__detail" data-nota-id="' +
                    n.id +
                    '" hidden>' +
                    '<td colspan="7">' +
                    '<div class="nf-grupo__detail-head">' +
                    "<strong>Ref. " +
                    n.id +
                    "</strong> · " +
                    _escHtml(TIPO_LABELS[n.tipo] || n.tipo) +
                    ' · <span class="nf-col-data">' +
                    _escHtml(_fmtDataHora(n.criado_em)) +
                    "</span>" +
                    "</div>" +
                    '<div class="nf-grupo__detail-erro">' +
                    _escHtml(er) +
                    "</div>" +
                    "</td>" +
                    "<td>" +
                    _menuAcoesHtml(n) +
                    "</td></tr>"
                );
            })
            .join("");

        return (
            '<tbody class="nf-grupo" data-expanded="0" data-grupo-id="' +
            _escHtml(gid) +
            '">' +
            '<tr class="nf-grupo__summary">' +
            '<td colspan="8">' +
            '<button type="button" class="nf-grupo__toggle" aria-expanded="false" onclick="NotasFiscaisPage.toggleGrupoErro(this)">' +
            '<span class="nf-grupo__chev" aria-hidden="true">▶</span>' +
            '<span class="nf-grupo__meta">' +
            '<div class="nf-grupo__tit">' +
            orcLabel +
            " · " +
            nTent +
            " tentativas · Última: " +
            _escHtml(_fmtDataHora(latest.criado_em)) +
            "</div>" +
            '<div class="nf-grupo__erro-resumo">Último erro: ' +
            _escHtml(_trunc(ultimoErro, 160)) +
            "</div>" +
            "</span>" +
            "</button></td></tr>" +
            detalhes +
            "</tbody>"
        );
    }

    function _renderTabela(notas, statusFiltro) {
        var usarGrupos = statusFiltro === "erro";
        var partes = ['<div class="nf-table-wrap"><table class="nf-table">', _theadTabelaHtml()];

        if (usarGrupos) {
            var grupos = _agruparPorOrcamento(notas);
            grupos.forEach(function (g, idx) {
                if (g.notas.length > 1) partes.push(_htmlGrupoErro(g, idx));
                else partes.push("<tbody>" + _linhaTabelaHtml(g.notas[0]) + "</tbody>");
            });
        } else {
            partes.push("<tbody>");
            notas.forEach(function (n) {
                partes.push(_linhaTabelaHtml(n));
            });
            partes.push("</tbody>");
        }

        partes.push("</table></div>");
        return partes.join("");
    }

    function _blocoTemporalNota(n) {
        var st = n.status || "";
        if (st === "emitida") {
            return _nfMetaRow("Emitida em", _escHtml(_fmtDataHora(n.emitida_em)));
        }
        if (st === "cancelada") {
            var emi = n.emitida_em ? _fmtDataHora(n.emitida_em) : "—";
            var canc = n.cancelada_em ? _fmtDataHora(n.cancelada_em) : "—";
            return _nfMetaRow("Emitida em", _escHtml(emi)) + _nfMetaRow("Cancelada em", _escHtml(canc));
        }
        if (st === "erro") {
            return (
                _nfMetaRow("Tentativa em", _escHtml(_fmtDataHora(n.criado_em))) +
                _nfMetaHint(
                    "Esta nota não foi autorizada pela SEFAZ; o número e a data de emissão só aparecem após sucesso."
                )
            );
        }
        var base = _nfMetaRow("Registrada em", _escHtml(_fmtDataHora(n.criado_em)));
        if (st === "processando") {
            base += _nfMetaHint("Em processamento na Focus/SEFAZ.");
        }
        return base;
    }

    function _blocoOrcamento(n) {
        if (!n.orcamento_id) return "";
        var link =
            '<a href="orcamento-view.html?id=' +
            encodeURIComponent(String(n.orcamento_id)) +
            '">#' +
            _escHtml(String(n.orcamento_id)) +
            "</a>";
        return _nfMetaRow("Orçamento", link);
    }

    function _renderCartoes(notas) {
        return notas
            .map(function (n) {
                var erroHtml = "";
                if (n.erro_mensagem) {
                    var resumo = _resumirErro(n.erro_mensagem);
                    erroHtml =
                        '<div class="nf-card__alert" role="alert"><div class="nf-card__alert-title">Erro</div><div class="nf-card__alert-msg">' +
                        _escHtml(resumo) +
                        "</div></div>";
                }

                var ops = [];
                if (n.status === "emitida") {
                    ops.push(
                        '<button type="button" onclick="NotasFiscaisPage.cancelar(' +
                            n.id +
                            ')" class="btn btn-sm btn-danger">Cancelar</button>'
                    );
                    ops.push(
                        '<button type="button" onclick="NotasFiscaisPage.sincronizarFocus(' +
                            n.id +
                            ')" class="btn btn-sm btn-secondary" title="Atualiza status consultando a API Focus">Sincronizar</button>'
                    );
                    ops.push(
                        '<button type="button" onclick="NotasFiscaisPage.reenviarHook(' +
                            n.id +
                            ')" class="btn btn-sm btn-secondary" title="Reenvia notificação (webhook) da Focus">Webhook</button>'
                    );
                    if (n.tipo === "nfe") {
                        ops.push(
                            '<button type="button" onclick="NotasFiscaisPage.cartaCorrecao(' +
                                n.id +
                                ')" class="btn btn-sm btn-secondary">CC-e</button>'
                        );
                    }
                    if (n.orcamento_id && (n.tipo === "nfe" || n.tipo === "nfce")) {
                        ops.push(
                            '<button type="button" onclick="NotasFiscaisPage.previaDanfe(' +
                                n.orcamento_id +
                                ",'" +
                                String(n.tipo || "nfe").replace(/'/g, "") +
                                '\')" class="btn btn-sm btn-secondary">Prévia DANFE</button>'
                        );
                    }
                }
                if (n.status === "processando") {
                    ops.push(
                        '<button type="button" onclick="NotasFiscaisPage.sincronizarFocus(' +
                            n.id +
                            ')" class="btn btn-sm btn-secondary">Sincronizar</button>'
                    );
                }
                if (n.status === "erro") {
                    ops.push(
                        '<button type="button" onclick="NotasFiscaisPage.analisarErro(' +
                            n.id +
                            ')" class="btn btn-sm btn-warning nf-btn-analisar">Analisar e corrigir</button>'
                    );
                }

                var links = [];
                if (n.danfe_url) {
                    links.push(
                        '<a href="' +
                            _escHtml(n.danfe_url) +
                            '" target="_blank" rel="noopener noreferrer" class="btn btn-sm">DANFE</a>'
                    );
                }
                if (n.xml_url) {
                    links.push(
                        '<a href="' +
                            _escHtml(n.xml_url) +
                            '" target="_blank" rel="noopener noreferrer" class="btn btn-sm">XML</a>'
                    );
                }
                if (n.qr_code) {
                    links.push(
                        '<a href="' +
                            _escHtml(n.qr_code) +
                            '" target="_blank" rel="noopener noreferrer" class="btn btn-sm">QR Code</a>'
                    );
                }

                var metaHtml =
                    _nfMetaRow("Natureza", _escHtml(n.natureza_operacao || "—")) +
                    _blocoOrcamento(n) +
                    _blocoTemporalNota(n);

                var linksHtml = links.length ? '<div class="nf-card__links">' + links.join("") + "</div>" : "";
                var opsHtml = ops.length ? '<div class="nf-card__ops">' + ops.join("") + "</div>" : "";
                var footerInner = linksHtml + opsHtml;
                var footerBlock = footerInner ? '<div class="nf-card__footer">' + footerInner + "</div>" : "";

                return (
                    '<article class="card nf-card" data-nota-id="' +
                    n.id +
                    '">' +
                    '<header class="nf-card__header">' +
                    '<div class="nf-card__header-main">' +
                    '<span class="badge ' +
                    (STATUS_CLASSES[n.status] || "") +
                    '">' +
                    _escHtml(STATUS_LABELS[n.status] || n.status) +
                    "</span>" +
                    '<span class="nf-card__tipo">' +
                    _escHtml(TIPO_LABELS[n.tipo] || n.tipo) +
                    "</span>" +
                    "</div>" +
                    '<div class="nf-card__numero">' +
                    _numeroHtml(n) +
                    "</div>" +
                    "</header>" +
                    '<div class="nf-card__body">' +
                    '<div class="nf-meta-grid">' +
                    metaHtml +
                    "</div>" +
                    erroHtml +
                    "</div>" +
                    footerBlock +
                    "</article>"
                );
            })
            .join("");
    }

    function renderizarNotas(notas) {
        ultimasNotas = notas || [];
        var container = document.getElementById("notas-list");
        var empty = document.getElementById("notas-empty");
        var statusFiltro = document.getElementById("filtro-status") ? document.getElementById("filtro-status").value : "";

        if (!ultimasNotas.length) {
            container.innerHTML = "";
            empty.style.display = "block";
            return;
        }
        empty.style.display = "none";

        var mode = getViewMode();
        container.classList.remove("nf-list--table", "nf-list--cards");
        container.classList.add(mode === VIEW_CARDS ? "nf-list--cards" : "nf-list--table");

        if (mode === VIEW_CARDS) {
            container.innerHTML = _renderCartoes(ultimasNotas);
        } else {
            container.innerHTML = _renderTabela(ultimasNotas, statusFiltro);
        }
    }

    function _indicesPaginas(atual, total) {
        var map = {};
        function add(p) {
            if (p >= 1 && p <= total) map[p] = true;
        }
        add(1);
        add(total);
        add(atual);
        add(atual - 1);
        add(atual + 1);
        add(atual - 2);
        add(atual + 2);
        return Object.keys(map)
            .map(Number)
            .sort(function (a, b) {
                return a - b;
            });
    }

    function _htmlBotoesNumeros(atual, total) {
        var keys = _indicesPaginas(atual, total);
        var parts = [];
        var last = 0;
        for (var i = 0; i < keys.length; i++) {
            var p = keys[i];
            if (last && p > last + 1) {
                parts.push('<span class="pagination-ellipsis" aria-hidden="true">…</span>');
            }
            var isAtual = p === atual;
            parts.push(
                '<button type="button" class="pagination-btn' +
                    (isAtual ? " active" : "") +
                    '"' +
                    (isAtual ? ' disabled aria-current="page"' : "") +
                    ' onclick="NotasFiscaisPage.carregar(' +
                    p +
                    ')">' +
                    p +
                    "</button>"
            );
            last = p;
        }
        return parts.join("");
    }

    async function carregarNotas(pagina) {
        pagina = pagina || 1;
        paginaAtual = pagina;
        var tipo = document.getElementById("filtro-tipo").value;
        var status = document.getElementById("filtro-status").value;
        var busca = document.getElementById("filtro-busca").value;

        var url = "/notas-fiscais?pagina=" + pagina + "&por_pagina=20";
        if (tipo) url += "&tipo=" + tipo;
        if (status) url += "&status=" + status;
        if (busca) url += "&busca=" + encodeURIComponent(busca);

        try {
            var resp = await api.get(url);
            var data = resp.data || resp;
            renderizarNotas(data.notas || []);
            renderizarPaginacao(data);
        } catch (e) {
            console.error("Erro ao carregar notas", e);
        }
    }

    function renderizarPaginacao(data) {
        var container = document.getElementById("notas-pagination");
        var porPagina = data.por_pagina || 20;
        var total = data.total != null ? data.total : 0;
        var totalPaginas = Math.max(1, Math.ceil(total / porPagina));

        if (totalPaginas <= 1) {
            container.innerHTML = "";
            return;
        }

        var infoTexto =
            "Página " +
            paginaAtual +
            " de " +
            totalPaginas +
            " · " +
            total +
            " registro" +
            (total !== 1 ? "s" : "");

        var prevDisabled = paginaAtual <= 1;
        var nextDisabled = paginaAtual >= totalPaginas;

        var numerosHtml = _htmlBotoesNumeros(paginaAtual, totalPaginas);

        container.innerHTML =
            '<nav class="pagination-wrapper" aria-label="Paginação das notas fiscais">' +
            '<span class="pagination-info">' +
            _escHtml(infoTexto) +
            "</span>" +
            '<div class="nf-pagination-nav">' +
            '<button type="button" class="pagination-btn"' +
            (prevDisabled ? " disabled" : "") +
            ' aria-label="Página anterior" onclick="NotasFiscaisPage.carregar(' +
            (paginaAtual - 1) +
            ')">Anterior</button>' +
            '<div class="pagination-controls" role="group" aria-label="Número da página">' +
            numerosHtml +
            "</div>" +
            '<button type="button" class="pagination-btn"' +
            (nextDisabled ? " disabled" : "") +
            ' aria-label="Próxima página" onclick="NotasFiscaisPage.carregar(' +
            (paginaAtual + 1) +
            ')">Próxima</button>' +
            "</div>" +
            "</nav>";
    }

    function toggleGrupoErro(btn) {
        var tbody = btn.closest("tbody.nf-grupo");
        if (!tbody) return;
        var exp = tbody.getAttribute("data-expanded") === "1";
        var novo = exp ? "0" : "1";
        tbody.setAttribute("data-expanded", novo);
        btn.setAttribute("aria-expanded", novo === "1" ? "true" : "false");
        tbody.querySelectorAll("tr.nf-grupo__detail").forEach(function (tr) {
            if (novo === "1") tr.removeAttribute("hidden");
            else tr.setAttribute("hidden", "hidden");
        });
    }

    async function sincronizarFocus(notaId) {
        try {
            await api.post("/notas-fiscais/" + notaId + "/sincronizar-focus", {});
            showNotif && showNotif("OK", "Sincronizado", "Status atualizado com a Focus.");
            carregarNotas(paginaAtual);
        } catch (e) {
            alert("Erro ao sincronizar: " + (e.message || ""));
        }
    }

    async function reenviarHook(notaId) {
        if (!confirm("Reenviar o webhook desta nota para a URL configurada na Focus?")) return;
        try {
            var r = await api.post("/notas-fiscais/" + notaId + "/reenviar-hook-focus", {});
            alert("Webhook reenviado. Resposta: " + JSON.stringify(r && (r.data != null ? r.data : r)).substring(0, 400));
            carregarNotas(paginaAtual);
        } catch (e) {
            alert("Erro: " + (e.message || ""));
        }
    }

    async function cartaCorrecao(notaId) {
        var t = prompt("Texto da carta de correção (15 a 1000 caracteres):");
        if (!t || t.length < 15) {
            alert("Mínimo 15 caracteres.");
            return;
        }
        if (t.length > 1000) {
            alert("Máximo 1000 caracteres.");
            return;
        }
        try {
            await api.post("/notas-fiscais/" + notaId + "/carta-correcao", { correcao: t });
            showNotif && showNotif("OK", "CC-e", "Carta de correção registrada na Focus.");
            carregarNotas(paginaAtual);
        } catch (e) {
            alert("Erro na carta de correção: " + (e.message || ""));
        }
    }

    async function previaDanfe(orcamentoId, tipo) {
        tipo = tipo || "nfe";
        try {
            var blob = await api.post(
                "/notas-fiscais/previsualizar-danfe",
                {
                    orcamento_id: orcamentoId,
                    tipo: tipo,
                    natureza_operacao: "Venda de mercadorias",
                    serie: "1",
                },
                { expectBinary: true }
            );
            var u = URL.createObjectURL(blob);
            window.open(u, "_blank", "noopener,noreferrer");
            setTimeout(function () {
                URL.revokeObjectURL(u);
            }, 120000);
        } catch (e) {
            alert("Erro na prévia DANFE: " + (e.message || ""));
        }
    }

    async function cancelar(notaId) {
        var motivo = prompt("Motivo do cancelamento (15 a 255 caracteres, exigência Focus):");
        if (!motivo || motivo.length < 15) {
            alert("Motivo deve ter pelo menos 15 caracteres.");
            return;
        }
        if (motivo.length > 255) {
            alert("Motivo deve ter no máximo 255 caracteres.");
            return;
        }
        try {
            await api.post("/notas-fiscais/" + notaId + "/cancelar", { motivo: motivo });
            carregarNotas(paginaAtual);
        } catch (e) {
            alert("Erro ao cancelar nota: " + (e.response?.data?.detail || e.message));
        }
    }

    async function analisarErro(notaId) {
        var btn = document.querySelector('[data-nota-id="' + notaId + '"] .nf-btn-analisar, [data-nota-id="' + notaId + '"] .btn-warning');
        if (btn) {
            btn.disabled = true;
            btn.textContent = "Analisando...";
        }

        var analise = null;
        try {
            analise = await api.post("/notas-fiscais/" + notaId + "/analisar-erro", {});
        } catch (e) {
            alert("Erro ao analisar: " + (e.message || "tente novamente"));
            if (btn) {
                btn.disabled = false;
                btn.textContent = "Analisar e corrigir";
            }
            return;
        }
        if (btn) {
            btn.disabled = false;
            btn.textContent = "Analisar e corrigir";
        }

        _mostrarModalAnalise(analise);
    }

    function _mostrarModalAnalise(analise) {
        var existente = document.getElementById("modal-analise-erro");
        if (existente) existente.remove();

        var sugestoesHtml = (analise.sugestoes || [])
            .map(function (s) {
                return (
                    '<div style="margin-bottom:12px;padding:10px 12px;background:rgba(255,200,0,0.08);border-left:3px solid #f59e0b;border-radius:4px">' +
                    '<div style="font-size:0.75rem;color:#f59e0b;font-weight:600;text-transform:uppercase;margin-bottom:4px">' +
                    _escHtml(s.campo) +
                    "</div>" +
                    '<div style="font-size:0.9rem">' +
                    _escHtml(s.acao) +
                    "</div>" +
                    "</div>"
                );
            })
            .join("");

        if (!sugestoesHtml) {
            sugestoesHtml = '<p style="color:var(--text-muted,#888)">Nenhuma sugestão automática disponível.</p>';
        }

        var botoesAcao = "";
        if (analise.orcamento_id) {
            botoesAcao +=
                '<a href="orcamento-view.html?id=' +
                encodeURIComponent(String(analise.orcamento_id)) +
                '" class="btn btn-secondary btn-sm" style="margin-right:8px" target="_blank" rel="noopener noreferrer">Ver Orçamento</a>';
            botoesAcao += '<button id="btn-reemitir-analise" class="btn btn-primary btn-sm">Reemitir Nota</button>';
        }

        var modal = document.createElement("div");
        modal.id = "modal-analise-erro";
        modal.style.cssText =
            "position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:9999;display:flex;align-items:center;justify-content:center";
        modal.innerHTML =
            '<div style="background:var(--bg-card,#1e1e2e);border:1px solid var(--border,#2d2d3f);border-radius:12px;width:520px;max-width:95vw;max-height:85vh;overflow-y:auto;padding:24px">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">' +
            '<h3 style="margin:0;font-size:1.1rem">Análise do Erro</h3>' +
            '<button type="button" id="btn-fechar-analise" style="background:none;border:none;cursor:pointer;font-size:1.4rem;color:var(--text-muted,#888)" aria-label="Fechar">&times;</button>' +
            "</div>" +
            '<div style="margin-bottom:16px">' +
            sugestoesHtml +
            "</div>" +
            (botoesAcao
                ? '<div style="display:flex;align-items:center;gap:8px;padding-top:12px;border-top:1px solid var(--border,#2d2d3f)">' +
                  botoesAcao +
                  "</div>"
                : "") +
            "</div>";

        document.body.appendChild(modal);

        document.getElementById("btn-fechar-analise").onclick = function () {
            modal.remove();
        };
        modal.onclick = function (e) {
            if (e.target === modal) modal.remove();
        };

        var btnReemitir = document.getElementById("btn-reemitir-analise");
        if (btnReemitir) {
            btnReemitir.onclick = async function () {
                btnReemitir.disabled = true;
                btnReemitir.textContent = "Reemitindo...";
                try {
                    await api.post("/notas-fiscais/" + analise.nota_id + "/reemitir", {});
                    modal.remove();
                    carregarNotas(paginaAtual);
                } catch (e) {
                    btnReemitir.disabled = false;
                    btnReemitir.textContent = "Reemitir Nota";
                    alert("Erro ao reemitir: " + (e.message || "tente novamente"));
                }
            };
        }
    }

    var debounceTimer;
    function debounce(fn, ms) {
        return function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(fn, ms);
        };
    }

    function init() {
        _syncViewButtons();

        var bTable = document.getElementById("nf-view-table");
        var bCards = document.getElementById("nf-view-cards");
        if (bTable) bTable.addEventListener("click", function () { setViewMode(VIEW_TABLE); });
        if (bCards) bCards.addEventListener("click", function () { setViewMode(VIEW_CARDS); });

        document.addEventListener("click", function (e) {
            if (e.target.closest(".nf-actions__trigger")) {
                e.preventDefault();
                e.stopPropagation();
                alternarMenuAcoes(e.target.closest(".nf-actions__trigger"));
                return;
            }
            if (!e.target.closest(".nf-actions")) fecharMenusAcoes();
        });

        var t = document.getElementById("filtro-tipo");
        if (t) t.addEventListener("change", function () { carregarNotas(1); });

        var s = document.getElementById("filtro-status");
        if (s) s.addEventListener("change", function () { carregarNotas(1); });

        var b = document.getElementById("filtro-busca");
        if (b) b.addEventListener("input", debounce(function () { carregarNotas(1); }, 300));

        carregarNotas(1);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

    window.NotasFiscaisPage = {
        carregar: carregarNotas,
        cancelar: cancelar,
        analisarErro: analisarErro,
        sincronizarFocus: sincronizarFocus,
        reenviarHook: reenviarHook,
        cartaCorrecao: cartaCorrecao,
        previaDanfe: previaDanfe,
        fecharMenusAcoes: fecharMenusAcoes,
        toggleGrupoErro: toggleGrupoErro,
    };
})();
