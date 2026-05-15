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

            img_url = item.get("imagem_url")
            if img_url:
                item["imagem_url"] = _otimizar_imagem_portfolio(img_url, max_width=150)


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
    """Ajusta o logo_url e capa_portfolio_url para caminhos locais absolutos ou relativos ao template_dir."""
    try:
        for campo in ["logo_url", "capa_portfolio_url"]:
            img_url = empresa.get(campo)
            if not img_url:
                continue
            
            img_str = str(img_url).strip()
            if not img_str or img_str.startswith("http"):
                continue
            
            # Se já for um caminho absoluto que existe, não mexe
            if os.path.isabs(img_str) and os.path.exists(img_str):
                empresa[f"_{campo}_path_completo"] = img_str
                continue
                
            # Base do projeto (onde está o static/)
            # Em produção (Railway), os arquivos estão em /app
            # pdf_service.py está em /app/app/services/pdf_service.py
            base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
            
            # Tenta localizar o arquivo no disco
            # Remove barra inicial se houver para não quebrar o join
            rel_path = img_str.lstrip("/")
            full_path = os.path.join(base_dir, rel_path)
            
            if os.path.exists(full_path):
                # Para o WeasyPrint com base_url=template_dir (/app/app/templates), 
                # o caminho de 'static' é '../../static'
                empresa[campo] = os.path.join("..", "..", rel_path)
                empresa[f"_{campo}_path_completo"] = full_path
        
        return empresa
    except Exception as e:
        logger.error(f"Erro ao normalizar imagens da empresa: {e}")
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

    logo_url = empresa.get("logo_url")
    logo_w = 0
    if logo_url:
        try:
            image_data = None
            # Primeiro, tenta o caminho local completo, se existir
            logo_path_completo = empresa.get("_logo_url_path_completo")
            if logo_path_completo and os.path.exists(logo_path_completo):
                with open(logo_path_completo, "rb") as f:
                    image_data = f.read()
            # Senão, se for uma URL HTTP, baixa a imagem
            elif str(logo_url).startswith("http"):
                import requests
                response = requests.get(logo_url, timeout=5)
                response.raise_for_status()
                image_data = response.content

            if image_data:
                import io
                from PIL import Image

                img = Image.open(io.BytesIO(image_data))
                img_w, img_h = img.size
                
                # Calcula a largura proporcional para uma altura fixa de 14
                aspect_ratio = img_w / img_h
                logo_render_h = 14
                logo_render_w = aspect_ratio * logo_render_h
                
                pdf.image(io.BytesIO(image_data), x=M, y=M, h=logo_render_h)
                logo_w = logo_render_w  # Usa a largura real calculada

        except Exception as e:
            logger.warning(f"FPDF2: Falha ao carregar o logo '{logo_url}': {e}")
            logo_w = 0

    nome_x = M + logo_w + (4 if logo_w else 0)

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
        
        has_image = bool(item.get("imagem_url"))
        desc_limit = 45 if has_image else 58
        desc  = _sanitize(item.get("descricao") or "")[:desc_limit]

        
        imagem_url = item.get("imagem_url")
        linha_h = 28 if imagem_url else 7  # Aumenta a altura da linha para a imagem
        offset_x = 28 if imagem_url else 0 # Aumenta o espaço para a imagem

        pdf.set_x(M)
        pdf.cell(C_DESC, linha_h, "", fill=True, ln=False)
        pdf.set_xy(M, pdf.get_y()) # Reset Y

        if imagem_url:
            try:
                import base64
                import io
                from PIL import Image

                # Lógica para tratar base64 ou baixar de URL
                image_data = None
                if str(imagem_url).startswith('data:image'):
                    header, encoded = imagem_url.split(",", 1)
                    image_data = base64.b64decode(encoded)
                    img_format = header.split('/')[1].split(';')[0].upper()
                elif str(imagem_url).startswith('http'):
                    import requests
                    response = requests.get(imagem_url, timeout=5)
                    response.raise_for_status()
                    image_data = response.content
                    img_format = Image.open(io.BytesIO(image_data)).format.upper()

                if image_data:
                    img = Image.open(io.BytesIO(image_data))
                    img_w, img_h = img.size
                    
                    # Calcula dimensões proporcionais para caber em 24x24 (contain)
                    max_w, max_h = 24, 24
                    ratio = min(max_w / img_w, max_h / img_h)
                    render_w, render_h = img_w * ratio, img_h * ratio
                    
                    # Centraliza a imagem no espaço de 28x28
                    pos_x = M + 2 + (max_w - render_w) / 2
                    pos_y = pdf.get_y() + 2 + (max_h - render_h) / 2

                    pdf.image(
                        io.BytesIO(image_data),
                        x=pos_x,
                        y=pos_y,
                        w=render_w,
                        h=render_h,
                        type=img_format if img_format in ['JPG', 'JPEG', 'PNG'] else 'JPEG'
                    )
            except Exception as e:
                logger.warning(f"FPDF2: Falha ao renderizar imagem do item: {e}")
        
        pdf.set_xy(M + offset_x, pdf.get_y())
        pdf.cell(C_DESC - offset_x, linha_h, f"  {desc}", fill=False, ln=False) # fill=False para não cobrir imagem
        
        pdf.set_xy(M + C_DESC, pdf.get_y())
        pdf.cell(C_QTD,  linha_h, qtd_s, align="C", fill=True, ln=False)
        pdf.cell(C_UNIT, linha_h, _brl(item.get("valor_unit") or 0), align="R", fill=True, ln=False)
        pdf.set_font(_FONT, "B", 9)
        pdf.cell(C_TOT,  linha_h, _brl(item.get("total") or 0), align="R", fill=True, ln=True)

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

