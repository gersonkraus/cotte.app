"""Renderização de relatórios semânticos em HTML/PDF para o assistente."""

from __future__ import annotations

import html
import json
import logging
import re
from datetime import datetime
from typing import Any

from fpdf import FPDF

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML

    HAS_WEASYPRINT = True
except Exception as exc:  # pragma: no cover - depende do ambiente
    logger.warning("WeasyPrint indisponível para relatório semântico: %s", exc)
    HAS_WEASYPRINT = False


def _safe_hex_color(value: Any, default: str) -> str:
    raw = str(value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", raw):
        return raw.lower()
    return default


def _coerce_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _coerce_theme(payload: dict[str, Any]) -> dict[str, Any]:
    theme = payload.get("theme")
    theme = theme if isinstance(theme, dict) else {}
    brand = payload.get("brand")
    brand = brand if isinstance(brand, dict) else {}
    return {
        "variant": str(theme.get("variant") or "professional"),
        "accent_color": _safe_hex_color(theme.get("accent_color"), "#0f766e"),
        "accent_soft": _safe_hex_color(theme.get("accent_soft"), "#ecfdf5"),
        "text_color": _safe_hex_color(theme.get("text_color"), "#111827"),
        "muted_color": _safe_hex_color(theme.get("muted_color"), "#4b5563"),
        "surface_color": _safe_hex_color(theme.get("surface_color"), "#f8fafc"),
        "border_color": _safe_hex_color(theme.get("border_color"), "#d1d5db"),
        "brand_name": str(brand.get("name") or theme.get("brand_name") or "Assistente COTTE"),
    }


def _slugify(text: Any, default: str = "relatorio_assistente") -> str:
    raw = str(text or "").strip().lower()
    if not raw:
        return default
    normalized = re.sub(r"[^a-z0-9]+", "_", raw)
    normalized = normalized.strip("_")
    return normalized or default


def _format_currency(value: Any) -> str:
    try:
        number = float(value or 0)
    except Exception:
        return str(value or "0")
    return f"R$ {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "Sim" if value else "Não"
    if isinstance(value, (int, float)):
        if abs(float(value)) >= 1000:
            return _format_currency(value)
        return str(round(float(value), 2)).replace(".", ",")
    return str(value)


def _period_label(payload: dict[str, Any]) -> str:
    period_label = str(payload.get("period_label") or "").strip()
    if period_label:
        return period_label
    try:
        period_days = int(payload.get("period_days") or 0)
    except Exception:
        period_days = 0
    if period_days > 0:
        return f"Últimos {period_days} dias"
    return "Período não informado"


def _build_table_html(rows: list[dict[str, Any]], border_color: str) -> str:
    if not rows:
        return "<p>Sem dados tabulares para exportação.</p>"
    headers = list(rows[0].keys())
    head_html = "".join(f"<th>{html.escape(str(header))}</th>" for header in headers)
    body_rows: list[str] = []
    for row in rows[:500]:
        cols = "".join(
            f"<td>{html.escape(_format_value(row.get(header)))}</td>" for header in headers
        )
        body_rows.append(f"<tr>{cols}</tr>")
    return (
        "<table>"
        f"<thead style=\"border-color:{border_color}\"><tr>{head_html}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def render_semantic_report_html(payload: dict[str, Any]) -> str:
    rows = _coerce_rows(payload)
    theme = _coerce_theme(payload)
    metadata = payload.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    insights = payload.get("insights")
    insights = insights if isinstance(insights, list) else []
    summary = str(payload.get("summary") or "")
    title = str(payload.get("title") or "Relatório do Assistente").strip()
    subtitle = str(payload.get("subtitle") or "").strip()
    generated_at = str(payload.get("generated_at") or datetime.now().isoformat())
    filters = payload.get("filters")
    filters = filters if isinstance(filters, dict) else {}
    confidence_hint = metadata.get("confidence_hint")
    confidence_text = (
        f"Confiança sugerida: {round(float(confidence_hint) * 100)}%"
        if isinstance(confidence_hint, (int, float))
        else "Confiança sugerida: não informada"
    )
    filters_text = html.escape(json.dumps(filters, ensure_ascii=False, sort_keys=True))
    insight_html = ""
    if insights:
        items = "".join(
            "<li><strong>"
            + html.escape(str(item.get("title") or "Insight"))
            + ":</strong> "
            + html.escape(str(item.get("detail") or ""))
            + "</li>"
            for item in insights[:6]
            if isinstance(item, dict)
        )
        if items:
            insight_html = f"<section><h2>Insights</h2><ul>{items}</ul></section>"

    subtitle_html = f"<div class=\"subtitle\">{html.escape(subtitle)}</div>" if subtitle else ""
    table_html = _build_table_html(rows, theme["border_color"])
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --accent: {theme["accent_color"]};
      --accent-soft: {theme["accent_soft"]};
      --text: {theme["text_color"]};
      --muted: {theme["muted_color"]};
      --surface: {theme["surface_color"]};
      --border: {theme["border_color"]};
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      margin: 0;
      padding: 32px;
      color: var(--text);
      background: #ffffff;
    }}
    header {{
      background: linear-gradient(135deg, var(--accent-soft), #ffffff 72%);
      border: 1px solid var(--border);
      border-left: 8px solid var(--accent);
      border-radius: 18px;
      padding: 24px 28px;
      margin-bottom: 24px;
    }}
    h1 {{ margin: 0; font-size: 28px; line-height: 1.2; }}
    .subtitle {{ margin-top: 6px; color: var(--muted); font-size: 14px; }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .meta-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 12px 14px;
    }}
    .meta-card__label {{ color: var(--muted); font-size: 12px; margin-bottom: 4px; text-transform: uppercase; letter-spacing: .04em; }}
    .meta-card__value {{ font-size: 14px; font-weight: 600; }}
    section {{ margin-bottom: 22px; }}
    h2 {{
      margin: 0 0 10px;
      font-size: 17px;
      color: var(--accent);
    }}
    .summary {{
      line-height: 1.65;
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 18px;
    }}
    .chip {{
      display: inline-block;
      background: var(--accent-soft);
      color: var(--accent);
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      margin-right: 8px;
      margin-bottom: 8px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      overflow: hidden;
      border-radius: 12px;
    }}
    thead tr {{
      background: var(--accent-soft);
    }}
    th, td {{
      border: 1px solid var(--border);
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }}
    tbody tr:nth-child(even) {{ background: #f9fafb; }}
    ul {{ margin: 0; padding-left: 18px; }}
    footer {{
      margin-top: 28px;
      padding-top: 16px;
      border-top: 1px solid var(--border);
      color: var(--muted);
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <header>
    <div class="chip">{html.escape(theme["brand_name"])}</div>
    <div class="chip">{html.escape(_period_label(payload))}</div>
    <div class="chip">{html.escape(confidence_text)}</div>
    <h1>{html.escape(title)}</h1>
    {subtitle_html}
    <div class="meta-grid">
      <div class="meta-card">
        <div class="meta-card__label">Gerado em</div>
        <div class="meta-card__value">{html.escape(generated_at)}</div>
      </div>
      <div class="meta-card">
        <div class="meta-card__label">Linhas</div>
        <div class="meta-card__value">{len(rows)}</div>
      </div>
      <div class="meta-card">
        <div class="meta-card__label">Filtros</div>
        <div class="meta-card__value">{filters_text or 'Sem filtros'}</div>
      </div>
    </div>
  </header>
  <section>
    <h2>Resumo Executivo</h2>
    <div class="summary">{html.escape(summary or 'Sem resumo disponível.')}</div>
  </section>
  {insight_html}
  <section>
    <h2>Detalhamento</h2>
    {table_html}
  </section>
  <footer>
    Relatório gerado pelo assistente com contrato semântico auditável.
  </footer>
</body>
</html>"""


def _render_pdf_fallback(payload: dict[str, Any]) -> bytes:
    rows = _coerce_rows(payload)
    theme = _coerce_theme(payload)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.set_margins(12, 12, 12)

    accent = theme["accent_color"].lstrip("#")
    r = int(accent[0:2], 16)
    g = int(accent[2:4], 16)
    b = int(accent[4:6], 16)
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, str(payload.get("title") or "Relatório do Assistente"), ln=True, fill=True)

    pdf.ln(4)
    pdf.set_text_color(20, 20, 20)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, str(payload.get("summary") or "Sem resumo disponível."))
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, f"Período: {_period_label(payload)}", ln=True)
    pdf.cell(0, 6, f"Gerado em: {payload.get('generated_at') or datetime.now().isoformat()}", ln=True)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(r, g, b)
    pdf.cell(0, 8, "Detalhamento", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(20, 20, 20)
    if not rows:
        pdf.multi_cell(0, 6, "Sem dados tabulares para exportação.")
    else:
        headers = list(rows[0].keys())
        for row in rows[:120]:
            parts = [f"{header}: {_format_value(row.get(header))}" for header in headers]
            pdf.multi_cell(0, 5.5, " | ".join(parts))
            pdf.ln(1)
    return bytes(pdf.output())


def render_semantic_report_pdf(payload: dict[str, Any]) -> bytes:
    html_content = render_semantic_report_html(payload)
    if HAS_WEASYPRINT:
        try:
            return HTML(string=html_content).write_pdf()
        except Exception as exc:  # pragma: no cover - depende do ambiente
            logger.warning("Falha ao gerar PDF semântico com WeasyPrint: %s", exc)
    return _render_pdf_fallback(payload)


def build_semantic_report_filename(payload: dict[str, Any], ext: str) -> str:
    title = payload.get("title") or "relatorio_assistente"
    return f"{_slugify(title)}.{ext.lstrip('.')}"
