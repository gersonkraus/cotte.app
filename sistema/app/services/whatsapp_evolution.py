"""
Provider Evolution API para WhatsApp.

Documentação: https://doc.evolution-api.com
Deploy via Docker: a Evolution API roda localmente ou em servidor próprio.

Variáveis necessárias no .env:
    EVOLUTION_API_URL      = http://localhost:8080   (URL base do servidor)
    EVOLUTION_API_KEY      = sua-api-key-global
    EVOLUTION_INSTANCE     = nome-da-instancia       (ex: "cotte-prod")

Para uso multi-tenant, instancie passando o nome da instância da empresa:
    EvolutionProvider(instance="empresa-42")
"""
import base64
import httpx

from app.core.config import settings
from app.services.whatsapp_base import WhatsAppProvider, _retry_async


class EvolutionProvider(WhatsAppProvider):

    def __init__(self, instance: str | None = None):
        base = settings.EVOLUTION_API_URL.rstrip("/")
        inst = instance or settings.EVOLUTION_INSTANCE
        self._base_instance = f"{base}"
        self._base_msg       = f"{base}/message"
        self._instance       = inst
        self._headers_dict   = {
            "Content-Type": "application/json",
            "apikey": settings.EVOLUTION_API_KEY,
        }

    # ── Gestão de instâncias (multi-tenant) ───────────────────────────────

    @staticmethod
    async def criar_instancia(instance_name: str, webhook_url: str) -> dict:
        """
        Cria uma nova instância na Evolution API e configura o webhook.
        Retorna o dict com dados da instância criada.
        """
        base = settings.EVOLUTION_API_URL.rstrip("/")
        headers = {
            "Content-Type": "application/json",
            "apikey": settings.EVOLUTION_API_KEY,
        }
        payload = {
            "instanceName": instance_name,
            "integration": "WHATSAPP-BAILEYS",
            "webhook": {
                "enabled": True,
                "url": webhook_url,
                "byEvents": True,
                "base64": False,
                "events": [
                    "MESSAGES_UPSERT",
                    "CONNECTION_UPDATE",
                ],
            },
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{base}/instance/create",
                headers=headers,
                json=payload,
            )
            if resp.status_code in (200, 201):
                return {"ok": True, "data": resp.json()}
            return {"ok": False, "error": resp.text, "status": resp.status_code}

    @staticmethod
    async def deletar_instancia(instance_name: str) -> bool:
        """Deleta a instância da Evolution API (desconecta e remove)."""
        base = settings.EVOLUTION_API_URL.rstrip("/")
        headers = {
            "Content-Type": "application/json",
            "apikey": settings.EVOLUTION_API_KEY,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(
                f"{base}/instance/delete/{instance_name}",
                headers=headers,
            )
            return resp.status_code in (200, 204)

    def _link_orcamento(self, link_publico: str) -> str:
        base = settings.APP_URL.rstrip("/")
        return f"{base}/app/orcamento-publico.html?token={link_publico}"

    # ── Conexão ────────────────────────────────────────────────────────────

    async def get_status(self) -> dict:
        """GET /instance/connectionState/{instance}"""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self._base_instance}/instance/connectionState/{self._instance}",
                headers=self._headers_dict,
            )
            if resp.status_code == 200:
                data = resp.json()
                # Evolution retorna { "instance": { "state": "open" } }
                state = data.get("instance", {}).get("state", "")
                return {"connected": state == "open", "state": state, "raw": data}
            return {"connected": False, "error": resp.text}

    async def get_qrcode(self) -> dict:
        """GET /instance/connect/{instance}  — retorna QR Code para parear."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self._base_instance}/instance/connect/{self._instance}",
                headers=self._headers_dict,
            )
            if resp.status_code == 200:
                data = resp.json()
                # Evolution pode retornar:
                # - { "code": "...", "base64": "data:image/png;base64,..." }
                # - { "value": "2@..." } (string usada para gerar o QR)
                # - { "qrcode": "data:image/png;base64,..." }
                qr_any = (
                    data.get("base64")
                    or data.get("qrcode")
                    or data.get("image")
                    or data.get("value")
                    or ""
                )
                # Remove prefixo data:image/png;base64, se presente, para compatibilidade
                if isinstance(qr_any, str) and "," in qr_any:
                    qr_any = qr_any.split(",", 1)[1]
                return {"qrcode": qr_any, "raw": data}
            return {"error": resp.text}

    async def desconectar(self) -> bool:
        """DELETE /instance/logout/{instance}"""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(
                f"{self._base_instance}/instance/logout/{self._instance}",
                headers=self._headers_dict,
            )
            return resp.status_code in (200, 204)

    # ── Envio de mensagens ─────────────────────────────────────────────────

    async def enviar_mensagem_texto(self, telefone: str, mensagem: str) -> bool:
        """POST /message/sendText/{instance}"""

        async def _do_send() -> bool:
            phone = self.normalizar_telefone(telefone)
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self._base_msg}/sendText/{self._instance}",
                    headers=self._headers_dict,
                    json={
                        "number": phone,
                        "text": mensagem,
                    },
                )
                return resp.status_code in (200, 201)

        return await _retry_async(_do_send)

    async def enviar_poll(
        self, telefone: str, pergunta: str, opcoes: list[str]
    ) -> bool:
        """Envia enquete nativa do WhatsApp (sendPoll) para confirmação."""
        from app.services.operador_interacao_service import enviar_poll_confirmacao
        return await enviar_poll_confirmacao(
            telefone, pergunta, opcoes, instancia=self._instance
        )

    async def enviar_lista(
        self,
        telefone: str,
        titulo: str,
        descricao: str,
        secoes: list[dict],
        botao_texto: str = "Ver opções",
    ) -> bool:
        """Envia menu de lista interativa (sendList)."""
        from app.services.operador_interacao_service import enviar_lista_selecao
        return await enviar_lista_selecao(
            telefone, titulo, descricao, secoes,
            botao_texto=botao_texto, instancia=self._instance
        )

    async def enviar_pdf(
        self, telefone: str, pdf_bytes: bytes, numero: str, caption: str = ""
    ) -> bool:
        """POST /message/sendMedia/{instance}  — envia PDF como documento."""

        async def _do_send() -> bool:
            phone   = self.normalizar_telefone(telefone)
            pdf_b64 = base64.b64encode(pdf_bytes).decode()
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self._base_msg}/sendMedia/{self._instance}",
                    headers=self._headers_dict,
                    json={
                        "number":   phone,
                        "mediatype": "document",
                        "mimetype": "application/pdf",
                        "caption":  caption or f"Orçamento {numero}",
                        "media":    pdf_b64,
                        "fileName": f"Orcamento-{numero.replace('/', '-')}.pdf",
                    },
                )
                return resp.status_code in (200, 201)

        return await _retry_async(_do_send)

    async def enviar_orcamento_completo(
        self, telefone: str, orcamento: dict, pdf_bytes: bytes = b""
    ) -> bool:
        """
        Envia mensagem de texto com o link do orçamento.
        A Evolution API não possui endpoint nativo de 'send-link card',
        então enviamos texto formatado + link + PDF em sequência.
        """
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
        if link:
            linhas.append(f"\nAcesse os detalhes e aprove com um clique:\n👉 {link}")
        else:
            linhas.append("\n\nPara aprovar, responda *ACEITO*")
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
            texto += "\n\nDocumentos complementares:\n" + "\n".join(linhas_docs)

        # SE TEM PDF: Envia como uma única mensagem (PDF + Legenda)
        sucesso = False
        if pdf_bytes:
            sucesso = await self.enviar_pdf(telefone, pdf_bytes, numero, texto)
        else:
            sucesso = await self.enviar_mensagem_texto(telefone, texto)
            
        # Tenta enviar um Poll interativo para o cliente logo após o orçamento
        if sucesso:
            await self.enviar_poll(
                telefone, 
                "Como você deseja prosseguir?", 
                ["✔️ Aprovar Orçamento", "💬 Tenho Dúvidas", "✏️ Solicitar Alteração"]
            )
            
        return sucesso

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
