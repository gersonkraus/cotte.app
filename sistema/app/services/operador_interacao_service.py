"""
Camada de interações interativas para o canal WhatsApp do operador.
Abstrai Poll, Lista e Texto estruturado — sem depender de sendButtons
(instável nas versões recentes da Evolution API 2.2.3+).
"""
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


async def enviar_poll_confirmacao(
    telefone: str,
    pergunta: str,
    opcoes: list[str],
    instancia: str | None = None,
) -> bool:
    """
    Envia enquete nativa do WhatsApp para confirmação.
    Mais estável que sendButtons na Evolution API atual.
    opcoes: ex: ["Confirmar", "Cancelar"]
    """
    inst = instancia or settings.EVOLUTION_INSTANCE
    url = f"{settings.EVOLUTION_API_URL.rstrip('/')}/message/sendPoll/{inst}"
    payload = {
        "number": _fmt_phone(telefone),
        "name": pergunta,
        "values": opcoes,
        "selectableCount": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                url,
                json=payload,
                headers={
                    "apikey": settings.EVOLUTION_API_KEY,
                    "Content-Type": "application/json",
                },
            )
            return r.status_code in (200, 201)
    except Exception as e:
        logger.warning("[Poll] Falha ao enviar poll: %s", e)
        return False


async def enviar_lista_selecao(
    telefone: str,
    titulo: str,
    descricao: str,
    secoes: list[dict],  # [{"titulo": str, "itens": [{"id": str, "titulo": str, "desc": str}]}]
    botao_texto: str = "Ver opções",
    instancia: str | None = None,
) -> bool:
    """Envia menu de lista (sendList) — para selecionar clientes, serviços etc."""
    inst = instancia or settings.EVOLUTION_INSTANCE
    url = f"{settings.EVOLUTION_API_URL.rstrip('/')}/message/sendList/{inst}"
    sections = [
        {
            "title": s["titulo"],
            "rows": [
                {
                    "title": i["titulo"],
                    "description": i.get("desc", ""),
                    "rowId": i["id"],
                }
                for i in s["itens"]
            ],
        }
        for s in secoes
    ]
    payload = {
        "number": _fmt_phone(telefone),
        "title": titulo,
        "description": descricao,
        "buttonText": botao_texto,
        "sections": sections,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                url,
                json=payload,
                headers={
                    "apikey": settings.EVOLUTION_API_KEY,
                    "Content-Type": "application/json",
                },
            )
            return r.status_code in (200, 201)
    except Exception as e:
        logger.warning("[Lista] Falha ao enviar lista: %s", e)
        return False


def texto_opcoes_numeradas(titulo: str, descricao: str, opcoes: list[str]) -> str:
    """Fallback universal: texto formatado com opções numeradas."""
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    linhas = [f"*{titulo}*", "", descricao, ""]
    for i, op in enumerate(opcoes):
        em = emojis[i] if i < len(emojis) else f"{i + 1}."
        linhas.append(f"{em} *{op}*")
    return "\n".join(linhas)


def sanitizar_para_whatsapp(texto: str) -> str:
    """Converte markdown rico para formato compatível com WhatsApp."""
    import re

    # Remove headers markdown (## Título → Título)
    texto = re.sub(r"^#{1,6}\s+", "", texto, flags=re.MULTILINE)
    # Converte **negrito** → *negrito*
    texto = re.sub(r"\*\*(.+?)\*\*", r"*\1*", texto)
    # Remove tabelas (linhas com |)
    texto = re.sub(r"\|.*\|", "", texto)
    # Remove linhas de separador de tabela (--- | ---)
    texto = re.sub(r"^[-| ]+$", "", texto, flags=re.MULTILINE)
    # Limpa linhas em branco duplicadas
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    # Trunca a 900 chars para evitar quebra de mensagem
    if len(texto) > 900:
        texto = texto[:900] + "\n_(mensagem truncada — veja detalhes no app)_"
    return texto.strip()


def _fmt_phone(telefone: str) -> str:
    try:
        from app.utils.phone import normalize_phone_number
        normalized = normalize_phone_number(telefone)
        return normalized or telefone
    except Exception:
        return telefone
