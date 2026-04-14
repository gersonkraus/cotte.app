"""
COTTE Context Builder - Gerenciamento de sessões e contexto de dados para o assistente IA.

Fornece:
- SessionStore: histórico de conversa persistido no banco (AIChatSessao + AIChatMensagem)
  com cache L1 em RAM para leitura rápida.
- ContextBuilder: busca dados do banco baseado na intenção detectada
"""

import logging
import os
import re
import unicodedata
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

logger = logging.getLogger(__name__)

# ── Cache L1 em RAM (performance) ─────────────────────────────────────────
# O banco (AIChatSessao/AIChatMensagem) é a fonte de verdade.
# Este dicionário serve apenas como fast-path para evitar queries repetitivas
# dentro da mesma sessão de servidor. Ao reiniciar, a fonte de verdade é o banco.

_sessions: dict[str, dict] = {}  # cache em RAM para sugestões e hot-path
SESSION_TTL_MINUTES = 120  # aumentado para 2h
MAX_MESSAGES_PER_SESSION = 12  # 6 turnos user + 6 assistant (maior contexto)
_semantic_cache: dict[str, dict[str, Any]] = {}
SEMANTIC_CACHE_TTL_SECONDS = 180


def _prune_expired():
    """Remove sessões expiradas do cache RAM (chamado lazily a cada get_or_create)."""
    cutoff = datetime.utcnow() - timedelta(minutes=SESSION_TTL_MINUTES)
    to_delete = [k for k, v in _sessions.items() if v.get("last_seen", datetime.min) < cutoff]
    for k in to_delete:
        del _sessions[k]