def _otimizar_imagem_portfolio(url: str, max_width=400) -> str:
    """Baixa e redimensiona a imagem para base64 para uso inline no HTML/PDF, reduzindo peso e evitando bloqueios CORS."""
    if not url or not str(url).startswith("http"):
        return url
    
    try:
        import requests
        from PIL import Image
        import io
        import base64
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        img = Image.open(io.BytesIO(response.content))
        # Convert to RGB to avoid alpha channel issues with JPEG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # Resize if width > max_width
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int((float(img.height) * float(ratio)))
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=75)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        logger.warning(f"Erro ao otimizar imagem {url}: {e}")
        return url

def gerar_html_portfolio(portfolio_dict: dict, empresa: dict) -> str:
    """Gera o HTML do portfolio a partir do jinja2."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    
    # Custom filters
    env.filters['brl'] = _brl
    
    # Otimizar imagens do portfolio (galeria usa largura maior para destaque no PDF)
    layout = (portfolio_dict.get("layout") or "compacto").strip().lower()
    max_img_w = 720 if layout == "galeria" else 400
    if "categorias" in portfolio_dict:
        for cat in portfolio_dict["categorias"]:
            for item in cat.get("itens", []):
                if item.get("imagem_url"):
                    item["imagem_url"] = _otimizar_imagem_portfolio(
                        item["imagem_url"], max_width=max_img_w
                    )
                    
    # Normalizar logo e capa
    empresa_norm = _normalizar_logo_url(empresa.copy())
    
    if empresa_norm.get("logo_url") and str(empresa_norm["logo_url"]).startswith("http"):
        empresa_norm["logo_url"] = _otimizar_imagem_portfolio(empresa_norm["logo_url"], max_width=400)
        
    if empresa_norm.get("capa_portfolio_url") and str(empresa_norm["capa_portfolio_url"]).startswith("http"):
        empresa_norm["capa_portfolio_url"] = _otimizar_imagem_portfolio(empresa_norm["capa_portfolio_url"], max_width=1200)
    
    template = env.get_template("portfolio.html")
    html_out = template.render(portfolio=portfolio_dict, empresa=empresa_norm)
    return html_out

def gerar_pdf_portfolio(portfolio_dict: dict, empresa: dict) -> bytes:
    """Gera PDF do portfolio via weasyprint."""
    try:
        from weasyprint import HTML, CSS
        html_str = gerar_html_portfolio(portfolio_dict, empresa)
        
        # Base url for local static assets
        base_url = f"file://{os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))}/"
        
        pdf_bytes = HTML(string=html_str, base_url=base_url).write_pdf(
            presentational_hints=True,
            optimize_size=('fonts', 'images')
        )
        return pdf_bytes
    except Exception as e:
        logger.error(f"Erro ao gerar PDF do portfólio via weasyprint: {e}")
        raise e

