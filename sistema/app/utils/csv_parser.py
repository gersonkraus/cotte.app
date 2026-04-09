import binascii
import base64
import logging
from typing import List
from app.schemas.schemas import LeadImportItem

logger = logging.getLogger(__name__)


def parse_csv_to_leads(csv_base64: str) -> List[LeadImportItem]:
    """Parse CSV base64 para lista de leads."""
    try:
        # Decodificar base64
        csv_bytes = base64.b64decode(csv_base64)
        csv_text = csv_bytes.decode('utf-8')

        leads = []
        lines = csv_text.strip().split('\n')

        # Pular cabeçalho se existir
        start_line = 1 if lines and lines[0].lower().startswith('nome') else 0

        for line in lines[start_line:]:
            if not line.strip():
                continue

            # Formato CSV: Nome,WhatsApp,Email,Cidade
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 2:
                nome = parts[0]
                whatsapp = parts[1] if len(parts) > 1 else None
                email = parts[2] if len(parts) > 2 else None
                cidade = parts[3] if len(parts) > 3 else None

                leads.append(LeadImportItem(
                    nome_responsavel=nome,
                    nome_empresa=nome,
                    whatsapp=whatsapp,
                    email=email,
                    cidade=cidade,
                    observacoes="Importado via CSV"
                ))

        return leads

    except (UnicodeDecodeError, binascii.Error) as e:
        logger.error(f"Erro ao parsear CSV: {e}")
        return []