class SessionStore:
    """
    Gerencia histórico de conversas — persiste no banco PostgreSQL e mantém
    cache L1 em RAM para acesso rápido dentro da mesma instância.

    Estratégia:
    - `get_or_create`: tenta cache RAM primeiro, senão busca no banco (recovery pós-reinício).
    - `append`: escreve no banco E no cache RAM simultaneamente.
    - `append_db`: utilitário que recebe `db` para operações com transação ativa.
    """

    MAX_SUGGESTIONS_TRACKED = 50

    @staticmethod
    def _cache_key(sessao_id: str, empresa_id: int = 0, usuario_id: int = 0) -> str:
        return f"{empresa_id or 0}:{usuario_id or 0}:{sessao_id}"

    @staticmethod
    def _resolve_cache_key(sessao_id: str, empresa_id: int = 0, usuario_id: int = 0) -> str:
        scoped = SessionStore._cache_key(sessao_id, empresa_id, usuario_id)
        if scoped in _sessions:
            return scoped
        legacy = sessao_id
        if legacy in _sessions:
            return legacy
        # Compatibilidade: alguns caminhos antigos consultam apenas por sessao_id.
        # Se houver exatamente um match com sufixo ":sessao_id", reutilizamos.
        if not empresa_id and not usuario_id:
            matches = [k for k in _sessions.keys() if k.endswith(f":{sessao_id}")]
            if len(matches) == 1:
                return matches[0]
        return scoped

    @staticmethod
    def get_or_create(sessao_id: str, db: Optional[Session] = None, empresa_id: int = 0, usuario_id: int = 0) -> list[dict]:
        """
        Retorna o histórico de mensagens da sessão.
        1. Tenta cache RAM.
        2. Se não encontrar, recupera do banco (survival pós-reinício).
        """
        _prune_expired()

        cache_key = SessionStore._resolve_cache_key(sessao_id, empresa_id, usuario_id)

        # Cache RAM hit — retorna imediatamente sem query
        if cache_key in _sessions:
            _sessions[cache_key]["last_seen"] = datetime.utcnow()
            return list(_sessions[cache_key]["messages"])

        # Cache miss — inicializa estrutura de dados em RAM
        _sessions[cache_key] = {
            "messages": deque(maxlen=MAX_MESSAGES_PER_SESSION),
            "seen_suggestions": deque(maxlen=SessionStore.MAX_SUGGESTIONS_TRACKED),
            "last_seen": datetime.utcnow(),
        }

        # Recovery do banco: recuperar mensagens persistidas (pós-reinício)
        if db is not None:
            try:
                from app.models.models import AIChatSessao, AIChatMensagem

                # Garante que a sessão existe no banco
                sessao_any = (
                    db.query(AIChatSessao).filter(AIChatSessao.id == sessao_id).first()
                )
                if sessao_any and empresa_id and sessao_any.empresa_id != empresa_id:
                    logger.warning(
                        "[SessionStore] Sessão %s bloqueada por escopo de empresa (%s != %s)",
                        sessao_id[:8],
                        sessao_any.empresa_id,
                        empresa_id,
                    )
                    sessao_db = None
                else:
                    sessao_db = sessao_any
                if not sessao_db and empresa_id and not sessao_any:
                    sessao_db = AIChatSessao(
                        id=sessao_id,
                        empresa_id=empresa_id,
                        usuario_id=usuario_id or 0,
                    )
                    db.add(sessao_db)
                    try:
                        db.commit()
                    except Exception:
                        db.rollback()

                # Carrega últimas mensagens do banco para o cache RAM
                msgs_q = (
                    db.query(AIChatMensagem)
                    .join(AIChatSessao, AIChatMensagem.sessao_id == AIChatSessao.id)
                    .filter(AIChatMensagem.sessao_id == sessao_id)
                )
                if empresa_id:
                    msgs_q = msgs_q.filter(AIChatSessao.empresa_id == empresa_id)
                msgs_db = (
                    msgs_q.order_by(AIChatMensagem.criado_em.asc())
                    .limit(MAX_MESSAGES_PER_SESSION)
                    .all()
                )
                for m in msgs_db:
                    _sessions[cache_key]["messages"].append({"role": m.role, "content": m.content})

                if msgs_db:
                    logger.debug(f"[SessionStore] Recovery: {len(msgs_db)} msgs restauradas para sessão {sessao_id[:8]}")

            except Exception as e:
                logger.warning(f"[SessionStore] Erro ao recuperar sessão do banco: {e}")

        _sessions[cache_key]["last_seen"] = datetime.utcnow()
        return list(_sessions[cache_key]["messages"])

    @staticmethod
    def append(
        sessao_id: str,
        role: str,
        content: str,
        empresa_id: int = 0,
        usuario_id: int = 0,
    ):
        """Adiciona mensagem ao cache RAM (sem persistência no banco — use append_db para persistir)."""
        cache_key = SessionStore._resolve_cache_key(sessao_id, empresa_id, usuario_id)
        if cache_key not in _sessions:
            SessionStore.get_or_create(
                sessao_id,
                empresa_id=empresa_id,
                usuario_id=usuario_id,
            )
        _sessions[cache_key]["messages"].append({"role": role, "content": content})
        _sessions[cache_key]["last_seen"] = datetime.utcnow()

    @staticmethod
    def append_db(
        sessao_id: str,
        role: str,
        content: str,
        db: Session,
        empresa_id: int = 0,
        usuario_id: int = 0,
    ):
        """
        Adiciona mensagem ao cache RAM E persiste no banco PostgreSQL.
        Usar em todos os fluxos definitivos (assistente_unificado_v2, etc.).
        """
        # Persiste no banco
        try:
            from app.models.models import AIChatMensagem, AIChatSessao
            sessao_q = db.query(AIChatSessao).filter(AIChatSessao.id == sessao_id)
            if empresa_id:
                sessao_q = sessao_q.filter(AIChatSessao.empresa_id == empresa_id)
            if not sessao_q.first():
                logger.warning(
                    "[SessionStore] Sessão %s não encontrada no escopo empresa=%s; pulando persistência",
                    sessao_id[:8],
                    empresa_id,
                )
                SessionStore.append(
                    sessao_id,
                    role,
                    content,
                    empresa_id=empresa_id,
                    usuario_id=usuario_id,
                )
                return
            msg_db = AIChatMensagem(sessao_id=sessao_id, role=role, content=content)
            db.add(msg_db)
            db.commit()
        except Exception as e:
            logger.warning(f"[SessionStore] Erro ao persistir mensagem no banco: {e}")
            try:
                db.rollback()
            except Exception:
                pass

        # Atualiza cache RAM
        SessionStore.append(
            sessao_id,
            role,
            content,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )

    @staticmethod
    def ensure_sessao_db(sessao_id: str, empresa_id: int, usuario_id: int, db: Session) -> None:
        """Garante que a sessão existe no banco. Idempotente."""
        try:
            from app.models.models import AIChatSessao
            existe = db.query(AIChatSessao).filter(AIChatSessao.id == sessao_id).first()
            if existe and existe.empresa_id != empresa_id:
                logger.warning(
                    "[SessionStore] Sessão %s pertence a empresa diferente (%s != %s)",
                    sessao_id[:8],
                    existe.empresa_id,
                    empresa_id,
                )
                return
            if not existe:
                db.add(AIChatSessao(
                    id=sessao_id,
                    empresa_id=empresa_id,
                    usuario_id=usuario_id,
                ))
                db.commit()
        except Exception as e:
            logger.warning(f"[SessionStore] Erro ao criar sessão no banco: {e}")
            try:
                db.rollback()
            except Exception:
                pass

    @staticmethod
    def add_seen_suggestions(
        sessao_id: str,
        sugestoes: list[str],
        empresa_id: int = 0,
        usuario_id: int = 0,
    ):
        """Registra sugestões já vistas para evitar repetição."""
        cache_key = SessionStore._resolve_cache_key(sessao_id, empresa_id, usuario_id)
        if cache_key not in _sessions:
            SessionStore.get_or_create(
                sessao_id,
                empresa_id=empresa_id,
                usuario_id=usuario_id,
            )
        normalized = [s.strip().lower()[:100] for s in sugestoes if s]
        _sessions[cache_key]["seen_suggestions"].extend(normalized)
        _sessions[cache_key]["last_seen"] = datetime.utcnow()

    @staticmethod
    def filter_new_suggestions(
        sessao_id: str,
        sugestoes: list[str],
        empresa_id: int = 0,
        usuario_id: int = 0,
    ) -> list[str]:
        """Filtra sugestões já vistas, retornando apenas as novas."""
        cache_key = SessionStore._resolve_cache_key(sessao_id, empresa_id, usuario_id)
        if cache_key not in _sessions:
            return sugestoes
        seen = set(_sessions[cache_key].get("seen_suggestions", []))
        return [s for s in sugestoes if s.strip().lower()[:100] not in seen]

    @staticmethod
    def get_suggestion_context(
        sessao_id: str,
        empresa_id: int = 0,
        usuario_id: int = 0,
    ) -> dict:
        """Retorna contexto de sugestões da sessão para o prompt."""
        cache_key = SessionStore._resolve_cache_key(sessao_id, empresa_id, usuario_id)
        if cache_key not in _sessions:
            return {"seen_count": 0, "recent": []}
        seen = list(_sessions[cache_key].get("seen_suggestions", []))
        return {
            "seen_count": len(seen),
            "recent": seen[-10:] if len(seen) > 10 else seen,
        }


