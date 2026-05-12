(function NotasFiscaisPage() {
    var TIPO_LABELS = { nfse: "NFS-e", nfe: "NF-e", nfce: "NFC-e" };
    var STATUS_CLASSES = {
        pendente: "badge-warning",
        processando: "badge-info",
        emitida: "badge-success",
        cancelada: "badge-secondary",
        erro: "badge-danger",
    };

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
            return '<div class="card nf-card" data-id="' + n.id + '">'
                + '<div class="card-header">'
                + '<span class="badge ' + (STATUS_CLASSES[n.status] || "") + '">' + n.status + '</span>'
                + '<span class="nf-tipo">' + (TIPO_LABELS[n.tipo] || n.tipo) + '</span>'
                + '<span class="nf-numero">' + (n.numero || "—") + '</span>'
                + '</div>'
                + '<div class="card-body">'
                + '<p><strong>Natureza:</strong> ' + (n.natureza_operacao || "—") + '</p>'
                + '<p><strong>Emitida em:</strong> ' + (n.emitida_em ? new Date(n.emitida_em).toLocaleDateString("pt-BR") : "—") + '</p>'
                + (n.erro_mensagem ? '<p class="text-danger"><strong>Erro:</strong> ' + n.erro_mensagem + '</p>' : "")
                + '</div>'
                + '<div class="card-footer">'
                + (n.danfe_url ? '<a href="' + n.danfe_url + '" target="_blank" class="btn btn-sm">DANFE</a>' : "")
                + (n.xml_url ? '<a href="' + n.xml_url + '" target="_blank" class="btn btn-sm">XML</a>' : "")
                + (n.qr_code ? '<a href="' + n.qr_code + '" target="_blank" class="btn btn-sm">QR Code</a>' : "")
                + (n.status === "emitida" ? '<button onclick="NotasFiscaisPage.cancelar(' + n.id + ')" class="btn btn-sm btn-danger">Cancelar</button>' : "")
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

    var debounceTimer;
    function debounce(fn, ms) {
        return function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(fn, ms);
        };
    }

    // Wait for DOM to be ready before attaching events
    document.addEventListener("DOMContentLoaded", function() {
        var t = document.getElementById("filtro-tipo");
        if(t) t.addEventListener("change", function() { carregarNotas(1); });
        
        var s = document.getElementById("filtro-status");
        if(s) s.addEventListener("change", function() { carregarNotas(1); });
        
        var b = document.getElementById("filtro-busca");
        if(b) b.addEventListener("input", debounce(function() { carregarNotas(1); }, 300));

        carregarNotas(1);
    });

    window.NotasFiscaisPage = { carregar: carregarNotas, cancelar: cancelar };
})();
