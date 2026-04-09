# Serviço de e-mail — API Brevo (HTTPS, funciona na Railway) ou SMTP
import asyncio
import base64
import concurrent.futures
import logging
import re
import smtplib
from html import escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

import httpx

from app.core.config import settings

# Timeout para conexão SMTP (Railway costuma bloquear porta 587)
SMTP_TIMEOUT = 25
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def brevo_api_habilitado() -> bool:
    """True se a API Brevo estiver configurada (recomendado na Railway)."""
    return bool((settings.BREVO_API_KEY or "").strip())


def smtp_habilitado() -> bool:
    """True se o SMTP estiver configurado (host, user e senha)."""
    return bool(
        settings.SMTP_HOST and settings.SMTP_USER and (settings.SMTP_PASS or "").strip()
    )


def email_habilitado() -> bool:
    """True se houver algum meio de envio (API Brevo ou SMTP)."""
    return brevo_api_habilitado() or smtp_habilitado()


# ── Pool de threads para SMTP não-bloqueante ──────────────────────────────────
# smtplib.SMTP() é síncrono e bloqueante. Em endpoints async do FastAPI,
# isso congela o event loop. Usamos um ThreadPoolExecutor dedicado para
# executar a conexão SMTP em thread separada quando estamos em contexto async.
_SMTP_THREAD_POOL = concurrent.futures.ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="smtp"
)


def _esta_em_event_loop() -> bool:
    """True se existe um event loop asyncio rodando (contexto async)."""
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


def _enviar_via_smtp(mensagem: MIMEMultipart) -> None:
    """
    Envia e-mail via SMTP, executando em thread pool se estivermos em contexto async.

    Em endpoints sync (def normal), a execução é direta (comportamento original).
    Em endpoints async (async def), a execução é delegada ao ThreadPoolExecutor
    para não bloquear o event loop.
    """

    def _smtp_send():
        with smtplib.SMTP(
            settings.SMTP_HOST, settings.SMTP_PORT, timeout=SMTP_TIMEOUT
        ) as srv:
            srv.starttls()
            srv.login(settings.SMTP_USER, settings.SMTP_PASS)
            srv.sendmail(mensagem["From"], mensagem["To"], mensagem.as_string())

    if _esta_em_event_loop():
        future = _SMTP_THREAD_POOL.submit(_smtp_send)
        future.result(timeout=SMTP_TIMEOUT + 10)
    else:
        _smtp_send()


def _parse_sender() -> tuple[str, str]:
    """Extrai (email, nome) de SMTP_FROM. Ex: 'COTTE <noreply@x.com>' -> ('noreply@x.com', 'COTTE')."""
    raw = (settings.SMTP_FROM or settings.SMTP_USER or "").strip()
    if not raw:
        return "", ""
    match = re.match(r"^(.+?)\s*<([^>]+)>$", raw)
    if match:
        return match.group(2).strip(), (match.group(1) or "").strip()[:70]
    return raw, ""


