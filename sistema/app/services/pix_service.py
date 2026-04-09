"""Serviço para geração de QR codes PIX no padrão EMV BRCode (Bacen).

O payload segue a especificação PIX do Banco Central (BRCode / EMV MPM),
garantindo compatibilidade com todos os apps bancários brasileiros.
"""

import qrcode
import io
import base64
import unicodedata


# ── Helpers ────────────────────────────────────────────────────────────────

def _emv_field(id: str, value: str) -> str:
    """Formata um campo EMV TLV: ID (2 chars) + Length (2 chars) + Value."""
    return f"{id}{len(value):02d}{value}"


def _sanitize_name(name: str) -> str:
    """Remove acentos e caracteres não-ASCII; retorna uppercase sem pontuação."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    clean = "".join(c for c in ascii_str if c.isalnum() or c == " ")
    return clean.upper().strip()


def _crc16(payload: str) -> int:
    """CRC16/CCITT-FALSE: poly=0x1021, init=0xFFFF — exigido pelo padrão EMV PIX."""
    crc = 0xFFFF
    for char in payload:
        crc ^= ord(char) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


# ── Funções públicas ────────────────────────────────────────────────────────

def gerar_payload_pix(
    chave: str,
    nome_recebedor: str,
    cidade: str = "BRASIL",
    valor: float = None,
    descricao: str = "",
) -> str:
    """Gera o payload EMV BRCode para PIX Estático (padrão Bacen).

    O texto retornado é o "Pix Copia e Cola" e também o que deve ser
    codificado dentro do QR Code para que apps bancários reconheçam.

    Args:
        chave: Chave PIX (CPF, CNPJ, e-mail, telefone ou aleatória).
        nome_recebedor: Nome do titular da conta (max 25 chars após sanitização).
        cidade: Cidade do recebedor (max 15 chars após sanitização). Default "BRASIL".
        valor: Valor da transação em R$. Se None ou 0, gera QR sem valor fixo.
        descricao: Texto livre exibido no app do pagador (opcional, max 72 chars).

    Returns:
        String do payload EMV completo (inclui CRC16 no final).
    """
    # Field 26 — Merchant Account Information
    gui_field   = _emv_field("00", "BR.GOV.BCB.PIX")
    chave_field = _emv_field("01", chave.strip())
    mai_inner   = gui_field + chave_field
    if descricao:
        mai_inner += _emv_field("02", descricao[:72])
    mai = _emv_field("26", mai_inner)

    # Montar payload sem CRC
    payload  = _emv_field("00", "01")      # Payload Format Indicator
    payload += _emv_field("01", "11")      # Point of Initiation: 11 = estático, reutilizável
    payload += mai                          # Merchant Account Information
    payload += _emv_field("52", "0000")    # Merchant Category Code
    payload += _emv_field("53", "986")     # Transaction Currency (BRL)

    if valor and valor > 0:
        payload += _emv_field("54", f"{valor:.2f}")

    payload += _emv_field("58", "BR")      # Country Code

    nome_clean   = _sanitize_name(nome_recebedor)[:25] or "NAO INFORMADO"
    cidade_clean = _sanitize_name(cidade)[:15] or "BRASIL"
    payload += _emv_field("59", nome_clean)
    payload += _emv_field("60", cidade_clean)

    # Field 62 — Additional Data (txid: número do orçamento sem traços/espaços, max 25; "***" genérico)
    txid_raw = descricao.replace("-", "").replace(" ", "")[:25] if descricao else "***"
    txid_clean = "".join(c for c in txid_raw if c.isalnum()) or "***"
    payload += _emv_field("62", _emv_field("05", txid_clean))

    # CRC16 — deve ser o último campo
    payload += "6304"
    payload += f"{_crc16(payload):04X}"

    return payload


def gerar_qrcode_pix(
    chave: str,
    nome_recebedor: str,
    cidade: str = "BRASIL",
    valor: float = None,
) -> str:
    """Gera QR Code PIX válido (padrão EMV BRCode) e retorna como base64 PNG.

    Args:
        chave: Chave PIX.
        nome_recebedor: Nome do titular da conta.
        cidade: Cidade do recebedor.
        valor: Valor da transação (opcional).

    Returns:
        String base64 da imagem PNG do QR code.
    """
    payload = gerar_payload_pix(chave, nome_recebedor, cidade, valor)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode()