class SemanticMemoryStore:
    """
    Memória semântica por empresa para perguntas recorrentes no assistente v2.

    Estratégia:
    - Busca mensagens históricas do usuário (AIChatMensagem) da empresa
    - Calcula similaridade léxica simples por sobreposição de tokens
    - Resume padrões de uso de tools por domínio (ToolCallLog)
    - Faz cache curto em RAM para reduzir custo em perguntas repetidas
    """

    _STOPWORDS = {
        "como", "qual", "quais", "meu", "minha", "meus", "minhas", "para",
        "com", "sem", "dos", "das", "uma", "umas", "uns", "por", "que",
        "tem", "tenho", "sobre", "isso", "hoje", "ontem", "amanha", "amanhã",
        "favor", "pode", "mostrar", "dizer", "fazer", "ser", "está", "esta",
    }

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        txt = (text or "").strip().lower()
        txt = unicodedata.normalize("NFKD", txt)
        txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
        txt = re.sub(r"[^a-z0-9\s]", " ", txt)
        txt = re.sub(r"\s+", " ", txt).strip()
        return txt

    @classmethod
    def _tokens(cls, text: str) -> list[str]:
        toks = [t for t in cls._normalize_text(text).split(" ") if len(t) >= 3]
        return [t for t in toks if t not in cls._STOPWORDS]

    @classmethod
    def _infer_domain(cls, mensagem: str) -> str:
        msg = cls._normalize_text(mensagem)
        if any(k in msg for k in ("fluxo", "financeiro", "caixa", "receber", "pagar", "despesa", "faturamento")):
            return "financeiro"
        if any(k in msg for k in ("orcamento", "proposta", "aprovar", "recusar", "desconto")):
            return "orcamentos"
        if any(k in msg for k in ("cliente", "telefone", "email", "contato")):
            return "clientes"
        if any(k in msg for k in ("agenda", "agendamento", "remarcar", "cancelar agendamento")):
            return "agendamentos"
        return "geral"

    @classmethod
    def _cache_key(cls, empresa_id: int, mensagem: str) -> str:
        domain = cls._infer_domain(mensagem)
        tokens = cls._tokens(mensagem)[:4]
        return f"{empresa_id}:{domain}:{'|'.join(tokens)}"

    @classmethod
    def _cache_key_with_user(cls, empresa_id: int, usuario_id: int, mensagem: str) -> str:
        base = cls._cache_key(empresa_id, mensagem)
        return f"{base}:u{usuario_id or 0}"

    @classmethod
    def _cache_get(cls, key: str) -> Optional[dict]:
        item = _semantic_cache.get(key)
        if not item:
            return None
        if item["expires_at"] < datetime.now(timezone.utc):
            _semantic_cache.pop(key, None)
            return None
        return item["value"]

    @classmethod
    def _cache_set(cls, key: str, value: dict) -> None:
        _semantic_cache[key] = {
            "value": value,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=SEMANTIC_CACHE_TTL_SECONDS),
        }

    @classmethod
    def _infer_response_style(cls, domain: str, frequencia_90d: int) -> dict:
        if frequencia_90d >= 40:
            gran = "executiva"
            tom = "direto"
        elif frequencia_90d >= 12:
            gran = "equilibrada"
            tom = "consultivo"
        else:
            gran = "didatica"
            tom = "orientativo"

        if domain == "financeiro":
            return {"tom": tom, "granularidade": gran, "prioridade_kpis": ["saldo_atual", "resultado_periodo", "receitas_vs_despesas", "inadimplencia"]}
        if domain == "orcamentos":
            return {"tom": tom, "granularidade": gran, "prioridade_kpis": ["taxa_aprovacao", "ticket_medio", "orcamentos_pendentes", "tempo_medio_conversao"]}
        if domain == "clientes":
            return {"tom": tom, "granularidade": gran, "prioridade_kpis": ["clientes_ativos", "clientes_novos_periodo", "recorrencia_cliente", "ticket_por_cliente"]}
        if domain == "agendamentos":
            return {"tom": tom, "granularidade": gran, "prioridade_kpis": ["agendamentos_hoje", "confirmacao", "no_show", "ocupacao_proximos_7_dias"]}
        return {"tom": tom, "granularidade": gran, "prioridade_kpis": ["resumo_geral", "alertas", "proximas_acoes"]}

    @classmethod
    def _build_dynamic_profile(
        cls,
        db: Session,
        empresa_id: int,
        usuario_id: int,
        domain: str,
        mensagem: str,
    ) -> dict:
        from app.models.models import AIChatMensagem, AIChatSessao, ToolCallLog, Usuario, Papel

        now = datetime.now(timezone.utc)
        windows = [7, 30, 90]
        metricas: dict[str, dict] = {}

        # Resolve setor/papel do usuário
        setor_nome = "geral"
        usuario_nome = "usuario"
        try:
            user = (
                db.query(Usuario.id, Usuario.nome, Usuario.is_gestor, Usuario.papel_id)
                .filter(Usuario.id == usuario_id, Usuario.empresa_id == empresa_id)
                .first()
            )
            if user:
                usuario_nome = user.nome or "usuario"
                if user.is_gestor:
                    setor_nome = "gestao"
                if getattr(user, "papel_id", None):
                    papel = db.query(Papel.nome, Papel.slug).filter(Papel.id == user.papel_id).first()
                    if papel:
                        setor_nome = (papel.slug or papel.nome or setor_nome or "geral").lower()
        except Exception:
            pass

        for days in windows:
            inicio = now - timedelta(days=days)
            # Frequência operacional no domínio (base: ToolCallLog)
            q_tools = (
                db.query(func.count(ToolCallLog.id))
                .filter(
                    ToolCallLog.empresa_id == empresa_id,
                    ToolCallLog.criado_em >= inicio,
                    ToolCallLog.status == "ok",
                )
            )
            if domain == "financeiro":
                q_tools = q_tools.filter(ToolCallLog.tool.ilike("%financeir%") | ToolCallLog.tool.ilike("%saldo%") | ToolCallLog.tool.ilike("%moviment%"))
            elif domain == "orcamentos":
                q_tools = q_tools.filter(ToolCallLog.tool.ilike("%orcamento%"))
            elif domain == "clientes":
                q_tools = q_tools.filter(ToolCallLog.tool.ilike("%cliente%"))
            elif domain == "agendamentos":
                q_tools = q_tools.filter(ToolCallLog.tool.ilike("%agendamento%"))

            uso_tools = int(q_tools.scalar() or 0)

            # Recorrência da intenção em perguntas do chat
            msgs = (
                db.query(AIChatMensagem.content)
                .join(AIChatSessao, AIChatMensagem.sessao_id == AIChatSessao.id)
                .filter(
                    AIChatSessao.empresa_id == empresa_id,
                    AIChatMensagem.role == "user",
                    AIChatMensagem.criado_em >= inicio,
                )
                .order_by(AIChatMensagem.criado_em.desc())
                .limit(180)
                .all()
            )
            q_tokens = set(cls._tokens(mensagem))
            recorrencia = 0
            for r in msgs:
                txt = (r.content or "").strip()
                if not txt:
                    continue
                overlap = len(q_tokens.intersection(set(cls._tokens(txt))))
                if overlap >= 2:
                    recorrencia += 1

            metricas[f"{days}d"] = {
                "uso_tools_dominio": uso_tools,
                "perguntas_semelhantes": recorrencia,
                "frequencia_operacional": uso_tools + recorrencia,
            }

        freq_90d = (metricas.get("90d") or {}).get("frequencia_operacional", 0)
        style = cls._infer_response_style(domain, int(freq_90d))
        return {
            "usuario_id": usuario_id,
            "usuario_nome": usuario_nome,
            "setor": setor_nome,
            "janelas": metricas,
            "estilo_resposta_recomendado": style,
            "regra_adaptacao": (
                "Use tom/granularidade recomendados e priorize KPIs na ordem informada. "
                "Quando houver baixa frequência, explique premissas; com alta frequência, responda de forma objetiva."
            ),
        }

    @classmethod
    def build_context(cls, db: Session, empresa_id: int, mensagem: str, usuario_id: int = 0) -> dict:
        try:
            from app.models.models import AIChatMensagem, AIChatSessao, ToolCallLog, Cliente
        except Exception:
            return {}

        key = cls._cache_key_with_user(empresa_id, usuario_id, mensagem)
        cached = cls._cache_get(key)
        if cached is not None:
            return cached

        domain = cls._infer_domain(mensagem)
        q_tokens = set(cls._tokens(mensagem))

        # 1) Histórico de perguntas similares na empresa (recência + overlap)
        rows = (
            db.query(AIChatMensagem.content)
            .join(AIChatSessao, AIChatMensagem.sessao_id == AIChatSessao.id)
            .filter(
                AIChatSessao.empresa_id == empresa_id,
                AIChatMensagem.role == "user",
            )
            .order_by(AIChatMensagem.criado_em.desc())
            .limit(120)
            .all()
        )

        similares: list[tuple[int, str]] = []
        for r in rows:
            txt = (r.content or "").strip()
            if not txt:
                continue
            overlap = len(q_tokens.intersection(set(cls._tokens(txt))))
            if overlap >= 2:
                similares.append((overlap, txt))
        similares.sort(key=lambda x: x[0], reverse=True)
        perguntas_recorrentes = []
        seen = set()
        for _, txt in similares:
            norm = cls._normalize_text(txt)
            if norm in seen:
                continue
            seen.add(norm)
            perguntas_recorrentes.append(txt[:160])
            if len(perguntas_recorrentes) >= 4:
                break

        # 2) Padrão operacional por domínio (tools mais usadas)
        tool_rows = (
            db.query(ToolCallLog.tool)
            .filter(ToolCallLog.empresa_id == empresa_id, ToolCallLog.status == "ok")
            .order_by(ToolCallLog.criado_em.desc())
            .limit(200)
            .all()
        )
        tool_counts: dict[str, int] = {}
        for tr in tool_rows:
            t = tr.tool or ""
            if not t:
                continue
            if domain == "financeiro" and not any(k in t for k in ("saldo", "moviment", "despesa", "pagamento", "parcel")):
                continue
            if domain == "orcamentos" and "orcamento" not in t:
                continue
            if domain == "clientes" and "cliente" not in t:
                continue
            if domain == "agendamentos" and "agendamento" not in t:
                continue
            tool_counts[t] = tool_counts.get(t, 0) + 1
        top_tools = sorted(tool_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]

        # 3) Contexto de cliente mencionado (quando houver "cliente X")
        cliente_ctx = None
        m = re.search(r"cliente\s+([a-zA-ZÀ-ÿ0-9 .'-]{2,80})", mensagem or "", re.IGNORECASE)
        if m:
            nome_busca = m.group(1).strip()
            cands = (
                db.query(Cliente.id, Cliente.nome)
                .filter(
                    Cliente.empresa_id == empresa_id,
                    Cliente.nome.ilike(f"%{nome_busca}%"),
                )
                .limit(5)
                .all()
            )
            if cands:
                cliente_ctx = [{"id": c.id, "nome": c.nome} for c in cands]

        value = {
            "dominio_detectado": domain,
            "perguntas_recorrentes_semelhantes": perguntas_recorrentes,
            "top_tools_dominio": [{"tool": t, "usos": n} for t, n in top_tools],
            "clientes_relacionados": cliente_ctx,
            "perfil_operacional_dinamico": cls._build_dynamic_profile(
                db=db,
                empresa_id=empresa_id,
                usuario_id=usuario_id,
                domain=domain,
                mensagem=mensagem,
            ),
        }
        cls._cache_set(key, value)
        return value


