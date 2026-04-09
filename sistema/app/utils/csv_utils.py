"""Utilitários centralizados para geração de CSV.

Elimina duplicação do padrão io.StringIO + csv.writer
usado em orcamentos, clientes e financeiro.
"""

import csv
import io
from datetime import datetime
from typing import List

from fastapi.responses import StreamingResponse


def gerar_csv_response(
    header: List[str],
    rows: List[List[str]],
    filename_prefix: str,
) -> StreamingResponse:
    """Gera StreamingResponse CSV com delimitador ponto-e-vírgula.

    Args:
        header: Lista de nomes das colunas.
        rows: Lista de linhas (cada linha é lista de strings).
        filename_prefix: Prefixo do arquivo (ex: "orcamentos").

    Returns:
        StreamingResponse com Content-Disposition para download.
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    output.seek(0)
    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
