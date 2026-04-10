"""
Serviço de preferências adaptativas do assistente IA.

Responsabilidades:
- Resolver instruções/guardrails por empresa.
- Resolver e atualizar preferência de visualização por usuário.
- Gerar playbook automático por setor com janela 7/30/90 dias.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session


class AssistantPreferencesService:
    _FORMATOS_VALIDOS = {"auto", "resumo", "tabela"}

    @staticmethod
    def _normalizar_dominio(dominio: Optional[str]) -> str:
        dom = (dominio or "geral").strip().lower()
        if dom in {"financeiro", "orcamentos", "clientes", "agendamentos", "comercial", "gestao"}:
            return dom
        return "geral"

    @classmethod
    def _normalizar_formato(cls, formato: Optional[str]) -> str:
        f = (formato or "auto").strip().lower()
        return f if f in cls._FORMATOS_VALIDOS else "auto"

    @staticmethod
    def inferir_dominio(mensagem: str) -> str:
        msg = (mensagem or "").lower()
        if any(k in msg for k in ("fluxo", "financeiro", "caixa", "receber", "pagar", "despesa", "faturamento")):
            return "financeiro"
        if any(k in msg for k in ("orcamento", "orçamento", "aprovar", "recusar", "proposta")):
            return "orcamentos"
        if any(k in msg for k in ("cliente", "telefone", "contato", "email")):
            return "clientes"
        if any(k in msg for k in ("agenda", "agendamento", "remarcar", "cancelar agendamento")):
            return "agendamentos"
        if any(k in msg for k in ("lead", "pipeline", "crm", "comercial", "vendas")):
            return "comercial"
        return "geral"

    @classmethod
    def upsert_preferencia_visualizacao(
        cls,
        db: Session,
        *,
        empresa_id: int,
        usuario_id: int,
        formato_preferido: str,
        dominio: str = "geral",
    ) -> dict:
        from app.models.models import AssistentePreferenciaUsuario

        dom = cls._normalizar_dominio(dominio)
        formato = cls._normalizar_formato(formato_preferido)

        pref = (
            db.query(AssistentePreferenciaUsuario)
            .filter(
                AssistentePreferenciaUsuario.empresa_id == empresa_id,
                AssistentePreferenciaUsuario.usuario_id == usuario_id,
                AssistentePreferenciaUsuario.dominio == dom,
            )
            .first()
        )
        if not pref:
            pref = AssistentePreferenciaUsuario(
                empresa_id=empresa_id,
                usuario_id=usuario_id,
                dominio=dom,
                formato_preferido=formato,
                confianca=0.7 if formato != "auto" else 0.5,
            )
            db.add(pref)
        else:
            pref.formato_preferido = formato
            pref.confianca = min(1.0, float(pref.confianca or 0.5) + 0.1) if formato != "auto" else 0.5
        db.commit()
        db.refresh(pref)
        return {
            "dominio": pref.dominio,
            "formato_preferido": pref.formato_preferido,
            "confianca": round(float(pref.confianca or 0.5), 2),
        }

    @classmethod
    def obter_preferencia_visualizacao(
        cls,
        db: Session,
        *,
        empresa_id: int,
        usuario_id: int,
        dominio: str,
    ) -> dict:
        from app.models.models import AssistentePreferenciaUsuario

        dom = cls._normalizar_dominio(dominio)
        pref = (
            db.query(AssistentePreferenciaUsuario)
            .filter(
                AssistentePreferenciaUsuario.empresa_id == empresa_id,
                AssistentePreferenciaUsuario.usuario_id == usuario_id,
                AssistentePreferenciaUsuario.dominio == dom,
            )
            .first()
        )
        if not pref and dom != "geral":
            pref = (
                db.query(AssistentePreferenciaUsuario)
                .filter(
                    AssistentePreferenciaUsuario.empresa_id == empresa_id,
                    AssistentePreferenciaUsuario.usuario_id == usuario_id,
                    AssistentePreferenciaUsuario.dominio == "geral",
                )
                .first()
            )
        if not pref:
            return {"dominio": dom, "formato_preferido": "auto", "confianca": 0.5}
        return {
            "dominio": dom,
            "formato_preferido": pref.formato_preferido or "auto",
            "confianca": round(float(pref.confianca or 0.5), 2),
        }

    @staticmethod
    def _resolver_setor_usuario(db: Session, *, empresa_id: int, usuario_id: int) -> str:
        from app.models.models import Usuario, Papel

        user = (
            db.query(Usuario.id, Usuario.is_gestor, Usuario.papel_id)
            .filter(Usuario.id == usuario_id, Usuario.empresa_id == empresa_id)
            .first()
        )
        if not user:
            return "geral"
        if user.is_gestor:
            return "gestao"
        if user.papel_id:
            papel = db.query(Papel.slug, Papel.nome).filter(Papel.id == user.papel_id).first()
            slug = (papel.slug or "") if papel else ""
            nome = (papel.nome or "") if papel else ""
            txt = (slug or nome).lower()
            if "finance" in txt:
                return "financeiro"
            if "comercial" in txt or "venda" in txt:
                return "comercial"
        return "geral"

    @staticmethod
    def _base_playbook_por_setor(setor: str) -> dict:
        if setor == "financeiro":
            return {
                "kpis": ["saldo_atual", "resultado_periodo", "receitas_vs_despesas", "inadimplencia"],
                "acoes": ["mostrar_fluxo_caixa", "listar_contas_vencendo", "priorizar_cobranca", "sugerir_reducao_despesas"],
            }
        if setor == "comercial":
            return {
                "kpis": ["taxa_conversao", "ticket_medio", "orcamentos_pendentes", "tempo_resposta_cliente"],
                "acoes": ["listar_orcamentos_pendentes", "sugerir_followups", "priorizar_leads_quentes", "preparar_proxima_proposta"],
            }
        if setor == "gestao":
            return {
                "kpis": ["resultado_periodo", "margem_estimada", "pipeline_comercial", "alertas_operacionais"],
                "acoes": ["resumo_executivo", "priorizar_gargalos", "sugerir_plano_7_dias", "acompanhar_meta_mensal"],
            }
        return {
            "kpis": ["resumo_geral", "alertas", "proximas_acoes"],
            "acoes": ["resumir_contexto", "propor_prioridades", "sugerir_proximos_passos"],
        }

    @classmethod
    def build_playbook_setor(
        cls,
        db: Session,
        *,
        empresa_id: int,
        usuario_id: int,
    ) -> dict:
        from app.models.models import FeedbackAssistente, ToolCallLog

        setor = cls._resolver_setor_usuario(db, empresa_id=empresa_id, usuario_id=usuario_id)
        base = cls._base_playbook_por_setor(setor)
        now = datetime.now(timezone.utc)
        janelas = [7, 30, 90]
        metricas: dict[str, Any] = {}

        for dias in janelas:
            inicio = now - timedelta(days=dias)
            total_fb = (
                db.query(func.count(FeedbackAssistente.id))
                .filter(
                    FeedbackAssistente.empresa_id == empresa_id,
                    FeedbackAssistente.criado_em >= inicio,
                )
                .scalar()
                or 0
            )
            positivos_fb = (
                db.query(func.count(FeedbackAssistente.id))
                .filter(
                    FeedbackAssistente.empresa_id == empresa_id,
                    FeedbackAssistente.criado_em >= inicio,
                    FeedbackAssistente.avaliacao == "positivo",
                )
                .scalar()
                or 0
            )
            taxa_sucesso = round((positivos_fb / total_fb), 3) if total_fb else 0.5
            total_tools = (
                db.query(func.count(ToolCallLog.id))
                .filter(
                    ToolCallLog.empresa_id == empresa_id,
                    ToolCallLog.criado_em >= inicio,
                    ToolCallLog.status == "ok",
                )
                .scalar()
                or 0
            )
            metricas[f"{dias}d"] = {
                "feedback_total": int(total_fb),
                "feedback_positivo": int(positivos_fb),
                "taxa_sucesso": taxa_sucesso,
                "tools_ok": int(total_tools),
            }

        score_90d = (metricas.get("90d") or {}).get("taxa_sucesso", 0.5)
        # Mantém ordem base; quando sucesso baixo, prioriza ações de diagnóstico.
        acoes = list(base["acoes"])
        if score_90d < 0.45 and "resumo_executivo" not in acoes:
            acoes = ["resumir_contexto", *acoes]

        return {
            "setor": setor,
            "janelas": metricas,
            "kpis_prioritarios": base["kpis"],
            "acoes_sugeridas_ordenadas": acoes,
        }

    @classmethod
    def get_context_for_prompt(
        cls,
        db: Session,
        *,
        empresa_id: int,
        usuario_id: int,
        mensagem: str,
    ) -> dict:
        from app.models.models import Empresa

        dominio = cls.inferir_dominio(mensagem)
        empresa = db.query(Empresa.id, Empresa.assistente_instrucoes).filter(Empresa.id == empresa_id).first()
        pref = cls.obter_preferencia_visualizacao(
            db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            dominio=dominio,
        )
        playbook = cls.build_playbook_setor(
            db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        return {
            "dominio_contextual": dominio,
            "instrucoes_empresa": (empresa.assistente_instrucoes if empresa else None) or "",
            "preferencia_visualizacao_usuario": pref,
            "playbook_setor": playbook,
            "regra_hibrida": (
                "Instruções da empresa são guardrails obrigatórios; "
                "preferência do usuário ajusta formato e ordem dentro desses limites."
            ),
        }
