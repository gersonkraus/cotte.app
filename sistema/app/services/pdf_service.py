import os
import re
import logging
from fpdf import FPDF
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except Exception as e:
    logger.warning(f"WeasyPrint não pôde ser carregado: {e}. Usando FPDF2 como fallback.")
    HAS_WEASYPRINT = False

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple:
    try:
        h = (hex_color or "#00e5a0").lstrip("#")
        if len(h) != 6:
            return (0, 229, 160)
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        return (0, 229, 160)


def _texto_sobre_cor(r: int, g: int, b: int) -> tuple:
    """Branco ou preto — decide pelo contraste (luminância WCAG)."""
    try:
        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return (255, 255, 255) if lum < 0.58 else (20, 20, 20)
    except Exception:
        return (255, 255, 255)


def _brl(valor: float) -> str:
    try:
        v = float(valor or 0)
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def _sanitize(texto: str) -> str:
    """Sanitiza texto para PDF: remove caracteres de controle, preserva acentos/codificações."""
    t = str(texto or "")
    # Remove caracteres de controle (exceto \n, \t) que quebram o PDF
    t = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', t)
    return t


# ─────────────────────────────────────────────────────────────────────────────
# FONTES TTF (Unicode — suporta acentos, cedilhas, etc.)
# ─────────────────────────────────────────────────────────────────────────────

_FONT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "fonts", "pdf"))