def _formatar_brl(valor: float | None) -> str:
    if valor is None:
        return "A combinar"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _montar_html_email_orcamento(
    cliente_nome: str,
    numero_orcamento: str,
    empresa_nome: str,
    link_proposta: str,
    validade_texto: str | None = None,
    valor_total: float | None = None,
    contato_telefone: str | None = None,
    contato_email: str | None = None,
    responsavel_nome: str | None = None,
    link_pdf: str | None = None,
    assinatura_email: str | None = None,
    documentos: list[dict] | None = None,
) -> str:
    cliente_nome_safe = escape((cliente_nome or "Cliente").strip())
    numero_safe = escape((numero_orcamento or "-").strip())
    empresa_safe = escape((empresa_nome or "Prestador").strip())
    link_proposta_safe = escape((link_proposta or "").strip(), quote=True)
    validade_safe = escape((validade_texto or "").strip())
    valor_safe = _formatar_brl(valor_total)

    contato_telefone_safe = escape((contato_telefone or "").strip())
    contato_email_safe = escape((contato_email or "").strip())
    responsavel_safe = escape((responsavel_nome or "").strip())

    link_pdf_value = (link_pdf or "").strip()
    link_pdf_safe = escape(link_pdf_value, quote=True) if link_pdf_value else ""

    assinatura_safe = escape((assinatura_email or "").strip())
    bloco_assinatura = ""
    if assinatura_safe:
        bloco_assinatura = f"""
            <p style="margin:0 0 8px 0;font-size:14px;color:#333;line-height:1.7;white-space:pre-line;">{assinatura_safe}</p>
"""

    linha_responsavel = ""
    if responsavel_safe:
        linha_responsavel = f"""
          <tr>
            <td class="label">Responsável</td>
            <td class="value">{responsavel_safe}</td>
          </tr>
"""

    linha_valor = ""
    if valor_total is not None:
        linha_valor = f"""
          <tr>
            <td class="label">Valor Total</td>
            <td class="value total">{valor_safe}</td>
          </tr>
"""

    linha_validade = ""
    if validade_safe:
        linha_validade = f"""
          <tr>
            <td class="label">Validade</td>
            <td class="value">{validade_safe}</td>
          </tr>
"""

    bloco_pdf = ""
    if link_pdf_safe:
        bloco_pdf = f"""
      <p style="text-align: center;">
        <a href="{link_pdf_safe}" class="btn-secondary">Baixar PDF</a>
      </p>
"""

    bloco_documentos = ""
    if documentos:
        itens = []
        for d in documentos:
            nome = escape((d.get("nome") or "Documento").strip())
            url = (d.get("url") or "").strip()
            url_safe = escape(url, quote=True) if url else ""
            if url_safe:
                itens.append(
                    f'<li style="margin:0 0 8px 0;"><a href="{url_safe}" target="_blank" style="color:#0d6efd;text-decoration:none;font-weight:600;">{nome}</a></li>'
                )
            else:
                itens.append(
                    f'<li style="margin:0 0 8px 0;color:#222;font-weight:600;">{nome}</li>'
                )
        bloco_documentos = f"""
      <div style="margin:0 0 22px 0;">
        <h3 style="margin:0 0 10px 0;color:#0d6efd;font-size:14px;text-transform:uppercase;letter-spacing:.08em;">Documentos complementares</h3>
        <ul style="margin:0;padding:0 0 0 18px;font-size:14px;line-height:1.65;color:#222;">
          {"".join(itens)}
        </ul>
      </div>
"""

    linha_telefone = ""
    if contato_telefone_safe:
        linha_telefone = f"""
        <strong>WhatsApp:</strong>
        <a href="https://wa.me/{contato_telefone_safe.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")}" class="whatsapp">{contato_telefone_safe}</a><br>
"""

    linha_email = ""
    if contato_email_safe:
        linha_email = f"""
        <strong>E-mail:</strong> {contato_email_safe}<br>
"""

    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Orçamento {numero_safe} disponível</title>
    <style type="text/css">
        body {{ margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; color: #1e293b; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
        table {{ border-collapse: collapse; }}
        img {{ border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; -ms-interpolation-mode: bicubic; }}
        a {{ color: #0284c7; text-decoration: none; }}
        .btn-primary {{ display: inline-block; background-color: #0284c7; color: #ffffff !important; padding: 14px 32px; border-radius: 8px; font-weight: 600; text-align: center; text-decoration: none; margin: 20px 0; }}
        .btn-secondary {{ display: inline-block; background-color: #f1f5f9; color: #475569 !important; padding: 10px 24px; border-radius: 6px; font-weight: 500; text-align: center; text-decoration: none; margin: 5px 0; border: 1px solid #e2e8f0; }}
        .card {{ background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); overflow: hidden; max-width: 600px; margin: 40px auto; }}
        .header {{ padding: 32px; text-align: center; border-bottom: 1px solid #f1f5f9; }}
        .content {{ padding: 32px; }}
        .footer {{ padding: 24px; text-align: center; font-size: 13px; color: #64748b; background-color: #f8fafc; border-top: 1px solid #f1f5f9; }}
        .info-box {{ background-color: #f8fafc; border-radius: 12px; padding: 24px; margin: 24px 0; border: 1px solid #f1f5f9; }}
        .label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; font-weight: 700; margin-bottom: 4px; }}
        .value {{ font-size: 15px; font-weight: 600; color: #0f172a; }}
        .total-value {{ font-size: 20px; color: #0284c7; font-weight: 700; }}
        @media screen and (max-width: 600px) {{
            .card {{ margin: 10px; }}
            .content, .header {{ padding: 20px; }}
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <div style="font-size: 14px; font-weight: 700; color: #0284c7; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px;">{empresa_safe}</div>
            <h1 style="font-size: 24px; margin: 0; color: #0f172a;">Seu Orçamento está pronto</h1>
        </div>
        
        <div class="content">
            <p style="margin: 0 0 16px 0; font-size: 16px;">Olá, <strong>{cliente_nome_safe}</strong>,</p>
            <p style="margin: 0; line-height: 1.6; color: #475569;">
                Temos o prazer de enviar os detalhes da proposta comercial solicitada. 
                Nossa equipe preparou uma solução sob medida para atender às suas necessidades.
            </p>

            <div class="info-box">
                <table width="100%" cellspacing="0" cellpadding="0" border="0">
                    <tr>
                        <td width="50%" style="padding-bottom: 16px;">
                            <div class="label">Nº do Orçamento</div>
                            <div class="value">{numero_safe}</div>
                        </td>
                        <td width="50%" style="padding-bottom: 16px; text-align: right;">
                            <div class="label">Status</div>
                            <div class="value" style="color: #059669;">Disponível</div>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding-bottom: 8px;">
                            <div class="label">Valor Total</div>
                            <div class="total-value">{valor_safe}</div>
                        </td>
                        <td style="padding-bottom: 8px; text-align: right;">
                            <div class="label">Validade</div>
                            <div class="value" style="color: #dc2626;">{validade_safe}</div>
                        </td>
                    </tr>
                    {linha_responsavel}
                </table>
            </div>

            <div style="text-align: center; margin: 32px 0;">
                <a href="{link_proposta_safe}" class="btn-primary">Ver Orçamento Completo</a>
                <p style="font-size: 12px; color: #94a3b8; margin-top: 12px;">Visualize online para aprovar ou solicitar alterações.</p>
            </div>

            {bloco_pdf}
            {bloco_documentos}

            <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid #f1f5f9; color: #475569; line-height: 1.6; font-size: 14px;">
                {bloco_assinatura}
                <p style="margin: 16px 0 0 0;">
                    Se tiver qualquer dúvida, estamos à disposição via {contato_email_safe if contato_email_safe else 'e-mail'} 
                    {f'ou pelo WhatsApp {contato_telefone_safe}' if contato_telefone_safe else ''}.
                </p>
            </div>
        </div>

        <div class="footer">
            <p style="margin: 0 0 8px 0;">© 2026 <strong>{empresa_safe}</strong>. Todos os direitos reservados.</p>
            <p style="margin: 0; opacity: 0.6; font-size: 11px;">Enviado via plataforma COTTE</p>
        </div>
    </div>
</body>
</html>
"""

def _enviar_via_brevo_api(
    destinatario: str,
    assunto: str,
    html: str,
    texto: str | None = None,
    attachment_filename: str | None = None,
    attachment_base64: str | None = None,
    attachments: list[dict] | None = None,
) -> tuple[bool, str]:
    """
    Envia e-mail pela API REST da Brevo (HTTPS). Retorna (True, "") ou (False, "erro").
    """
    if not brevo_api_habilitado():
        return False, "BREVO_API_KEY não configurada"
    sender_email, sender_name = _parse_sender()
    if not sender_email:
        return False, "Configure SMTP_FROM (ex: COTTE <noreply@seudominio.com>)"
    payload = {
        "sender": {"email": sender_email, "name": sender_name or settings.APP_NAME},
        "to": [{"email": destinatario}],
        "subject": assunto,
        "htmlContent": html,
    }
    if texto:
        payload["textContent"] = texto
    anexos = []
    if attachment_filename and attachment_base64:
        anexos.append({"name": attachment_filename, "content": attachment_base64})
    if attachments:
        anexos.extend(attachments)
    if anexos:
        payload["attachment"] = anexos
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                BREVO_API_URL,
                headers={
                    "api-key": (settings.BREVO_API_KEY or "").strip(),
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if r.status_code in (200, 201):
            return True, ""
        try:
            err = r.json()
            msg = err.get("message", err.get("code", r.text)) or r.text
        except Exception:
            msg = r.text or str(r.status_code)
        return False, f"Brevo API {r.status_code}: {msg}"
    except Exception as e:
        logging.exception("Erro ao chamar API Brevo: %s", e)
        return False, str(e)


def enviar_orcamento_por_email(
    destinatario: str,
    cliente_nome: str,
    numero_orcamento: str,
    empresa_nome: str,
    link_publico: str,
    pdf_bytes: bytes | None = None,
    anexar_pdf: bool = False,
    app_url: str = None,
    validade_texto: str | None = None,
    valor_total: float | None = None,
    contato_prestador: str | None = None,
    contato_email: str | None = None,
    responsavel_nome: str | None = None,
    link_pdf: str | None = None,
    assinatura_email: str | None = None,
    documentos: list[dict] | None = None,
    anexos_extra: list[dict] | None = None,
) -> bool:
    """
    Envia e-mail ao cliente com link para visualizar/aceitar.
    O anexo em PDF é opcional e controlado por configuração da empresa.
    Usa API Brevo se BREVO_API_KEY estiver definida (recomendado na Railway), senão SMTP.
    """
    if not email_habilitado():
        logging.warning(
            "E-mail não configurado (defina BREVO_API_KEY ou SMTP_HOST/SMTP_USER/SMTP_PASS)."
        )
        return False

    base_url = (app_url or settings.APP_URL).rstrip("/")
    link_proposta = f"{base_url}/app/orcamento-publico.html?token={link_publico}"
    assunto = f"Orçamento {numero_orcamento} — {empresa_nome}"
    link_pdf_full = None
    if link_pdf:
        pdf = link_pdf.strip()
        if pdf.startswith("http://") or pdf.startswith("https://"):
            link_pdf_full = pdf
        elif pdf.startswith("/"):
            link_pdf_full = f"{base_url}{pdf}"
    elif (link_publico or "").strip():
        # Fallback estável: endpoint público que gera o PDF sob demanda.
        link_pdf_full = f"{base_url}/o/{link_publico.strip()}/pdf"

    html = _montar_html_email_orcamento(
        cliente_nome=cliente_nome,
        numero_orcamento=numero_orcamento,
        empresa_nome=empresa_nome,
        link_proposta=link_proposta,
        validade_texto=validade_texto,
        valor_total=valor_total,
        contato_telefone=contato_prestador,
        contato_email=contato_email,
        responsavel_nome=responsavel_nome,
        link_pdf=link_pdf_full,
        assinatura_email=assinatura_email,
        documentos=documentos,
    )

    if brevo_api_habilitado():
        logging.info(
            "Enviando orçamento por e-mail para %s via API Brevo", destinatario
        )
        attachments = []
        if anexar_pdf and pdf_bytes:
            attachments.append(
                {
                    "name": f"orcamento-{numero_orcamento.replace('/', '-')}.pdf",
                    "content": base64.b64encode(pdf_bytes).decode("ascii"),
                }
            )
        elif anexar_pdf:
            logging.warning(
                "Configuração de anexo ativa, mas PDF indisponível para o orçamento %s; enviando sem anexo.",
                numero_orcamento,
            )
        if anexos_extra:
            for a in anexos_extra:
                content = a.get("content") or b""
                if not content:
                    continue
                attachments.append(
                    {
                        "name": a.get("filename") or "documento.pdf",
                        "content": base64.b64encode(content).decode("ascii"),
                    }
                )
        ok, err = _enviar_via_brevo_api(
            destinatario,
            assunto,
            html,
            attachments=attachments if attachments else None,
        )
        if ok:
            logging.info(
                "Orçamento %s enviado por e-mail para %s",
                numero_orcamento,
                destinatario,
            )
            return True
        logging.exception(
            "Falha ao enviar orçamento por e-mail para %s: %s", destinatario, err
        )
        return False

    logging.info(
        "Enviando orçamento por e-mail para %s via SMTP %s:%s",
        destinatario,
        settings.SMTP_HOST,
        settings.SMTP_PORT,
    )
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
        msg["To"] = destinatario
        msg.attach(MIMEText(html, "html"))
        if anexar_pdf and pdf_bytes:
            part = MIMEBase("application", "pdf")
            part.set_payload(pdf_bytes)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=f"orcamento-{numero_orcamento.replace('/', '-')}.pdf",
            )
            msg.attach(part)
        elif anexar_pdf:
            logging.warning(
                "Configuração de anexo ativa, mas PDF indisponível para o orçamento %s; enviando sem anexo.",
                numero_orcamento,
            )
        if anexos_extra:
            for a in anexos_extra:
                content = a.get("content") or b""
                if not content:
                    continue
                mime = (a.get("mime") or "application/pdf").split("/", 1)
                maintype = mime[0] if len(mime) > 1 else "application"
                subtype = mime[1] if len(mime) > 1 else "octet-stream"
                part = MIMEBase(maintype, subtype)
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=a.get("filename") or "documento.pdf",
                )
                msg.attach(part)
        _enviar_via_smtp(msg)
        logging.info(
            "Orçamento %s enviado por e-mail para %s", numero_orcamento, destinatario
        )
        return True
    except Exception as e:
        logging.exception(
            "Falha ao enviar orçamento por e-mail para %s: %s", destinatario, e
        )
        return False


def _montar_html_email_confirmacao_aceite(
    cliente_nome: str,
    aceite_nome: str,
    numero_orcamento: str,
    empresa_nome: str,
    valor_total: float | None = None,
    contato_telefone: str | None = None,
    contato_email_empresa: str | None = None,
    assinatura_email: str | None = None,
) -> str:
    cliente_safe = escape((cliente_nome or aceite_nome or "Cliente").strip())
    aceite_safe = escape((aceite_nome or "").strip())
    numero_safe = escape((numero_orcamento or "-").strip())
    empresa_safe = escape((empresa_nome or "a empresa").strip())
    valor_safe = _formatar_brl(valor_total) if valor_total else None
    tel_safe = escape((contato_telefone or "").strip())
    email_emp_safe = escape((contato_email_empresa or "").strip())

    assinatura_safe = escape((assinatura_email or "").strip())
    bloco_assinatura = ""
    if assinatura_safe:
        bloco_assinatura = f"""
            <p style="margin:0 0 8px 0;font-size:14px;color:#333;line-height:1.7;white-space:pre-line;">{assinatura_safe}</p>
"""

    linha_valor = ""
    if valor_safe:
        linha_valor = f"""
          <tr>
            <td class="label">Valor</td>
            <td class="value total">{valor_safe}</td>
          </tr>
"""

    tel_digits = tel_safe.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
    linha_telefone = ""
    if tel_safe:
        linha_telefone = f"""
        <strong>WhatsApp:</strong>
        <a href="https://wa.me/{tel_digits}" class="whatsapp">{tel_safe}</a><br>
"""

    linha_email = ""
    if email_emp_safe:
        linha_email = f"""
        <strong>E-mail:</strong> {email_emp_safe}<br>
"""

    assinatura_aceite = ""
    if aceite_safe:
        assinatura_aceite = f"""
      <div style="margin:24px 0;padding:14px 16px;background-color:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;">
        <p style="margin:0;font-size:14px;line-height:1.6;color:#166534;">
          Aceite registrado por: <strong>{aceite_safe}</strong>
        </p>
      </div>
"""

    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Aceite confirmado - Orçamento {numero_safe}</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background-color: #f4f6f9;
      font-family: 'Segoe UI', Arial, sans-serif;
    }}
    .container {{
      max-width: 600px;
      margin: 20px auto;
      background-color: #ffffff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }}
    .header {{
      background-color: #0d6efd;
      color: white;
      padding: 25px 30px;
      text-align: center;
    }}
    .logo {{
      font-size: 28px;
      font-weight: bold;
      margin: 0;
    }}
    .content {{
      padding: 30px;
    }}
    .greeting {{
      font-size: 18px;
      color: #333;
      margin-bottom: 20px;
    }}
    .highlight-box {{
      background-color: #f8f9fa;
      border-left: 5px solid #0d6efd;
      padding: 20px;
      margin: 25px 0;
      border-radius: 8px;
    }}
    .summary-table {{
      width: 100%;
      border-collapse: collapse;
    }}
    .summary-table td {{
      padding: 12px 0;
      border-bottom: 1px solid #eee;
    }}
    .label {{
      color: #666;
      font-weight: 500;
    }}
    .value {{
      text-align: right;
      font-weight: 600;
      color: #222;
    }}
    .total {{
      font-size: 22px;
      color: #0d6efd;
      font-weight: bold;
    }}
    .footer {{
      background-color: #f8f9fa;
      padding: 25px 30px;
      font-size: 14px;
      color: #666;
      text-align: center;
      border-top: 1px solid #eee;
    }}
    .whatsapp {{
      color: #25D366;
      font-weight: 600;
    }}
    @media only screen and (max-width: 600px) {{
      .container {{
        margin: 10px;
        border-radius: 8px;
      }}
      .content {{
        padding: 20px;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header" style="background-color:#0d6efd;color:#ffffff;padding:25px 30px;text-align:center;">
      <h1 class="logo" style="color:#ffffff !important;font-size:28px;font-weight:bold;margin:0;">cotte.app</h1>
      <p style="margin:8px 0 0 0;opacity:0.9;color:#ffffff !important;">{empresa_safe} - Confirmação de aceite</p>
    </div>
    <div class="content">
      <p class="greeting">Olá, {cliente_safe},</p>
      <p>Seu aceite do orçamento <strong>{numero_safe}</strong> foi registrado com sucesso!</p>
      <p>Em breve <strong>{empresa_safe}</strong> entrará em contato para confirmar os próximos passos.</p>
      <div class="highlight-box">
        <h3 style="margin-top: 0; color: #0d6efd;">Resumo</h3>
        <table class="summary-table">
          <tr>
            <td class="label">Orçamento</td>
            <td class="value">{numero_safe}</td>
          </tr>
{linha_valor}
          <tr>
            <td class="label">Empresa</td>
            <td class="value">{empresa_safe}</td>
          </tr>
        </table>
      </div>
{assinatura_aceite}
{bloco_assinatura}
      <p>Qualquer dúvidas, entre em contato diretamente com {empresa_safe}:</p>
{linha_telefone}
{linha_email}
      <p style="margin-top: 30px;">
        Um abraço,<br>
        <strong>{empresa_safe}</strong>
      </p>
    </div>
    <div class="footer">
      <p style="margin: 0; font-size: 13px;">
        Este e-mail foi gerado automaticamente pela plataforma <strong>Cotte.app</strong>.<br>
        © 2026 Cotte.app
      </p>
    </div>
  </div>
</body>
</html>
"""

def _enviar_via_brevo_api(
    destinatario: str,
    assunto: str,
    html: str,
    texto: str | None = None,
    attachment_filename: str | None = None,
    attachment_base64: str | None = None,
    attachments: list[dict] | None = None,
) -> tuple[bool, str]:
    """
    Envia e-mail pela API REST da Brevo (HTTPS). Retorna (True, "") ou (False, "erro").
    """
    if not brevo_api_habilitado():
        return False, "BREVO_API_KEY não configurada"
    sender_email, sender_name = _parse_sender()
    if not sender_email:
        return False, "Configure SMTP_FROM (ex: COTTE <noreply@seudominio.com>)"
    payload = {
        "sender": {"email": sender_email, "name": sender_name or settings.APP_NAME},
        "to": [{"email": destinatario}],
        "subject": assunto,
        "htmlContent": html,
    }
    if texto:
        payload["textContent"] = texto
    anexos = []
    if attachment_filename and attachment_base64:
        anexos.append({"name": attachment_filename, "content": attachment_base64})
    if attachments:
        anexos.extend(attachments)
    if anexos:
        payload["attachment"] = anexos
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                BREVO_API_URL,
                headers={
                    "api-key": (settings.BREVO_API_KEY or "").strip(),
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if r.status_code in (200, 201):
            return True, ""
        try:
            err = r.json()
            msg = err.get("message", err.get("code", r.text)) or r.text
        except Exception:
            msg = r.text or str(r.status_code)
        return False, f"Brevo API {r.status_code}: {msg}"
    except Exception as e:
        logging.exception("Erro ao chamar API Brevo: %s", e)
        return False, str(e)


def enviar_orcamento_por_email(
    destinatario: str,
    cliente_nome: str,
    numero_orcamento: str,
    empresa_nome: str,
    link_publico: str,
    pdf_bytes: bytes | None = None,
    anexar_pdf: bool = False,
    app_url: str = None,
    validade_texto: str | None = None,
    valor_total: float | None = None,
    contato_prestador: str | None = None,
    contato_email: str | None = None,
    responsavel_nome: str | None = None,
    link_pdf: str | None = None,
    assinatura_email: str | None = None,
    documentos: list[dict] | None = None,
    anexos_extra: list[dict] | None = None,
) -> bool:
    """
    Envia e-mail ao cliente com link para visualizar/aceitar.
    O anexo em PDF é opcional e controlado por configuração da empresa.
    Usa API Brevo se BREVO_API_KEY estiver definida (recomendado na Railway), senão SMTP.
    """
    if not email_habilitado():
        logging.warning(
            "E-mail não configurado (defina BREVO_API_KEY ou SMTP_HOST/SMTP_USER/SMTP_PASS)."
        )
        return False

    base_url = (app_url or settings.APP_URL).rstrip("/")
    link_proposta = f"{base_url}/app/orcamento-publico.html?token={link_publico}"
    assunto = f"Orçamento {numero_orcamento} — {empresa_nome}"
    link_pdf_full = None
    if link_pdf:
        pdf = link_pdf.strip()
        if pdf.startswith("http://") or pdf.startswith("https://"):
            link_pdf_full = pdf
        elif pdf.startswith("/"):
            link_pdf_full = f"{base_url}{pdf}"
    elif (link_publico or "").strip():
        # Fallback estável: endpoint público que gera o PDF sob demanda.
        link_pdf_full = f"{base_url}/o/{link_publico.strip()}/pdf"

    html = _montar_html_email_orcamento(
        cliente_nome=cliente_nome,
        numero_orcamento=numero_orcamento,
        empresa_nome=empresa_nome,
        link_proposta=link_proposta,
        validade_texto=validade_texto,
        valor_total=valor_total,
        contato_telefone=contato_prestador,
        contato_email=contato_email,
        responsavel_nome=responsavel_nome,
        link_pdf=link_pdf_full,
        assinatura_email=assinatura_email,
        documentos=documentos,
    )

    if brevo_api_habilitado():
        logging.info(
            "Enviando orçamento por e-mail para %s via API Brevo", destinatario
        )
        attachments = []
        if anexar_pdf and pdf_bytes:
            attachments.append(
                {
                    "name": f"orcamento-{numero_orcamento.replace('/', '-')}.pdf",
                    "content": base64.b64encode(pdf_bytes).decode("ascii"),
                }
            )
        elif anexar_pdf:
            logging.warning(
                "Configuração de anexo ativa, mas PDF indisponível para o orçamento %s; enviando sem anexo.",
                numero_orcamento,
            )
        if anexos_extra:
            for a in anexos_extra:
                content = a.get("content") or b""
                if not content:
                    continue
                attachments.append(
                    {
                        "name": a.get("filename") or "documento.pdf",
                        "content": base64.b64encode(content).decode("ascii"),
                    }
                )
        ok, err = _enviar_via_brevo_api(
            destinatario,
            assunto,
            html,
            attachments=attachments if attachments else None,
        )
        if ok:
            logging.info(
                "Orçamento %s enviado por e-mail para %s",
                numero_orcamento,
                destinatario,
            )
            return True
        logging.exception(
            "Falha ao enviar orçamento por e-mail para %s: %s", destinatario, err
        )
        return False

    logging.info(
        "Enviando orçamento por e-mail para %s via SMTP %s:%s",
        destinatario,
        settings.SMTP_HOST,
        settings.SMTP_PORT,
    )
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
        msg["To"] = destinatario
        msg.attach(MIMEText(html, "html"))
        if anexar_pdf and pdf_bytes:
            part = MIMEBase("application", "pdf")
            part.set_payload(pdf_bytes)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=f"orcamento-{numero_orcamento.replace('/', '-')}.pdf",
            )
            msg.attach(part)
        elif anexar_pdf:
            logging.warning(
                "Configuração de anexo ativa, mas PDF indisponível para o orçamento %s; enviando sem anexo.",
                numero_orcamento,
            )
        if anexos_extra:
            for a in anexos_extra:
                content = a.get("content") or b""
                if not content:
                    continue
                mime = (a.get("mime") or "application/pdf").split("/", 1)
                maintype = mime[0] if len(mime) > 1 else "application"
                subtype = mime[1] if len(mime) > 1 else "octet-stream"
                part = MIMEBase(maintype, subtype)
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=a.get("filename") or "documento.pdf",
                )
                msg.attach(part)
        _enviar_via_smtp(msg)
        logging.info(
            "Orçamento %s enviado por e-mail para %s", numero_orcamento, destinatario
        )
        return True
    except Exception as e:
        logging.exception(
            "Falha ao enviar orçamento por e-mail para %s: %s", destinatario, e
        )
        return False


def _montar_html_email_confirmacao_aceite(
    cliente_nome: str,
    aceite_nome: str,
    numero_orcamento: str,
    empresa_nome: str,
    valor_total: float | None = None,
    contato_telefone: str | None = None,
    contato_email_empresa: str | None = None,
    assinatura_email: str | None = None,
) -> str:
    cliente_safe = escape((cliente_nome or aceite_nome or "Cliente").strip())
    aceite_safe = escape((aceite_nome or "").strip())
    numero_safe = escape((numero_orcamento or "-").strip())
    empresa_safe = escape((empresa_nome or "a empresa").strip())
    valor_safe = _formatar_brl(valor_total) if valor_total else None
    tel_safe = escape((contato_telefone or "").strip())
    email_emp_safe = escape((contato_email_empresa or "").strip())

    assinatura_safe = escape((assinatura_email or "").strip())
    bloco_assinatura = ""
    if assinatura_safe:
        bloco_assinatura = f"""
            <p style="margin:0 0 8px 0;font-size:14px;color:#333;line-height:1.7;white-space:pre-line;">{assinatura_safe}</p>
"""

    linha_valor = ""
    if valor_safe:
        linha_valor = f"""
          <tr>
            <td class="label">Valor</td>
            <td class="value total">{valor_safe}</td>
          </tr>
"""

    tel_digits = tel_safe.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
    linha_telefone = ""
    if tel_safe:
        linha_telefone = f"""
        <strong>WhatsApp:</strong>
        <a href="https://wa.me/{tel_digits}" class="whatsapp">{tel_safe}</a><br>
"""

    linha_email = ""
    if email_emp_safe:
        linha_email = f"""
        <strong>E-mail:</strong> {email_emp_safe}<br>
"""

    assinatura_aceite = ""
    if aceite_safe:
        assinatura_aceite = f"""
      <div style="margin:24px 0;padding:14px 16px;background-color:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;">
        <p style="margin:0;font-size:14px;line-height:1.6;color:#166534;">
          Aceite registrado por: <strong>{aceite_safe}</strong>
        </p>
      </div>
"""

    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Aceite confirmado - Orçamento {numero_safe}</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background-color: #f4f6f9;
      font-family: 'Segoe UI', Arial, sans-serif;
    }}
    .container {{
      max-width: 600px;
      margin: 20px auto;
      background-color: #ffffff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }}
    .header {{
      background-color: #0d6efd;
      color: white;
      padding: 25px 30px;
      text-align: center;
    }}
    .logo {{
      font-size: 28px;
      font-weight: bold;
      margin: 0;
    }}
    .content {{
      padding: 30px;
    }}
    .greeting {{
      font-size: 18px;
      color: #333;
      margin-bottom: 20px;
    }}
    .highlight-box {{
      background-color: #f8f9fa;
      border-left: 5px solid #0d6efd;
      padding: 20px;
      margin: 25px 0;
      border-radius: 8px;
    }}
    .summary-table {{
      width: 100%;
      border-collapse: collapse;
    }}
    .summary-table td {{
      padding: 12px 0;
      border-bottom: 1px solid #eee;
    }}
    .label {{
      color: #666;
      font-weight: 500;
    }}
    .value {{
      text-align: right;
      font-weight: 600;
      color: #222;
    }}
    .total {{
      font-size: 22px;
      color: #0d6efd;
      font-weight: bold;
    }}
    .footer {{
      background-color: #f8f9fa;
      padding: 25px 30px;
      font-size: 14px;
      color: #666;
      text-align: center;
      border-top: 1px solid #eee;
    }}
    .whatsapp {{
      color: #25D366;
      font-weight: 600;
    }}
    @media only screen and (max-width: 600px) {{
      .container {{
        margin: 10px;
        border-radius: 8px;
      }}
      .content {{
        padding: 20px;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header" style="background-color:#0d6efd;color:#ffffff;padding:25px 30px;text-align:center;">
      <h1 class="logo" style="color:#ffffff !important;font-size:28px;font-weight:bold;margin:0;">cotte.app</h1>
      <p style="margin:8px 0 0 0;opacity:0.9;color:#ffffff !important;">{empresa_safe} - Confirmação de aceite</p>
    </div>
    <div class="content">
      <p class="greeting">Olá, {cliente_safe},</p>
      <p>Seu aceite do orçamento <strong>{numero_safe}</strong> foi registrado com sucesso!</p>
      <p>Em breve <strong>{empresa_safe}</strong> entrará em contato para confirmar os próximos passos.</p>
      <div class="highlight-box">
        <h3 style="margin-top: 0; color: #0d6efd;">Resumo</h3>
        <table class="summary-table">
          <tr>
            <td class="label">Orçamento</td>
            <td class="value">{numero_safe}</td>
          </tr>
{linha_valor}
          <tr>
            <td class="label">Empresa</td>
            <td class="value">{empresa_safe}</td>
          </tr>
        </table>
      </div>
{assinatura_aceite}
{bloco_assinatura}
      <p>Qualquer dúvidas, entre em contato diretamente com {empresa_safe}:</p>
{linha_telefone}
{linha_email}
      <p style="margin-top: 30px;">
        Um abraço,<br>
        <strong>{empresa_safe}</strong>
      </p>
    </div>
    <div class="footer">
      <p style="margin: 0; font-size: 13px;">
        Este e-mail foi gerado automaticamente pela plataforma <strong>Cotte.app</strong>.<br>
        © 2026 Cotte.app
      </p>
    </div>
  </div>
</body>
</html>
"""

def enviar_otp_aceite(
    destinatario: str,
    codigo: str,
    numero_orcamento: str,
    empresa_nome: str,
) -> bool:
    """
    Envia e-mail com código OTP para confirmar o aceite do orçamento.
    """
    if not email_habilitado():
        return False

    assunto = f"Código de confirmação — Orçamento {numero_orcamento}"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#ffffff;color:#0f172a;padding:36px;border-radius:16px;border:1px solid #e1e7f0">
      <div style="text-align:left;margin-bottom:28px">
        <span style="font-size:14px;font-weight:700;color:#06b6d4;text-transform:uppercase;letter-spacing:0.05em">{empresa_nome}</span>
      </div>
      <h2 style="color:#0f172a;margin:0 0 16px;font-size:24px">Confirmar aceite</h2>
      <p style="color:#475569;margin:0 0 24px;font-size:16px;line-height:1.6">
        Você solicitou a confirmação para aceitar o orçamento <strong>{numero_orcamento}</strong>. 
        Use o código abaixo para validar sua identidade:
      </p>
      <div style="background:#f8fafc;border:1px solid #e1e7f0;border-radius:12px;padding:24px;text-align:center;margin-bottom:24px">
        <span style="font-family:monospace;font-size:32px;font-weight:700;letter-spacing:10px;color:#0f172a">{codigo}</span>
      </div>
      <p style="color:#64748b;font-size:14px;line-height:1.6;margin:0">
        Este código é válido por 10 minutos. Se você não solicitou este código, ignore este e-mail.
      </p>
      <hr style="border:0;border-top:1px solid #e1e7f0;margin:32px 0">
      <p style="color:#94a3b8;font-size:12px;text-align:center;margin:0">Enviado via plataforma COTTE</p>
    </div>
    """

    if brevo_api_habilitado():
        ok, _ = _enviar_via_brevo_api(destinatario, assunto, html)
        return ok

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
        msg["To"] = destinatario
        msg.attach(MIMEText(html, "html"))
        _enviar_via_smtp(msg)
        return True
    except Exception:
        logging.exception("Falha ao enviar e-mail de OTP para %s", destinatario)
        return False


def enviar_email_confirmacao_aceite(
    destinatario: str,
    cliente_nome: str,
    aceite_nome: str,
    numero_orcamento: str,
    empresa_nome: str,
    valor_total: float | None = None,
    contato_telefone: str | None = None,
    contato_email_empresa: str | None = None,
    assinatura_email: str | None = None,
) -> bool:
    """
    Envia e-mail de confirmação ao cliente após aceitar o orçamento pelo link público.
    Usa API Brevo se configurada, senão SMTP. Retorna True se enviou com sucesso.
    """
    if not email_habilitado():
        return False

    assunto = f"Aceite confirmado — {numero_orcamento} | {empresa_nome}"
    html = _montar_html_email_confirmacao_aceite(
        cliente_nome=cliente_nome,
        aceite_nome=aceite_nome,
        numero_orcamento=numero_orcamento,
        empresa_nome=empresa_nome,
        valor_total=valor_total,
        contato_telefone=contato_telefone,
        contato_email_empresa=contato_email_empresa,
        assinatura_email=assinatura_email,
    )

    if brevo_api_habilitado():
        ok, err = _enviar_via_brevo_api(destinatario, assunto, html)
        if ok:
            logging.info(
                "Confirmação de aceite enviada para %s via Brevo", destinatario
            )
        else:
            logging.warning(
                "Falha ao enviar confirmação de aceite para %s: %s", destinatario, err
            )
        return ok

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
        msg["To"] = destinatario
        msg.attach(MIMEText(html, "html"))
        _enviar_via_smtp(msg)
        logging.info("Confirmação de aceite enviada para %s via SMTP", destinatario)
        return True
    except Exception as e:
        logging.exception(
            "Falha ao enviar confirmação de aceite para %s: %s", destinatario, e
        )
        return False


def enviar_email_teste(destinatario: str) -> tuple[bool, str]:
    """
    Envia um e-mail de teste. Usa API Brevo se configurada, senão SMTP.
    Retorna (True, "") em sucesso ou (False, "mensagem de erro").
    """
    if not email_habilitado():
        return (
            False,
            "E-mail não configurado (BREVO_API_KEY ou SMTP_HOST/SMTP_USER/SMTP_PASS)",
        )

    assunto = f"[{settings.APP_NAME}] Teste de e-mail"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#0f1117;color:#e5e7eb;padding:32px;border-radius:16px">
      <div style="text-align:center;margin-bottom:24px">
        <span style="background:#00e5a0;color:#0f1117;font-weight:700;font-size:18px;padding:6px 16px;border-radius:8px">{settings.APP_NAME}</span>
      </div>
      <h2 style="color:#00e5a0;margin:0 0 8px">E-mail de teste</h2>
      <p style="color:#9ca3af;margin:0 0 16px">Se você recebeu esta mensagem, o envio (Brevo) está funcionando.</p>
      <p style="color:#4b5563;font-size:12px;text-align:center;margin-top:24px">{settings.APP_URL}</p>
    </div>
    """
    if brevo_api_habilitado():
        ok, err = _enviar_via_brevo_api(destinatario, assunto, html)
        if ok:
            logging.info("E-mail de teste enviado para %s via API Brevo", destinatario)
            return True, ""
        return False, err
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
        msg["To"] = destinatario
        msg.attach(MIMEText(html, "html"))
        _enviar_via_smtp(msg)
        logging.info("E-mail de teste enviado para %s", destinatario)
        return True, ""
    except Exception as e:
        logging.exception(
            "Falha ao enviar e-mail de teste para %s: %s", destinatario, e
        )
        return False


def enviar_email_boas_vindas(destinatario: str, nome: str, senha: str) -> bool:
    """
    Envia e-mail HTML de boas-vindas com credenciais (registro público).
    Usa API Brevo se configurada, senão SMTP. Retorna True se enviou com sucesso.
    """
    if not email_habilitado():
        return False
    primeiro = (nome or "").strip().split()[0] if (nome or "").strip() else "usuário"
    link = f"{settings.APP_URL.rstrip('/')}/app/index.html"
    assunto = "Bem-vindo ao COTTE — suas credenciais de acesso"

    primeiro_safe = escape(primeiro)
    link_safe = escape(link, quote=True)
    app_url_safe = escape(settings.APP_URL.rstrip("/"), quote=True)
    senha_safe = escape(senha)

    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Bem-vindo ao COTTE</title>
    </head>
    <body style="margin:0;padding:0;background-color:#f4f7fb;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#f4f7fb;margin:0;padding:24px 12px;">
        <tr>
          <td align="center">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:640px;">
              <tr>
                <td style="padding:0 0 14px 0;text-align:center;">
                  <span style="display:inline-block;font-size:14px;line-height:1.2;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#06b6d4;">
                    COTTE
                  </span>
                </td>
              </tr>
            </table>

            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:640px;background-color:#ffffff;border:1px solid #e1e7f0;border-radius:16px;">
              <tr>
                <td style="padding:32px 28px 24px 28px;">
                  <h1 style="margin:0 0 14px 0;font-size:28px;line-height:1.2;color:#0f172a;font-weight:700;">
                    Bem-vindo, {primeiro_safe}! 🎉
                  </h1>
                  <p style="margin:0 0 14px 0;font-size:16px;line-height:1.7;color:#334155;">
                    Sua conta foi criada com sucesso.
                  </p>
                  <p style="margin:0 0 14px 0;font-size:15px;line-height:1.7;color:#475569;">
                    Aqui estão seus dados de acesso:
                  </p>
                  
                  <div style="margin:0 0 24px 0;padding:18px 20px;background-color:#f8fafc;border:1px solid #e1e7f0;border-radius:12px;">
                    <p style="margin:0 0 10px 0;font-size:14px;line-height:1.6;color:#334155;">
                      <strong style="color:#0f172a;">E-mail:</strong> {escape(destinatario)}
                    </p>
                    <p style="margin:0;font-size:14px;line-height:1.6;color:#334155;">
                      <strong style="color:#0f172a;">Senha:</strong>
                      <code style="background:#0f172a;color:#06b6d4;padding:4px 10px;border-radius:5px;font-size:14px;letter-spacing:1px;">{senha_safe}</code>
                    </p>
                  </div>

                  <p style="margin:0 0 24px 0;font-size:15px;line-height:1.7;color:#475569;">
                    Seu trial gratuito é válido por <strong style="color:#0f172a;">14 dias</strong>.
                  </p>

                  <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin:0 auto 22px auto;">
                    <tr>
                      <td bgcolor="#06b6d4" style="border-radius:10px;text-align:center;">
                        <a href="{link_safe}" target="_blank" style="display:inline-block;padding:14px 24px;font-size:15px;line-height:1.2;font-weight:700;color:#ffffff;text-decoration:none;border-radius:10px;">
                          Acessar o COTTE →
                        </a>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="padding:14px 28px 20px 28px;border-top:1px solid #e1e7f0;">
                  <p style="margin:0 0 8px 0;font-size:12px;line-height:1.6;color:#94a3b8;">
                    Equipe COTTE
                  </p>
                  <p style="margin:0;font-size:12px;line-height:1.6;color:#94a3b8;">
                    <a href="{app_url_safe}" target="_blank" style="color:#06b6d4;text-decoration:none;">{app_url_safe}</a>
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """
    if brevo_api_habilitado():
        ok, _ = _enviar_via_brevo_api(destinatario, assunto, html)
        if ok:
            logging.info(
                "E-mail de boas-vindas enviado para %s via API Brevo", destinatario
            )
        return ok
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
        msg["To"] = destinatario
        msg.attach(MIMEText(html, "html"))
        _enviar_via_smtp(msg)
        logging.info("E-mail de boas-vindas enviado para %s", destinatario)
        return True
    except Exception as e:
        logging.exception(
            "Falha ao enviar e-mail de boas-vindas para %s: %s", destinatario, e
        )
        return False


def _montar_html_email_reset_senha(
    primeiro_nome: str,
    link_reset: str,
    app_url: str,
    expiracao_minutos: int = 30,
) -> str:
    """Monta HTML transacional para e-mail de redefinição de senha."""
    primeiro_safe = escape((primeiro_nome or "usuário").strip())
    link_reset_safe = escape((link_reset or "").strip(), quote=True)
    app_url_safe = escape((app_url or "").strip(), quote=True)
    expiracao_safe = escape(str(expiracao_minutos))

    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Redefinição de senha</title>
    </head>
    <body style="margin:0;padding:0;background-color:#f4f7fb;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#f4f7fb;margin:0;padding:24px 12px;">
        <tr>
          <td align="center">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:640px;">
              <tr>
                <td style="padding:0 0 14px 0;text-align:center;">
                  <span style="display:inline-block;font-size:14px;line-height:1.2;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#06b6d4;">
                    COTTE
                  </span>
                </td>
              </tr>
            </table>

            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:640px;background-color:#ffffff;border:1px solid #e1e7f0;border-radius:16px;">
              <tr>
                <td style="padding:32px 28px 24px 28px;">
                  <h1 style="margin:0 0 14px 0;font-size:28px;line-height:1.2;color:#0f172a;font-weight:700;">
                    Redefinição de senha
                  </h1>
                  <p style="margin:0 0 14px 0;font-size:16px;line-height:1.7;color:#334155;">
                    Olá, <strong>{primeiro_safe}</strong>.
                  </p>
                  <p style="margin:0 0 14px 0;font-size:15px;line-height:1.7;color:#475569;">
                    Recebemos uma solicitação para redefinir a senha da sua conta no COTTE.
                  </p>
                  <p style="margin:0 0 24px 0;font-size:15px;line-height:1.7;color:#475569;">
                    Para continuar, clique no botão abaixo. Este link é válido por <strong style="color:#0f172a;">{expiracao_safe} minutos</strong>.
                  </p>

                  <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin:0 auto 22px auto;">
                    <tr>
                      <td bgcolor="#06b6d4" style="border-radius:10px;text-align:center;">
                        <a href="{link_reset_safe}" target="_blank" style="display:inline-block;padding:14px 24px;font-size:15px;line-height:1.2;font-weight:700;color:#ffffff;text-decoration:none;border-radius:10px;">
                          Redefinir senha
                        </a>
                      </td>
                    </tr>
                  </table>

                  <div style="margin:0 0 12px 0;padding:14px 16px;background-color:#f8fafc;border:1px solid #e1e7f0;border-radius:12px;">
                    <p style="margin:0;font-size:13px;line-height:1.6;color:#64748b;">
                      Se você não solicitou esta redefinição, ignore este e-mail. Sua senha atual continuará válida e sua conta permanecerá protegida.
                    </p>
                  </div>
                </td>
              </tr>
              <tr>
                <td style="padding:14px 28px 20px 28px;border-top:1px solid #e1e7f0;">
                  <p style="margin:0 0 8px 0;font-size:12px;line-height:1.6;color:#94a3b8;">
                    Equipe COTTE
                  </p>
                  <p style="margin:0;font-size:12px;line-height:1.6;color:#94a3b8;">
                    <a href="{app_url_safe}" target="_blank" style="color:#06b6d4;text-decoration:none;">{app_url_safe}</a>
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """


def _montar_texto_email_reset_senha(
    primeiro_nome: str,
    link_reset: str,
    app_url: str,
    expiracao_minutos: int = 30,
) -> str:
    """Monta fallback em texto puro para clientes sem renderização HTML."""
    primeiro_safe = (primeiro_nome or "usuário").strip()
    link_reset_safe = (link_reset or "").strip()
    app_url_safe = (app_url or "").strip()

    return (
        f"Olá, {primeiro_safe}.\n\n"
        "Recebemos uma solicitação para redefinir a senha da sua conta no COTTE.\n"
        f"Para continuar, acesse o link abaixo (válido por {expiracao_minutos} minutos):\n\n"
        f"{link_reset_safe}\n\n"
        "Se você não solicitou esta redefinição, ignore este e-mail. "
        "Sua senha atual continuará válida.\n\n"
        "Equipe COTTE\n"
        f"{app_url_safe}\n"
    )


def enviar_email_reset_senha(destinatario: str, nome: str, link_reset: str) -> bool:
    """
    Envia e-mail com link temporário para redefinição de senha.
    Usa API Brevo se configurada, senão SMTP. Retorna True se enviou com sucesso.
    """
    if not email_habilitado():
        return False

    primeiro = (nome or "").strip().split()[0] if (nome or "").strip() else "usuário"
    app_url = settings.APP_URL.rstrip("/")
    assunto = "COTTE — redefinição de senha"
    # Variáveis dinâmicas principais do template: nome do usuário e link único de reset.
    html = _montar_html_email_reset_senha(
        primeiro_nome=primeiro,
        link_reset=link_reset,
        app_url=app_url,
        expiracao_minutos=30,
    )
    # Fallback em texto para clientes que não renderizam HTML.
    texto = _montar_texto_email_reset_senha(
        primeiro_nome=primeiro,
        link_reset=link_reset,
        app_url=app_url,
        expiracao_minutos=30,
    )

    if brevo_api_habilitado():
        ok, _ = _enviar_via_brevo_api(destinatario, assunto, html, texto=texto)
        if ok:
            logging.info(
                "E-mail de redefinição de senha enviado para %s via API Brevo",
                destinatario,
            )
        return ok

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
        msg["To"] = destinatario
        msg.attach(MIMEText(texto, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))
        _enviar_via_smtp(msg)
        logging.info("E-mail de redefinição de senha enviado para %s", destinatario)
        return True
    except Exception as e:
        logging.exception(
            "Falha ao enviar e-mail de redefinição de senha para %s: %s",
            destinatario,
            e,
        )
        return False


def _texto_plano_para_html_email(mensagem: str) -> str:
    """HTML mínimo para htmlContent da Brevo (texto plano com quebras de linha)."""
    esc = escape(mensagem or "")
    corpo = esc.replace("\n", "<br/>\n")
    return (
        '<div style="font-family:system-ui,Segoe UI,sans-serif;font-size:15px;'
        'line-height:1.5;color:#1e293b;">' + corpo + "</div>"
    )


def send_email_simples(destinatario: str, assunto: str, mensagem: str) -> bool:
    """
    Envia um e-mail simples (texto plano).
    Usa API Brevo se configurada, senão SMTP.
    Retorna True se enviou com sucesso.
    """
    if not email_habilitado():
        logging.error("Serviço de e-mail não configurado")
        return False

    if brevo_api_habilitado():
        html_body = _texto_plano_para_html_email(mensagem)
        return _enviar_via_brevo_api(
            destinatario, assunto, html_body, texto=mensagem
        )[0]

    try:
        msg = MIMEText(mensagem, "plain", "utf-8")
        msg["Subject"] = assunto
        msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
        msg["To"] = destinatario

        _enviar_via_smtp(msg)

        logging.info("E-mail simples enviado para %s", destinatario)
        return True
    except Exception as e:
        logging.exception("Falha ao enviar e-mail simples para %s: %s", destinatario, e)
        return False
