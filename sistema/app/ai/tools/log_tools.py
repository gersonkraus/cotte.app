"""Tools de diagnóstico: histórico de execução de ferramentas (ToolCallLog)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.models import ToolCallLog, Usuario

from ._base import ToolSpec


class AnalisarToolLogsInput(BaseModel):
    tool_name: Optional[str] = Field(
        default=None,
        description="Filtrar por nome da tool (ex: 'criar_orcamento'). Se omitido, retorna todas.",
    )
    horas_retroativas: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Janela de tempo em horas para trás (padrão 24h, máximo 7 dias).",
    )
    status: Optional[str] = Field(
        default=None,
        description=(
            "Filtrar por status: 'ok', 'erro', 'forbidden', 'pending', "
            "'invalid_input', 'unknown_tool'."
        ),
    )
    limit: int = Field(default=20, ge=1, le=50)


async def _analisar_tool_logs(
    inp: AnalisarToolLogsInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    inicio = datetime.now(ZoneInfo("America/Sao_Paulo")) - timedelta(hours=inp.horas_retroativas)

    q = db.query(ToolCallLog).filter(
        ToolCallLog.empresa_id == current_user.empresa_id,
        ToolCallLog.criado_em >= inicio,
    )
    if inp.tool_name:
        q = q.filter(ToolCallLog.tool == inp.tool_name.strip())
    if inp.status:
        q = q.filter(ToolCallLog.status == inp.status.strip())

    logs = q.order_by(ToolCallLog.criado_em.desc()).limit(inp.limit).all()

    _campos_resultado_seguros = {"erro", "mensagem", "resposta", "status", "code"}
    registros = []
    for log in logs:
        resultado_resumido = None
        if log.resultado_json and isinstance(log.resultado_json, dict):
            resultado_resumido = {
                k: v for k, v in log.resultado_json.items()
                if k in _campos_resultado_seguros
            }
        registros.append({
            "id": log.id,
            "tool": log.tool,
            "status": log.status,
            "latencia_ms": log.latencia_ms,
            "criado_em": log.criado_em.isoformat() if log.criado_em else None,
            "args": log.args_json,
            "resultado_resumido": resultado_resumido,
        })

    total_erros = sum(1 for r in registros if r["status"] == "erro")
    return {
        "total": len(registros),
        "erros": total_erros,
        "periodo_horas": inp.horas_retroativas,
        "instrucao_para_assistente": (
            "Analise os logs retornados e identifique padrões de erro, "
            "tools mais usadas e possíveis causas de falha."
        ),
        "logs": registros,
    }


analisar_tool_logs = ToolSpec(
    name="analisar_tool_logs",
    description=(
        "Consulta o histórico de execução das ferramentas do assistente IA da empresa. "
        "Use para diagnosticar erros (ex: 'Por que criar_orcamento falhou hoje?'), "
        "verificar padrões de uso e auditar chamadas recentes."
    ),
    input_model=AnalisarToolLogsInput,
    handler=_analisar_tool_logs,
    destrutiva=False,
    cacheable_ttl=10,
    permissao_recurso="ia",
    permissao_acao="leitura",
)