# ── Context Builder ────────────────────────────────────────────────────────


class ContextBuilder:
    """
    Constrói o contexto de dados do banco baseado na intenção detectada.
    Todos os métodos são async para permitir chamadas a funções async existentes.
    """

    # Mapeamento: intenção → método de busca
    _INTENT_MAP = {
        "SALDO_RAPIDO": "_ctx_financeiro",
        "FATURAMENTO": "_ctx_financeiro",
        "CONTAS_RECEBER": "_ctx_financeiro",
        "CONTAS_PAGAR": "_ctx_financeiro",
        "DASHBOARD": "_ctx_geral",
        "PREVISAO": "_ctx_financeiro",
        "INADIMPLENCIA": "_ctx_financeiro",
        "ANALISE": "_ctx_geral",
        "CONVERSAO": "_ctx_orcamentos",
        "NEGOCIO": "_ctx_geral",
        "CONVERSACAO": "_ctx_geral_com_ajuda",
        "AJUDA_SISTEMA": "_ctx_ajuda_sistema",
        "AGENDAMENTO_CRIAR": "_ctx_agendamentos",
        "AGENDAMENTO_LISTAR": "_ctx_agendamentos",
        "AGENDAMENTO_STATUS": "_ctx_agendamentos",
        "AGENDAMENTO_CANCELAR": "_ctx_agendamentos",
    }

    # Cache singleton da knowledge base (parseada uma vez no startup)
    _kb_cache: dict[str, str] | None = None
    _kb_resumo: str = ""

    @classmethod
    async def build(
        cls,
        intencao: str,
        db: Session,
        empresa_id: int,
        usuario_id: int = 0,
        mensagem: str = "",
    ) -> dict:
        """
        Retorna dict com dados relevantes do banco para a intenção fornecida.
        Retorna {} em caso de erro (nunca lança exceção).
        """
        fn_name = cls._INTENT_MAP.get(intencao, "_ctx_geral")
        fn = getattr(cls, fn_name)
        try:
            # AJUDA_SISTEMA recebe a mensagem para detectar seção relevante
            if intencao == "AJUDA_SISTEMA":
                ctx = await fn(db, empresa_id, mensagem)
            else:
                ctx = await fn(db, empresa_id)
        except Exception as e:
            logger.warning(
                f"[ContextBuilder] Erro ao buscar contexto '{intencao}': {e}"
            )
            ctx = {}

        # Para CONVERSACAO, injetar KB quando a pergunta for sobre funcionalidade
        if intencao == "CONVERSACAO" and mensagem and cls._e_pergunta_funcionalidade(mensagem):
            try:
                ajuda_ctx = await cls._ctx_ajuda_sistema(db, empresa_id, mensagem)
                doc = ajuda_ctx.get("documentacao_sistema", "")
                if doc:
                    ctx["documentacao_sistema"] = doc
            except Exception as e:
                logger.warning(f"[ContextBuilder] Erro ao injetar KB em CONVERSACAO: {e}")

        # Injetar perfil da empresa/usuário em todas as intenções
        try:
            ctx["perfil"] = await ContextBuilder._ctx_empresa_usuario(
                db, empresa_id, usuario_id
            )
        except Exception as e:
            logger.warning(f"[ContextBuilder] Erro ao buscar perfil: {e}")

        return ctx

    @staticmethod
    async def _ctx_empresa_usuario(
        db: Session, empresa_id: int, usuario_id: int = 0
    ) -> dict:
        """Busca nome da empresa e do usuário logado."""
        from app.models.models import Empresa, Usuario

        empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
        usuario = (
            db.query(Usuario).filter(Usuario.id == usuario_id).first()
            if usuario_id
            else None
        )
        return {
            "empresa_nome": empresa.nome if empresa else "—",
            "usuario_nome": usuario.nome if usuario else "—",
        }

    @staticmethod
    async def _ctx_financeiro(db: Session, empresa_id: int) -> dict:
        """Busca dados financeiros do mês atual + comparativo com mês anterior."""
        from app.services.cotte_ai_hub import _buscar_dados_financeiros
        from app.models.models import ContaFinanceira
        from datetime import date, timedelta
        from sqlalchemy import func as _func

        dados = await _buscar_dados_financeiros(db, empresa_id)

        # Comparativo: receitas do mês anterior
        try:
            hoje = date.today()
            inicio_mes_atual = hoje.replace(day=1)
            fim_mes_anterior = inicio_mes_atual - timedelta(days=1)
            inicio_mes_anterior = fim_mes_anterior.replace(day=1)

            receitas_anterior = (
                db.query(_func.sum(ContaFinanceira.valor_pago))
                .filter(
                    ContaFinanceira.empresa_id == empresa_id,
                    ContaFinanceira.tipo == "receber",
                    ContaFinanceira.pago_em >= inicio_mes_anterior,
                    ContaFinanceira.pago_em <= fim_mes_anterior,
                    ContaFinanceira.excluido_em.is_(None),
                )
                .scalar()
                or 0
            )

            receitas_atual = (dados.get("totais") or {}).get("receitas", 0)
            variacao = None
            if receitas_anterior > 0:
                variacao = round(
                    (receitas_atual - receitas_anterior) / receitas_anterior * 100, 1
                )

            dados["comparativo_mes_anterior"] = {
                "mes": fim_mes_anterior.strftime("%B/%Y"),
                "receitas": float(receitas_anterior),
                "variacao_receitas_pct": variacao,
            }
        except Exception as e:
            logger.warning(f"[ContextBuilder] Erro comparativo mensal: {e}")

        return dados

    @staticmethod
    async def _ctx_orcamentos(db: Session, empresa_id: int) -> dict:
        """Busca últimos 10 orçamentos com resumo por status."""
        from app.models.models import Orcamento, Cliente

        rows = (
            db.query(
                Orcamento.numero,
                Orcamento.status,
                Orcamento.total,
                Orcamento.criado_em,
                Cliente.nome.label("cliente_nome"),
            )
            .join(Cliente, Orcamento.cliente_id == Cliente.id)
            .filter(Orcamento.empresa_id == empresa_id)
            .order_by(desc(Orcamento.criado_em))
            .limit(10)
            .all()
        )

        orcamentos = [
            {
                "numero": r.numero,
                "status": r.status.value
                if hasattr(r.status, "value")
                else str(r.status),
                "total": float(r.total or 0),
                "criado_em": str(r.criado_em.date()) if r.criado_em else None,
                "cliente": r.cliente_nome,
            }
            for r in rows
        ]

        counts = (
            db.query(
                Orcamento.status,
                func.count(Orcamento.id).label("quantidade"),
                func.coalesce(func.avg(Orcamento.total), 0).label("ticket_medio"),
            )
            .filter(Orcamento.empresa_id == empresa_id)
            .group_by(Orcamento.status)
            .all()
        )

        por_status = {
            (c.status.value if hasattr(c.status, "value") else str(c.status)): {
                "quantidade": c.quantidade,
                "ticket_medio": round(float(c.ticket_medio), 2),
            }
            for c in counts
        }

        # Orçamentos pendentes de ação (rascunho ou enviado)
        from datetime import date as _date
        from app.models.models import StatusOrcamento

        pendentes_rows = (
            db.query(
                Orcamento.id,
                Orcamento.numero,
                Orcamento.total,
                Orcamento.criado_em,
                Cliente.nome.label("cliente_nome"),
                Orcamento.status,
            )
            .join(Cliente, Orcamento.cliente_id == Cliente.id)
            .filter(
                Orcamento.empresa_id == empresa_id,
                Orcamento.status.in_(
                    [StatusOrcamento.RASCUNHO, StatusOrcamento.ENVIADO]
                ),
            )
            .order_by(Orcamento.criado_em.asc())
            .limit(5)
            .all()
        )
        hoje = _date.today()
        pendentes = [
            {
                "id": p.id,
                "numero": p.numero,
                "cliente": p.cliente_nome,
                "total": float(p.total or 0),
                "status": p.status.value
                if hasattr(p.status, "value")
                else str(p.status),
                "dias_aguardando": (hoje - p.criado_em.date()).days
                if p.criado_em
                else 0,
            }
            for p in pendentes_rows
        ]

        return {
            "orcamentos_recentes": orcamentos,
            "resumo_por_status": por_status,
            "pendentes_acao": pendentes,
        }

    @staticmethod
    async def _ctx_clientes(db: Session, empresa_id: int) -> dict:
        """Busca total de clientes e os 5 mais recentes."""
        from app.models.models import Cliente

        total = (
            db.query(func.count(Cliente.id))
            .filter(Cliente.empresa_id == empresa_id)
            .scalar()
        ) or 0

        recentes = (
            db.query(Cliente.nome, Cliente.cidade, Cliente.criado_em)
            .filter(Cliente.empresa_id == empresa_id)
            .order_by(desc(Cliente.criado_em))
            .limit(5)
            .all()
        )

        return {
            "total_clientes": total,
            "clientes_recentes": [
                {
                    "nome": r.nome,
                    "cidade": r.cidade,
                    "criado_em": str(r.criado_em.date()) if r.criado_em else None,
                }
                for r in recentes
            ],
        }

    @staticmethod
    async def _ctx_leads(db: Session, empresa_id: int) -> dict:
        """Busca resumo do funil comercial (leads por status)."""
        from app.models.models import CommercialLead

        por_status = (
            db.query(
                CommercialLead.status_pipeline,
                func.count(CommercialLead.id).label("quantidade"),
            )
            .filter(
                CommercialLead.empresa_id == empresa_id,
                CommercialLead.ativo == True,
            )
            .group_by(CommercialLead.status_pipeline)
            .all()
        )

        total = sum(r.quantidade for r in por_status)

        return {
            "total_leads_ativos": total,
            "funil": {r.status_pipeline: r.quantidade for r in por_status},
        }

    # Mapeamento de keywords para seções da knowledge base
    _SECAO_KEYWORDS = {
        "ORCAMENTOS": [
            "orçamento", "orcamento", "orc", "proposta", "criar orc", "enviar orc",
            "aprovar", "duplicar", "clonar", "copiar orc", "rascunho", "enviado",
            "aprovado", "recusado", "linha do tempo", "historico orc", "anexar doc",
            "novo orc", "pdf orc", "gerar pdf", "desconto", "dar desconto",
            "enviar por email", "enviar por whatsapp", "link público", "link cliente",
            "valor orçamento", "status orc", "exportar orc", "filtrar orc",
        ],
        "CLIENTES": [
            "cliente", "cadastrar cliente", "editar cliente", "buscar cliente",
            "exportar clientes", "csv clientes", "novo cliente", "adicionar cliente",
        ],
        "FINANCEIRO": [
            "financeiro", "caixa", "pagar", "receber", "despesa", "parcela",
            "parcelar", "parcelamento", "fluxo", "fluxo de caixa", "conta",
            "saldo", "pagamento", "recebimento", "vencimento", "categoria financeira",
            "a receber", "a pagar", "boleto", "custo", "gasto", "fatura",
            "cobrar", "cobrança", "marcar pago", "registrar pagamento",
        ],
        "CATALOGO": [
            "catálogo", "catalogo", "serviço", "servico", "preço", "preco",
            "produto", "importar serviço", "csv serviço", "tabela de preços",
            "novo serviço", "item catálogo", "desativar serviço", "editar serviço",
        ],
        "COMERCIAL": [
            "comercial", "lead", "pipeline", "crm", "funil", "interação",
            "interacao", "follow-up", "oportunidade", "template mensagem",
            "campanha", "mensagem em lote", "disparar mensagem", "bulk",
            "lembrete lead", "prospect",
        ],
        "DOCUMENTOS": [
            "documento", "contrato", "termo", "garantia", "pdf",
            "biblioteca", "upload", "anexo", "vincular documento",
        ],
        "WHATSAPP": [
            "whatsapp", "whats", "qr code", "qrcode", "bot", "conectar",
            "vincular whatsapp", "número", "numero", "mensagem automática",
            "bot automático", "resposta automática", "desconectar whatsapp",
        ],
        "AGENDAMENTOS": [
            "agendamento", "agendar", "agenda", "remarcar", "cancelar agendamento",
            "confirmar agendamento", "slot", "horário disponível", "visita",
            "serviço agendado", "data do serviço",
        ],
        "RELATORIOS": [
            "relatório", "relatorio", "indicadores", "métricas", "kpis",
            "taxa de aprovação", "ticket médio", "desempenho", "resultados",
            "exportar relatório",
        ],
        "CONFIGURACOES": [
            "configuração", "configuracao", "configurar", "forma de pagamento",
            "usuário", "usuario", "equipe", "permissão", "permissao",
            "gestor", "operador", "texto do cliente", "comunicação", "comunicacao",
            "categoria de despesa", "logo", "logotipo", "dados empresa", "upload logo",
        ],
        "ASSISTENTE_IA": [
            "assistente", "chat", "ia", "inteligência artificial", "criar pelo chat",
        ],
        "FUNCIONALIDADES_INEXISTENTES": [
            "nota fiscal", "nfs-e", "nfse", "erp", "assinatura digital",
            "app mobile", "importar leads csv", "múltiplas empresas",
        ],
    }

    # Prefixos que indicam pergunta sobre funcionalidade (trigger para carregar KB)
    _PREFIXOS_FUNCIONALIDADE = [
        "tem como", "dá pra", "da pra", "é possível", "e possivel",
        "consigo", "como faço", "como faz", "como posso", "posso",
        "como funciona", "onde fica", "onde eu", "como configurar",
        "como usar", "como criar", "como enviar", "como ver",
        "tem ", "existe ", "há como", "ha como", "como adicionar",
        "como fazer", "tem opção", "tem função", "tem feature",
    ]

    @classmethod
    def _carregar_kb(cls) -> dict[str, str]:
        """Carrega e parseia a knowledge_base.md — singleton, lê uma vez."""
        if cls._kb_cache is not None:
            return cls._kb_cache

        kb_path = os.path.join(os.path.dirname(__file__), "prompts", "knowledge_base.md")
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                conteudo = f.read()

            secoes: dict[str, str] = {}
            secao_atual = None
            linhas_atual: list[str] = []
            for linha in conteudo.splitlines():
                if linha.startswith("## Módulo:"):
                    if secao_atual:
                        secoes[secao_atual] = "\n".join(linhas_atual).strip()
                    secao_atual = linha.replace("## Módulo:", "").strip()
                    linhas_atual = []
                else:
                    linhas_atual.append(linha)
            if secao_atual:
                secoes[secao_atual] = "\n".join(linhas_atual).strip()

            cls._kb_cache = secoes
            cls._kb_resumo = (
                "Módulos disponíveis: Orçamentos, Clientes, Financeiro, Catálogo, "
                "Comercial (CRM/leads/campanhas), Documentos, WhatsApp (bot), "
                "Agendamentos, Relatórios, Configurações, Assistente IA."
            )
            logger.info(f"[ContextBuilder] KB carregada: {len(secoes)} módulos")
        except Exception as e:
            logger.warning(f"[ContextBuilder] Erro ao carregar knowledge_base.md: {e}")
            cls._kb_cache = {}

        return cls._kb_cache

    @classmethod
    def _detectar_secao(cls, mensagem: str) -> list[str]:
        """
        Detecta quais seções da KB são relevantes para a pergunta.
        Usa scoring: conta keywords encontradas por seção, retorna top 3.
        """
        msg = mensagem.lower()
        scores: dict[str, int] = {}
        for secao, keywords in cls._SECAO_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in msg)
            if score > 0:
                scores[secao] = score
        # Top 3 seções com maior pontuação
        return sorted(scores, key=lambda s: scores[s], reverse=True)[:3]

    @classmethod
    def _e_pergunta_funcionalidade(cls, mensagem: str) -> bool:
        """Detecta se a mensagem é sobre 'como usar / se existe' alguma funcionalidade."""
        msg = mensagem.lower()
        return any(pref in msg for pref in cls._PREFIXOS_FUNCIONALIDADE)

    @classmethod
    async def _ctx_ajuda_sistema(
        cls, db: Session, empresa_id: int, mensagem: str = ""
    ) -> dict:
        """Carrega apenas a seção relevante da KB para a pergunta (intenção AJUDA_SISTEMA)."""
        secoes = cls._carregar_kb()
        if not secoes:
            return {"documentacao_sistema": ""}

        relevantes = cls._detectar_secao(mensagem) if mensagem else []

        if relevantes:
            partes = [secoes[s] for s in relevantes if s in secoes]
            doc = "\n\n---\n\n".join(partes)
        else:
            # Fallback: resumo executivo dos módulos disponíveis
            doc = cls._kb_resumo or "\n\n".join(secoes.values())

        return {"documentacao_sistema": doc}

    @classmethod
    async def _ctx_geral_com_ajuda(cls, db: Session, empresa_id: int) -> dict:
        """
        Contexto geral (dados) + KB injetada se a mensagem indica pergunta sobre funcionalidade.
        Usado por CONVERSACAO — a mensagem não está disponível aqui, então a injeção da KB
        é feita condicionalmente em build() via mensagem.
        """
        return await cls._ctx_geral(db, empresa_id)

    @classmethod
    async def _ctx_geral(cls, db: Session, empresa_id: int) -> dict:
        """Combinação compacta: financeiro (totais + comparativo) + orçamentos + clientes + leads."""
        ctx = {}

        try:
            fin = await ContextBuilder._ctx_financeiro(db, empresa_id)
            ctx["financeiro"] = {
                "saldo_atual": fin.get("saldo", {}).get("atual", 0),
                "total_receitas_mes": fin.get("totais", {}).get("receitas", 0),
                "total_despesas_mes": fin.get("totais", {}).get("despesas", 0),
                "periodo": fin.get("periodo", "mes_atual"),
                "comparativo_mes_anterior": fin.get("comparativo_mes_anterior"),
            }
        except Exception:
            pass

        try:
            orc_ctx = await ContextBuilder._ctx_orcamentos(db, empresa_id)
            ctx["orcamentos"] = orc_ctx
        except Exception:
            pass

        try:
            ctx["clientes"] = await ContextBuilder._ctx_clientes(db, empresa_id)
        except Exception:
            pass

        try:
            ctx["leads"] = await ContextBuilder._ctx_leads(db, empresa_id)
        except Exception:
            pass

        try:
            ctx["agendamentos"] = await ContextBuilder._ctx_agendamentos(db, empresa_id)
        except Exception:
            pass

        return ctx

    @staticmethod
    async def _ctx_agendamentos(db: "Session", empresa_id: int) -> dict:
        """Busca contexto de agendamentos para o assistente."""
        from app.models.models import Agendamento, StatusAgendamento
        from datetime import date, time as dtime, timedelta

        hoje = date.today()
        inicio_hoje = datetime.combine(hoje, dtime.min).replace(tzinfo=timezone.utc)
        fim_hoje = datetime.combine(hoje, dtime.max).replace(tzinfo=timezone.utc)
        fim_7d = datetime.combine(hoje + timedelta(days=7), dtime.max).replace(tzinfo=timezone.utc)

        # Agendamentos de hoje
        ag_hoje = (
            db.query(Agendamento)
            .filter(
                Agendamento.empresa_id == empresa_id,
                Agendamento.data_agendada >= inicio_hoje,
                Agendamento.data_agendada <= fim_hoje,
                Agendamento.status.notin_([
                    StatusAgendamento.CANCELADO,
                    StatusAgendamento.NAO_COMPARECEU,
                ]),
            )
            .order_by(Agendamento.data_agendada.asc())
            .limit(10)
            .all()
        )

        # Pendentes de confirmação
        pendentes = (
            db.query(Agendamento)
            .filter(
                Agendamento.empresa_id == empresa_id,
                Agendamento.status == StatusAgendamento.PENDENTE,
            )
            .count()
        )

        # Próximos 7 dias
        proximos = (
            db.query(Agendamento)
            .filter(
                Agendamento.empresa_id == empresa_id,
                Agendamento.data_agendada > fim_hoje,
                Agendamento.data_agendada <= fim_7d,
                Agendamento.status.notin_([
                    StatusAgendamento.CANCELADO,
                    StatusAgendamento.NAO_COMPARECEU,
                ]),
            )
            .count()
        )

        return {
            "hoje": [
                {
                    "numero": a.numero,
                    "cliente": a.cliente.nome if a.cliente else "—",
                    "hora": a.data_agendada.strftime("%H:%M") if a.data_agendada else "—",
                    "status": a.status.value if a.status else "—",
                    "responsavel": a.responsavel.nome if a.responsavel else "—",
                }
                for a in ag_hoje
            ],
            "total_hoje": len(ag_hoje),
            "pendentes_confirmacao": pendentes,
            "proximos_7_dias": proximos,
        }
