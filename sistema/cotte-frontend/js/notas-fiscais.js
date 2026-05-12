(function NotasFiscaisPage() {
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

    var paginaAtual = 1;

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
        } catch(e) {
            console.error("Erro ao carregar notas", e);
        }
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

    function _linhaTemporalNota(n) {
        var st = n.status || "";
        if (st === "emitida") {
            return "<p><strong>Emitida em:</strong> " + _escHtml(_fmtDataHora(n.emitida_em)) + "</p>";
        }
        if (st === "cancelada") {
            var emi = n.emitida_em ? _fmtDataHora(n.emitida_em) : "—";
            var canc = n.cancelada_em ? _fmtDataHora(n.cancelada_em) : "—";
            return "<p><strong>Emitida em:</strong> " + _escHtml(emi) + "</p>"
                + "<p><strong>Cancelada em:</strong> " + _escHtml(canc) + "</p>";
        }
        if (st === "erro") {
            return "<p><strong>Tentativa registrada em:</strong> " + _escHtml(_fmtDataHora(n.criado_em)) + "</p>"
                + "<p style=\"font-size:0.82rem;color:var(--muted,#666);margin:4px 0\">"
                + "Esta nota não foi autorizada pela SEFAZ; o número e a data de emissão só aparecem após sucesso."
                + "</p>";
        }
        return "<p><strong>Registrada em:</strong> " + _escHtml(_fmtDataHora(n.criado_em)) + "</p>"
            + (st === "processando"
                ? "<p style=\"font-size:0.82rem;color:var(--muted,#666);margin:4px 0\">Em processamento na Notaas/SEFAZ.</p>"
                : "");
    }

    function _linhaOrcamento(n) {
        if (!n.orcamento_id) return "";
        return "<p><strong>Orçamento:</strong> "
            + "<a href=\"orcamento-view.html?id=" + encodeURIComponent(String(n.orcamento_id)) + "\">#"
            + _escHtml(String(n.orcamento_id)) + "</a></p>";
    }

    function renderizarNotas(notas) {
        var container = document.getElementById("notas-list");
        var empty = document.getElementById("notas-empty");

        if (!notas.length) {
            container.innerHTML = "";
            empty.style.display = "block";
            return;
        }
        empty.style.display = "none";

        container.innerHTML = notas.map(function(n) {
            var erroHtml = "";
            if (n.erro_mensagem) {
                var resumo = _resumirErro(n.erro_mensagem);
                erroHtml = '<p class="text-danger" style="font-size:0.82rem;margin:4px 0"><strong>Erro:</strong> '
                    + _escHtml(resumo) + "</p>";
            }
            var botoesAcao = "";
            if (n.status === "emitida") {
                botoesAcao += '<button onclick="NotasFiscaisPage.cancelar(' + n.id + ')" class="btn btn-sm btn-danger">Cancelar</button>';
            }
            if (n.status === "erro") {
                botoesAcao += '<button onclick="NotasFiscaisPage.analisarErro(' + n.id + ')" class="btn btn-sm btn-warning">Analisar e Corrigir</button>';
            }
            var numLabel = n.numero ? _escHtml(n.numero) : (n.status === "erro" ? "— <span style=\"font-weight:400;color:var(--muted,#666)\">(não emitida)</span>" : "—");
            return '<div class="card nf-card" data-id="' + n.id + '">'
                + '<div class="card-header">'
                + '<span class="badge ' + (STATUS_CLASSES[n.status] || "") + '">' + _escHtml(STATUS_LABELS[n.status] || n.status) + '</span>'
                + '<span class="nf-tipo">' + _escHtml(TIPO_LABELS[n.tipo] || n.tipo) + '</span>'
                + '<span class="nf-numero">' + numLabel + '</span>'
                + '</div>'
                + '<div class="card-body">'
                + '<p><strong>Natureza:</strong> ' + _escHtml(n.natureza_operacao || "—") + '</p>'
                + _linhaOrcamento(n)
                + _linhaTemporalNota(n)
                + erroHtml
                + '</div>'
                + '<div class="card-footer">'
                + (n.danfe_url ? '<a href="' + _escHtml(n.danfe_url) + '" target="_blank" rel="noopener noreferrer" class="btn btn-sm">DANFE</a>' : "")
                + (n.xml_url ? '<a href="' + _escHtml(n.xml_url) + '" target="_blank" rel="noopener noreferrer" class="btn btn-sm">XML</a>' : "")
                + (n.qr_code ? '<a href="' + _escHtml(n.qr_code) + '" target="_blank" rel="noopener noreferrer" class="btn btn-sm">QR Code</a>' : "")
                + botoesAcao
                + '</div>'
                + '</div>';
        }).join("");
    }

    function renderizarPaginacao(data) {
        var container = document.getElementById("notas-pagination");
        var totalPaginas = Math.ceil(data.total / data.por_pagina);
        if (totalPaginas <= 1) {
            container.innerHTML = "";
            return;
        }
        var html = "";
        for (var i = 1; i <= totalPaginas; i++) {
            html += '<button class="btn btn-sm ' + (i === paginaAtual ? "btn-primary" : "") + '" onclick="NotasFiscaisPage.carregar(' + i + ')">' + i + '</button>';
        }
        container.innerHTML = html;
    }

    async function cancelar(notaId) {
        var motivo = prompt("Motivo do cancelamento (mínimo 15 caracteres):");
        if (!motivo || motivo.length < 15) {
            alert("Motivo deve ter pelo menos 15 caracteres.");
            return;
        }
        try {
            await api.post("/notas-fiscais/" + notaId + "/cancelar", { motivo: motivo });
            carregarNotas(paginaAtual);
        } catch(e) {
            alert("Erro ao cancelar nota: " + (e.response?.data?.detail || e.message));
        }
    }

    async function analisarErro(notaId) {
        var btn = document.querySelector('[data-id="' + notaId + '"] .btn-warning');
        if (btn) { btn.disabled = true; btn.textContent = "Analisando..."; }

        var analise = null;
        try {
            analise = await api.post("/notas-fiscais/" + notaId + "/analisar-erro", {});
        } catch(e) {
            alert("Erro ao analisar: " + (e.message || "tente novamente"));
            if (btn) { btn.disabled = false; btn.textContent = "Analisar e Corrigir"; }
            return;
        }
        if (btn) { btn.disabled = false; btn.textContent = "Analisar e Corrigir"; }

        _mostrarModalAnalise(analise);
    }

    function _mostrarModalAnalise(analise) {
        var existente = document.getElementById("modal-analise-erro");
        if (existente) existente.remove();

        var sugestoesHtml = (analise.sugestoes || []).map(function(s) {
            return '<div style="margin-bottom:12px;padding:10px 12px;background:rgba(255,200,0,0.08);border-left:3px solid #f59e0b;border-radius:4px">'
                + '<div style="font-size:0.75rem;color:#f59e0b;font-weight:600;text-transform:uppercase;margin-bottom:4px">' + s.campo + '</div>'
                + '<div style="font-size:0.9rem">' + s.acao + '</div>'
                + '</div>';
        }).join("");

        if (!sugestoesHtml) {
            sugestoesHtml = '<p style="color:var(--text-muted,#888)">Nenhuma sugestão automática disponível.</p>';
        }

        var botoesAcao = "";
        if (analise.orcamento_id) {
            botoesAcao += '<a href="orcamento-view.html?id=' + encodeURIComponent(String(analise.orcamento_id)) + '" class="btn btn-secondary btn-sm" style="margin-right:8px" target="_blank" rel="noopener noreferrer">Ver Orçamento</a>';
            botoesAcao += '<button id="btn-reemitir-analise" class="btn btn-primary btn-sm">Reemitir Nota</button>';
        }

        var modal = document.createElement("div");
        modal.id = "modal-analise-erro";
        modal.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:9999;display:flex;align-items:center;justify-content:center";
        modal.innerHTML = '<div style="background:var(--bg-card,#1e1e2e);border:1px solid var(--border,#2d2d3f);border-radius:12px;width:520px;max-width:95vw;max-height:85vh;overflow-y:auto;padding:24px">'
            + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">'
            + '<h3 style="margin:0;font-size:1.1rem">Análise do Erro</h3>'
            + '<button id="btn-fechar-analise" style="background:none;border:none;cursor:pointer;font-size:1.4rem;color:var(--text-muted,#888)">&times;</button>'
            + '</div>'
            + '<div style="margin-bottom:16px">' + sugestoesHtml + '</div>'
            + (botoesAcao ? '<div style="display:flex;align-items:center;gap:8px;padding-top:12px;border-top:1px solid var(--border,#2d2d3f)">' + botoesAcao + '</div>' : '')
            + '</div>';

        document.body.appendChild(modal);

        document.getElementById("btn-fechar-analise").onclick = function() { modal.remove(); };
        modal.onclick = function(e) { if (e.target === modal) modal.remove(); };

        var btnReemitir = document.getElementById("btn-reemitir-analise");
        if (btnReemitir) {
            btnReemitir.onclick = async function() {
                btnReemitir.disabled = true;
                btnReemitir.textContent = "Reemitindo...";
                try {
                    await api.post("/notas-fiscais/" + analise.nota_id + "/reemitir", {});
                    modal.remove();
                    carregarNotas(paginaAtual);
                } catch(e) {
                    btnReemitir.disabled = false;
                    btnReemitir.textContent = "Reemitir Nota";
                    alert("Erro ao reemitir: " + (e.message || "tente novamente"));
                }
            };
        }
    }

    var debounceTimer;
    function debounce(fn, ms) {
        return function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(fn, ms);
        };
    }

    function init() {
        var t = document.getElementById("filtro-tipo");
        if(t) t.addEventListener("change", function() { carregarNotas(1); });

        var s = document.getElementById("filtro-status");
        if(s) s.addEventListener("change", function() { carregarNotas(1); });

        var b = document.getElementById("filtro-busca");
        if(b) b.addEventListener("input", debounce(function() { carregarNotas(1); }, 300));

        carregarNotas(1);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

    window.NotasFiscaisPage = { carregar: carregarNotas, cancelar: cancelar, analisarErro: analisarErro };
})();