def _registrar_fontes(pdf: FPDF):
    """Registra fontes DejaVuSans (Unicode) no FPDF."""
    regular = os.path.join(_FONT_DIR, "DejaVuSans.ttf")
    bold = os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")

    if not os.path.isfile(regular) or not os.path.isfile(bold):
        return False

    try:
        pdf.add_font("DejaVu", "", regular)
        pdf.add_font("DejaVu", "B", bold)
        return True
    except Exception as e:
        logger.error(f"Erro ao registrar fontes DejaVu: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# GERADORES
# ─────────────────────────────────────────────────────────────────────────────

def _enriquecer_orcamento(orc: dict) -> dict:
    """Garante que o dicionário tenha todos os campos necessários para os templates."""
    try:
        itens = orc.get("itens") or []
        
        # Garantir que todos os valores numéricos sejam float e não None
        for item in itens:
            item["quantidade"] = float(item.get("quantidade") or 0)
            item["valor_unit"] = float(item.get("valor_unit") or 0)
            # Se total não existir, calcula
            if item.get("total") is None:
                item["total"] = item["quantidade"] * item["valor_unit"]
            else:
                item["total"] = float(item["total"])

        subtotal = orc.get("subtotal")
        if subtotal is None:
            subtotal = sum(i["total"] for i in itens)
        else:
            subtotal = float(subtotal)
        
        total = float(orc.get("total") or 0)
        
        desconto_v = orc.get("desconto_valor")
        if desconto_v is None:
            # Tenta inferir desconto se tiver valor de desconto bruto ou percentual
            desc_raw = float(orc.get("desconto") or 0)
            if desc_raw > 0:
                if orc.get("desconto_tipo") == "percentual":
                    desconto_v = subtotal * (desc_raw / 100)
                else:
                    desconto_v = desc_raw
            else:
                # Fallback final por diferença
                desconto_v = subtotal - total if subtotal > total else 0.0
        else:
            desconto_v = float(desconto_v)
        
        orc["subtotal"] = subtotal
        orc["desconto_valor"] = desconto_v
        orc["total"] = total
        orc["numero"] = str(orc.get("numero") or "S/N")
        
        return orc
    except Exception as e:
        logger.error(f"Erro ao enriquecer orçamento para PDF: {e}")
        return orc


def _normalizar_logo_url(empresa: dict) -> dict:
    """Ajusta o logo_url para ser um caminho local absoluto ou relativo ao template_dir."""
    try:
        logo = empresa.get("logo_url")
        if not logo:
            return empresa
        
        logo_str = str(logo).strip()
        if not logo_str or logo_str.startswith("http"):
            return empresa
        
        # Se já for um caminho absoluto que existe, não mexe
        if os.path.isabs(logo_str) and os.path.exists(logo_str):
            empresa["_logo_path_completo"] = logo_str
            return empresa
            
        # Base do projeto (onde está o static/)
        # Em produção (Railway), os arquivos estão em /app
        # pdf_service.py está em /app/app/services/pdf_service.py
        base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        
        # Tenta localizar o arquivo no disco
        # Remove barra inicial se houver para não quebrar o join
        rel_path = logo_str.lstrip("/")
        full_path = os.path.join(base_dir, rel_path)
        
        if os.path.exists(full_path):
            # Para o WeasyPrint com base_url=template_dir (/app/app/templates), 
            # o caminho de 'static' é '../../static'
            empresa["logo_url"] = os.path.join("..", "..", rel_path)
            empresa["_logo_path_completo"] = full_path
        
        return empresa
    except Exception as e:
        logger.error(f"Erro ao normalizar logo_url: {e}")
        return empresa


def gerar_pdf_orcamento(orcamento: dict, empresa: dict) -> bytes:
    """Gera PDF de orçamento usando WeasyPrint (preferencial) ou FPDF2 (fallback)."""
    try:
        orcamento = _enriquecer_orcamento(orcamento)
        empresa = _normalizar_logo_url(empresa)
        
        # Se a empresa escolheu 'moderno', tentamos WeasyPrint
        template_pref = str(empresa.get("template_orcamento") or "classico").lower()
        
        if HAS_WEASYPRINT and template_pref == "moderno":
            try:
                return gerar_pdf_weasyprint(orcamento, empresa)
            except Exception as e:
                logger.error(f"Falha ao gerar PDF com WeasyPrint: {e}. Usando fallback FPDF2.")
                import traceback
                logger.error(traceback.format_exc())
                return gerar_pdf_fpdf2(orcamento, empresa)
        else:
            return gerar_pdf_fpdf2(orcamento, empresa)
    except Exception as e:
        logger.error(f"Erro crítico em gerar_pdf_orcamento: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Tenta o fallback mais simples possível se tudo falhar
        return gerar_pdf_fpdf2(orcamento, empresa)


def gerar_pdf_weasyprint(orcamento: dict, empresa: dict) -> bytes:
    """Gera PDF usando WeasyPrint e template HTML."""
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("orcamento.html")

    emissao = datetime.now()
    data_emi = emissao.strftime("%d/%m/%Y")
    validade_dias = orcamento.get("validade_dias") or 7
    data_val = (emissao + timedelta(days=validade_dias)).strftime("%d/%m/%Y")

    # Preparar dados para o template
    context = {
        "orcamento": orcamento,
        "empresa": empresa,
        "data_emissao": data_emi,
        "validade": data_val,
    }

    html_content = template.render(context)
    
    # Log para debug de caminhos
    logger.info(f"WeasyPrint: base_url={template_dir}")
    if empresa.get("logo_url"):
        logger.info(f"WeasyPrint: logo_url={empresa['logo_url']}")

    # Renderizar para PDF
    pdf_bytes = HTML(string=html_content, base_url=template_dir).write_pdf()
    
    return pdf_bytes


def gerar_pdf_fpdf2(orcamento: dict, empresa: dict) -> bytes:
    """Lógica original usando FPDF2 (mantida para fallback)."""
    emissao   = datetime.now()
    data_emi  = emissao.strftime("%d/%m/%Y")
    data_val  = (emissao + timedelta(days=orcamento.get("validade_dias") or 7)).strftime("%d/%m/%Y")

    # Cor da empresa
    cr, cg, cb = _hex_to_rgb(empresa.get("cor_primaria") or "#00e5a0")
    txt_r, txt_g, txt_b = _texto_sobre_cor(cr, cg, cb)  # texto sobre fundo colorido

    # Margem e largura útil
    M = 14          # margem esquerda/direita
    W = 182         # largura útil (210 - 2×14)
    X2 = M + W      # borda direita (196)

    pdf = FPDF()
    fonts_ok = _registrar_fontes(pdf)
    _FONT = "DejaVu" if fonts_ok else "Helvetica"
    pdf.add_page()
    pdf.set_margins(M, M, M)
    pdf.set_auto_page_break(auto=True, margin=14)

    # ── 1. CABEÇALHO ─────────────────────────────────────────────────────────
    #    Logo + nome/info  (esq)  |  "Orçamento" + número + datas  (dir)

    logo_path = empresa.get("_logo_path_completo") or (empresa.get("logo_url") or "").lstrip("/")
    logo_w = 0
    if logo_path and os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=M, y=M, h=14)
            logo_w = 18     # espaço reservado à direita da logo
        except Exception:
            logo_w = 0

    nome_x = M + logo_w + (3 if logo_w else 0)

    # Nome da empresa em cor_primaria
    pdf.set_xy(nome_x, M)
    pdf.set_font(_FONT, "B", 17)
    pdf.set_text_color(cr, cg, cb)
    espaco_nome = W * 0.56 - logo_w
    pdf.cell(espaco_nome, 8, _sanitize(empresa.get("nome") or "Empresa"), ln=False)

    # Bloco direito: label "Orçamento"
    col2_x = M + W * 0.56
    pdf.set_xy(col2_x, M)
    pdf.set_font(_FONT, "B", 8)
    pdf.set_text_color(180, 180, 180)
    pdf.cell(W * 0.44, 4, "Orçamento", align="R", ln=False)

    # Número em destaque
    pdf.set_xy(col2_x, M + 4)
    pdf.set_font(_FONT, "B", 14)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(W * 0.44, 7, _sanitize(orcamento.get("numero") or ""), align="R", ln=True)

    # Info empresa (telefone / email)
    info_partes = []
    if empresa.get("telefone"): info_partes.append(empresa["telefone"])
    if empresa.get("email"):    info_partes.append(empresa["email"])
    if info_partes:
        pdf.set_xy(nome_x, M + 9)
        pdf.set_font(_FONT, "", 8)
        pdf.set_text_color(130, 130, 130)
        pdf.cell(espaco_nome, 4, _sanitize("  ".join(info_partes)), ln=False)

    # Datas (emissão / validade)
    y_datas = M + 12
    pdf.set_xy(col2_x, y_datas)
    pdf.set_font(_FONT, "", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(W * 0.44, 4, f"Emissão: {data_emi}", align="R", ln=True)
    pdf.set_x(col2_x)
    pdf.cell(W * 0.44, 4, f"Validade: {data_val}", align="R", ln=False)

    # Linha divisória na cor da empresa (3pt = ~1mm)
    y_linha = max(pdf.get_y() + 5, M + 22)
    pdf.set_draw_color(cr, cg, cb)
    pdf.set_line_width(0.9)
    pdf.line(M, y_linha, X2, y_linha)
    pdf.set_line_width(0.2)
    pdf.set_draw_color(200, 200, 200)

    # ── 2. BLOCO CLIENTE + CONDIÇÕES ─────────────────────────────────────────
    #    Retângulo cinza claro com borda esquerda colorida

    y_info = y_linha + 5
    info_h = 28    # altura do bloco (ajusta conforme email)
    cli = orcamento.get("cliente") or {}
    if cli.get("email"): info_h += 4

    # Fundo cinza claro
    pdf.set_fill_color(249, 249, 249)
    pdf.rect(M, y_info, W, info_h, "F")
    # Borda esquerda colorida (4px)
    pdf.set_fill_color(cr, cg, cb)
    pdf.rect(M, y_info, 1.2, info_h, "F")

    col_w = W * 0.52
    pad   = 4      # padding interno

    # — Coluna esquerda: cliente —
    y_c = y_info + pad
    pdf.set_xy(M + 4, y_c)
    pdf.set_font(_FONT, "B", 7)
    pdf.set_text_color(180, 180, 180)
    pdf.cell(col_w - 4, 4, "PARA", ln=True)

    pdf.set_x(M + 4)
    pdf.set_font(_FONT, "B", 12)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(col_w - 4, 6, _sanitize(cli.get("nome") or "—"), ln=True)

    if cli.get("telefone"):
        pdf.set_x(M + 4)
        pdf.set_font(_FONT, "", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(col_w - 4, 4, _sanitize(cli["telefone"]), ln=True)

    if cli.get("email"):
        pdf.set_x(M + 4)
        pdf.set_font(_FONT, "", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(col_w - 4, 4, _sanitize(cli["email"]), ln=True)

    # — Coluna direita: condições —
    forma_map = {
        "pix": "PIX",
        "a_vista": "À vista",
        "2x": "2x sem juros",
        "3x": "3x sem juros",
        "4x": "4x sem juros",
    }
    raw_forma = orcamento.get("forma_pagamento") or "PIX"
    # Pode vir como Enum, string simples ("pix") ou "FormaPagamento.PIX"
    if hasattr(raw_forma, "value"):
        raw_forma = raw_forma.value
    forma_key = str(raw_forma).lower()
    if "." in forma_key:
        # Trata enum em string tipo "FormaPagamento.PIX"
        forma_key = forma_key.split(".")[-1]
    forma = forma_map.get(forma_key, str(raw_forma) or "PIX")

    col2_x2 = M + col_w
    y_c2 = y_info + pad

    pdf.set_xy(col2_x2, y_c2)
    pdf.set_font(_FONT, "B", 7)
    pdf.set_text_color(180, 180, 180)
    pdf.cell(W - col_w, 4, "CONDIÇÕES", align="R", ln=False)

    for label, val in [("Pagamento:", forma), (f"Validade:", f"{orcamento.get('validade_dias') or 7} dias")]:
        y_c2 += 5
        pdf.set_xy(col2_x2, y_c2)
        pdf.set_font(_FONT, "", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(W - col_w - 28, 4, _sanitize(label), align="R", ln=False)
        pdf.set_font(_FONT, "B", 8)
        pdf.set_text_color(20, 20, 20)
        pdf.cell(28, 4, _sanitize(val), align="R", ln=False)

    pdf.set_y(y_info + info_h + 5)

    # ── 3. TABELA DE ITENS ────────────────────────────────────────────────────

    # Cabeçalho da tabela — cor da empresa
    pdf.set_fill_color(cr, cg, cb)
    pdf.set_text_color(txt_r, txt_g, txt_b)
    pdf.set_font(_FONT, "B", 8)
    pdf.set_x(M)

    C_DESC  = W * 0.55
    C_QTD   = W * 0.10
    C_UNIT  = W * 0.175
    C_TOT   = W * 0.175

    pdf.cell(C_DESC, 7, "  DESCRIÇÃO",  fill=True, ln=False)
    pdf.cell(C_QTD,  7, "QTD",  align="C", fill=True, ln=False)
    pdf.cell(C_UNIT, 7, "UNIT.", align="R", fill=True, ln=False)
    pdf.cell(C_TOT,  7, "TOTAL", align="R", fill=True, ln=True)

    # Linhas de item
    pdf.set_font(_FONT, "", 9)
    for i, item in enumerate(orcamento.get("itens") or []):
        bg = (248, 249, 250) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_text_color(30, 30, 30)

        qtd = item.get("quantidade") or 1
        qtd_s = str(int(qtd)) if qtd == int(qtd) else f"{qtd:.1f}"
        desc  = _sanitize(item.get("descricao") or "")[:58]

        pdf.set_x(M)
        pdf.cell(C_DESC, 7, f"  {desc}", fill=True, ln=False)
        pdf.cell(C_QTD,  7, qtd_s, align="C", fill=True, ln=False)
        pdf.cell(C_UNIT, 7, _brl(item.get("valor_unit") or 0), align="R", fill=True, ln=False)
        pdf.set_font(_FONT, "B", 9)
        pdf.cell(C_TOT,  7, _brl(item.get("total") or 0), align="R", fill=True, ln=True)
        pdf.set_font(_FONT, "", 9)

    pdf.ln(2)

    # ── 4. TOTAIS (alinhados à direita) ───────────────────────────────────────

    desconto      = float(orcamento.get("desconto") or 0)
    desconto_tipo = orcamento.get("desconto_tipo") or "percentual"
    subtotal      = float(orcamento.get("subtotal") or orcamento.get("total") or 0)
    total         = float(orcamento.get("total") or 0)

    tot_w   = W * 0.45        # largura do bloco de totais
    tot_x   = X2 - tot_w     # posição X inicial

    if desconto > 0:
        # Subtotal
        pdf.set_x(tot_x)
        pdf.set_font(_FONT, "", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(tot_w * 0.58, 6, "Subtotal", fill=True, ln=False)
        pdf.cell(tot_w * 0.42, 6, _brl(subtotal), align="R", fill=True, ln=True)

        # Desconto
        if desconto_tipo == "percentual":
            desc_label = f"Desconto ({desconto:.0f}%)"
            desc_val   = subtotal * (desconto / 100)
        else:
            desc_label = "Desconto"
            desc_val   = desconto
        pdf.set_x(tot_x)
        pdf.set_font(_FONT, "", 9)
        pdf.set_text_color(200, 60, 60)
        pdf.set_fill_color(255, 245, 245)
        pdf.cell(tot_w * 0.58, 6, _sanitize(desc_label), fill=True, ln=False)
        pdf.cell(tot_w * 0.42, 6, f"- {_brl(desc_val)}", align="R", fill=True, ln=True)
        pdf.ln(1)

    # Linha de TOTAL — cor da empresa
    pdf.set_x(tot_x)
    pdf.set_fill_color(cr, cg, cb)
    pdf.set_text_color(txt_r, txt_g, txt_b)
    pdf.set_font(_FONT, "B", 11)
    pdf.cell(tot_w * 0.50, 10, "  TOTAL", fill=True, ln=False)
    pdf.cell(tot_w * 0.50, 10, _brl(total), align="R", fill=True, ln=True)

    # ── 5. ACEITE DIGITAL (se aprovado) ───────────────────────────────────────
    if orcamento.get("status") == "aprovado" or orcamento.get("aceite_nome"):
        pdf.ln(8)
        # Bloco de aceite
        pdf.set_fill_color(240, 255, 245)  # Verde bem clarinho
        pdf.rect(M, pdf.get_y(), W, 22, "F")
        pdf.set_fill_color(0, 150, 50)     # Barra verde lateral
        pdf.rect(M, pdf.get_y(), 1.2, 22, "F")

        pdf.set_xy(M + 4, pdf.get_y() + 4)
        pdf.set_font(_FONT, "B", 8)
        pdf.set_text_color(0, 120, 40)
        pdf.cell(W - 8, 4, "ACEITE DIGITAL REGISTRADO", ln=True)

        pdf.set_x(M + 4)
        pdf.set_font(_FONT, "", 10)
        pdf.set_text_color(20, 20, 20)
        aceite_nome = orcamento.get("aceite_nome") or "Cliente"
        aceite_data = orcamento.get("aceite_em")
        if isinstance(aceite_data, str):
            try:
                # Se for ISO string do banco
                dt = datetime.fromisoformat(aceite_data.replace("Z", "+00:00"))
                aceite_data = dt.strftime("%d/%m/%Y %H:%M")
            except:
                pass
        elif hasattr(aceite_data, "strftime"):
            aceite_data = aceite_data.strftime("%d/%m/%Y %H:%M")
        
        txt_aceite = f"Aceito por: {aceite_nome}"
        if aceite_data:
            txt_aceite += f" em {aceite_data}"
        
        pdf.cell(W - 40, 6, _sanitize(txt_aceite), ln=False)

        # Selo OTP se confirmado
        if orcamento.get("aceite_confirmado_otp"):
            pdf.set_font(_FONT, "B", 8)
            pdf.set_text_color(255, 255, 255)
            pdf.set_fill_color(0, 150, 50)
            # Badge "VERIFICADO VIA OTP"
            pdf.set_xy(X2 - 42, pdf.get_y())
            pdf.cell(38, 6, "VERIFICADO VIA OTP", align="C", fill=True, ln=True)
        else:
            pdf.ln(6)

        pdf.set_x(M + 4)
        pdf.set_font(_FONT, "", 7)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(W - 8, 4, _sanitize("Este aceite tem validade jurídica como concordância com os termos desta proposta."), ln=True)

    # ── 6. OBSERVAÇÕES + DOCUMENTOS ──────────────────────────────────────────

    if orcamento.get("observacoes"):
        pdf.ln(6)
        # Linha divisória fina
        y_obs = pdf.get_y()
        pdf.set_draw_color(220, 220, 220)
        pdf.line(M, y_obs, X2, y_obs)
        pdf.ln(3)

        pdf.set_x(M)
        pdf.set_font(_FONT, "B", 7)
        pdf.set_text_color(170, 170, 170)
        pdf.cell(0, 4, "OBSERVAÇÕES", ln=True)

        pdf.set_x(M)
        pdf.set_font(_FONT, "", 8.5)
        pdf.set_text_color(70, 70, 70)
        pdf.multi_cell(W * 0.62, 5, _sanitize(orcamento["observacoes"]))

    documentos = orcamento.get("documentos") or []
    if isinstance(documentos, list) and documentos:
        pdf.ln(6)
        y_docs = pdf.get_y()
        pdf.set_draw_color(220, 220, 220)
        pdf.line(M, y_docs, X2, y_docs)
        pdf.ln(3)

        pdf.set_x(M)
        pdf.set_font(_FONT, "B", 7)
        pdf.set_text_color(170, 170, 170)
        pdf.cell(0, 4, "DOCUMENTOS DA PROPOSTA", ln=True)

        pdf.set_x(M)
        pdf.set_font(_FONT, "", 8.5)
        pdf.set_text_color(70, 70, 70)
        for d in documentos:
            nome = (d or {}).get("nome") or (d or {}).get("documento_nome") or ""
            tipo = (d or {}).get("tipo") or (d or {}).get("documento_tipo") or ""
            versao = (d or {}).get("versao") or (d or {}).get("documento_versao") or ""
            meta = " · ".join([p for p in [tipo, (("v" + str(versao)) if versao else "")] if p])
            linha = f"- {nome}" + (f" ({meta})" if meta else "")
            pdf.multi_cell(W * 0.90, 5, _sanitize(linha))

        link_publico = (orcamento.get("link_publico") or "").strip()
        if link_publico:
            base = (settings.APP_URL or "").rstrip("/")
            url = f"{base}/app/orcamento-publico.html?token={link_publico}"
            pdf.ln(1)
            pdf.set_x(M)
            pdf.set_font(_FONT, "", 8)
            pdf.set_text_color(120, 120, 120)
            pdf.multi_cell(W * 0.90, 4.5, _sanitize(f"Acesse a proposta para abrir os documentos: {url}"))

    # ── 6. RODAPÉ ─────────────────────────────────────────────────────────────

    pdf.set_auto_page_break(False)
    pdf.set_y(-13)

    # Linha fina sobre o rodapé
    pdf.set_draw_color(220, 220, 220)
    pdf.line(M, pdf.get_y() - 1, X2, pdf.get_y() - 1)

    pdf.set_font(_FONT, "", 7)
    pdf.set_text_color(190, 190, 190)
    pdf.set_x(M)
    pdf.cell(W * 0.55, 5, f"Emitido em {data_emi}  |  Válido até {data_val}  |  {_sanitize(empresa.get('nome') or '')}", ln=False)

    pdf.set_font(_FONT, "B", 7)
    pdf.set_text_color(cr, cg, cb)
    pdf.cell(W * 0.45, 5, "Gerado por COTTE", align="R", ln=False)

    return bytes(pdf.output())


# ─────────────────────────────────────────────────────────────────────────────

def salvar_pdf(pdf_bytes: bytes, numero: str) -> str:
    output_dir = "static/pdfs"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{numero.replace('/', '-')}.pdf"
    path = os.path.join(output_dir, filename)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return path
