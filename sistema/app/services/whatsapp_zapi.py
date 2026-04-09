"""
Provider Z-API para WhatsApp.

Documentação: https://developer.z-api.io
"""
import base64
import httpx

from app.core.config import settings
from app.services.whatsapp_base import WhatsAppProvider, _retry_async


class ZAPIProvider(WhatsAppProvider):

    def __init__(self):
        self._base = (
            f"{settings.ZAPI_BASE_URL}"
            f"/{settings.ZAPI_INSTANCE_ID}"
            f"/token/{settings.ZAPI_TOKEN}"
        )

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if settings.ZAPI_CLIENT_TOKEN:
            h["Client-Token"] = settings.ZAPI_CLIENT_TOKEN
        return h

    def _link_orcamento(self, link_publico: str) -> str:
        base = settings.APP_URL.rstrip("/")
        return f"{base}/app/orcamento-publico.html?token={link_publico}"

    # ── Conexão ────────────────────────────────────────────────────────────

    async def get_status(self) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self._base}/status", headers=self._headers())
            if resp.status_code == 200:
                return resp.json()
            return {"connected": False, "error": resp.text}

    async def get_qrcode(self) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{self._base}/qr-code", headers=self._headers())
            if resp.status_code == 200:
                return resp.json()
            return {"error": resp.text}

    async def desconectar(self) -> bool:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(
                f"{self._base}/disconnect", headers=self._headers()
            )
            return resp.status_code == 200

    # ── Envio de mensagens ─────────────────────────────────────────────────

    async def enviar_mensagem_texto(self, telefone: str, mensagem: str) -> bool:
        async def _do_send() -> bool:
            phone = self.normalizar_telefone(telefone)
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self._base}/send-text",
                    headers=self._headers(),
                    json={"phone": phone, "message": mensagem},
                )
                return resp.status_code == 200

        return await _retry_async(_do_send)

    async def enviar_pdf(
        self, telefone: str, pdf_bytes: bytes, numero: str, caption: str = ""
    ) -> bool:
        async def _do_send() -> bool:
            phone = self.normalizar_telefone(telefone)
            pdf_b64 = base64.b64encode(pdf_bytes).decode()
            filename = f"Orcamento-{numero.replace('/', '-')}"
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    f"{self._base}/send-document/pdf",
                    headers=self._headers(),
                    json={
                        "phone": phone,
                        "document": f"data:application/pdf;base64,{pdf_b64}",
                        "fileName": filename,
                        "caption": caption or f"Orcamento {numero}",
                    },
                )
                return resp.status_code == 200

        return await _retry_async(_do_send)

    async def enviar_orcamento_completo(
        self, telefone: str, orcamento: dict, pdf_bytes: bytes = b""
    ) -> bool:
        numero        = orcamento["numero"]
        cliente       = orcamento.get("cliente_nome", "")
        total         = orcamento["total"]
        validade      = orcamento.get("validade_dias", 7)
        empresa_nome  = orcamento.get("empresa_nome", "")
        vendedor_nome = orcamento.get("vendedor_nome", "")
        link_publico  = orcamento.get("link_publico", "")

        total_fmt = self.formatar_brl(total)
        link = self._link_orcamento(link_publico) if link_publico else ""

        linhas = [
            f"📋 *Orçamento #{numero} — {cliente}*",
            f"Olá, {cliente}! Seu orçamento está pronto. 🎉",
            f"💰 *Valor:* {total_fmt}",
            f"📅 *Válido até:* {self._calcular_data_validade(validade)}",
        ]
        if vendedor_nome:
            linhas.append(f"👤 *Responsável:* {vendedor_nome}")
        linhas.append("\nQualquer dúvida, é só chamar!")
        texto = "\n".join(linhas)
        docs = orcamento.get("documentos_whatsapp") or []
        if isinstance(docs, list) and docs:
            linhas_docs = []
            for d in docs:
                nome = (d or {}).get("nome") or "Documento"
                url = (d or {}).get("url") or ""
                if url:
                    linhas_docs.append(f"- {nome}: {url}")
                else:
                    linhas_docs.append(f"- {nome}")
            texto += "\n\n📎 Documentos complementares:\n" + "\n".join(linhas_docs)

        # SE TEM PDF: Envia como uma única mensagem (PDF + Legenda)
        if pdf_bytes:
            # Adiciona o link ao final do texto da legenda para garantir que o cliente possa clicar
            if link:
                texto += f"\n\n👉 Acesse os detalhes e aprove com um clique:\n{link}"
            
            return await self.enviar_pdf(
                telefone, pdf_bytes, numero, texto
            )

        # SE NÃO TEM PDF: Envia como link-card (send-link) ou texto simples
        if link:
            phone = self.normalizar_telefone(telefone)
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self._base}/send-link",
                    headers=self._headers(),
                    json={
                        "phone": phone,
                        "message": texto,
                        "linkUrl": link,
                        "title": f"Orçamento {numero} — {empresa_nome or 'COTTE'}",
                        "linkDescription": (
                            f"Toque para ver detalhes e aceitar online. Total: {total_fmt}"
                        ),
                    },
                )
            if resp.status_code == 200:
                return True
            
            # Fallback se send-link falhar
            return await self.enviar_mensagem_texto(
                telefone, texto + f"\n\n👉 Acesse os detalhes e aprove com um clique:\n{link}"
            )
        
        return await self.enviar_mensagem_texto(
            telefone, texto + "\n\nPara aprovar, responda *ACEITO*"
        )

    # ── Notificações ao operador ───────────────────────────────────────────

    async def notificar_operador_visualizacao(
        self, telefone_operador: str, numero: str, cliente_nome: str
    ) -> bool:
        msg = (
            f"📬 *{cliente_nome}* acabou de abrir o orçamento *{numero}*!\n"
            f"O cliente está visualizando a proposta agora. 👀"
        )
        return await self.enviar_mensagem_texto(telefone_operador, msg)

    async def notificar_operador_aceite(
        self,
        telefone_operador: str,
        numero: str,
        cliente_nome: str,
        aceite_nome: str,
        total: float,
        mensagem: str | None = None,
    ) -> bool:
        total_fmt = self.formatar_brl(total)
        msg = (
            f"✅ *Orçamento {numero} ACEITO!*\n\n"
            f"👤 Cliente: {cliente_nome}\n"
            f"✍️ Aceite registrado por: {aceite_nome}\n"
            f"💰 Valor: {total_fmt}"
        )
        if mensagem:
            msg += f"\n\n💬 Mensagem do cliente:\n_{mensagem}_"
        msg += "\n\nEntre em contato para confirmar a execução do serviço."
        return await self.enviar_mensagem_texto(telefone_operador, msg)

    async def notificar_operador_recusa(
        self,
        telefone_operador: str,
        numero: str,
        cliente_nome: str,
        motivo: str | None = None,
    ) -> bool:
        msg = (
            f"❌ *Orçamento {numero} RECUSADO*\n\n"
            f"👤 Cliente: {cliente_nome}\n"
        )
        if motivo:
            msg += f"💬 Motivo: {motivo}\n"
        msg += "\nBoa oportunidade para entrar em contato e entender o que pode ser ajustado."
        return await self.enviar_mensagem_texto(telefone_operador, msg)

    async def enviar_lembrete_cliente(
        self,
        telefone_cliente: str,
        cliente_nome: str,
        numero_orc: str,
        link_publico: str,
        empresa_nome: str,
        base_url: str = "",
        lembrete_texto: str | None = None,
    ) -> bool:
        url = base_url.rstrip("/")
        link = f"{url}/app/orcamento-publico.html?token={link_publico}" if url else link_publico
        if lembrete_texto:
            msg = lembrete_texto.replace("{cliente_nome}", cliente_nome)\
                                .replace("{numero_orc}", numero_orc)\
                                .replace("{empresa_nome}", empresa_nome)\
                                .replace("{link}", link)
        else:
            msg = (
                f"Olá, *{cliente_nome}*! 👋\n\n"
                f"Passando para lembrar que seu orçamento *{numero_orc}* da *{empresa_nome}* "
                f"ainda está disponível para aprovação.\n\n"
                f"Clique abaixo para visualizar a proposta:\n{link}\n\n"
                f"Qualquer dúvida, estamos à disposição! 😊"
            )
        return await self.enviar_mensagem_texto(telefone_cliente, msg)
