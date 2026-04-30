"""Compositor de respostas finais para a interface do Copiloto."""

from __future__ import annotations

from typing import Any

from app.services.internal_copilot_memory import SessionWorkingMemory
from app.services.internal_copilot_artifacts import LiveArtifact


class ResponseComposer:
    """
    Formata o estado final de SessionWorkingMemory e LiveArtifact
    num dicionario compativel com o frontend do copiloto.
    O frontend espera principalmente `resposta` ou `summary` (que sao renderizados como markdown),
    alem de `table`, `chart`, `actions`, etc.
    """

    @staticmethod
    def compose(
        memory: SessionWorkingMemory | dict[str, Any],
        artifact: LiveArtifact | dict[str, Any]
    ) -> dict[str, Any]:
        """
        Gera o payload final de resposta com base na memoria e artefato atuais.
        """
        # Normaliza parametros
        if isinstance(memory, dict):
            # Fallback pra evitar excecao se faltarem campos obrigatorios:
            # SessionWorkingMemory model_validate default ja ignora extras.
            try:
                mem_obj = SessionWorkingMemory.model_validate(memory)
            except Exception:
                mem_obj = SessionWorkingMemory()
        else:
            mem_obj = memory

        if isinstance(artifact, dict):
            try:
                art_obj = LiveArtifact.model_validate(artifact)
            except Exception:
                art_obj = LiveArtifact()
        else:
            art_obj = artifact

        # Constroi a resposta em markdown
        linhas_resposta = []
        
        if art_obj.summary:
            linhas_resposta.append(art_obj.summary)
        
        if art_obj.insights:
            if linhas_resposta:
                linhas_resposta.append("")
            linhas_resposta.append("**Insights:**")
            for insight in art_obj.insights:
                linhas_resposta.append(f"- {insight}")

        # Se nao houver summary nem insights no artefato, tenta usar dados da memoria
        if not linhas_resposta and mem_obj.objetivo_ativo:
            linhas_resposta.append(f"Objetivo atual: {mem_obj.objetivo_ativo}")
            if mem_obj.ultimo_resultado_relevante:
                linhas_resposta.append("Tenho os dados processados e prontos para visualização.")

        # Se ainda vazio, mensagem padrao
        if not linhas_resposta:
            linhas_resposta.append("Operação concluída.")

        resposta_markdown = "\n".join(linhas_resposta)

        # Prepara a saida compatível com a UI do hub (cotte_ai_hub) ou frontend
        payload = {
            "resposta": resposta_markdown,
            "mensagem": resposta_markdown, # redundancia para sistemas mais antigos
            "summary": art_obj.summary or resposta_markdown,
            "actions": art_obj.suggested_actions or mem_obj.proximos_passos_sugeridos or [],
        }

        # Anexa tabela se houver
        if art_obj.table:
            payload["table"] = art_obj.table
            payload["sql_result"] = art_obj.table # Alias para alguns renders de UI

        # Anexa chart se houver
        if art_obj.chart:
            payload["chart"] = art_obj.chart

        # Se tiver pending confirmation, podemos retornar como um form ou flag especial?
        # A instrucao so cita: `actions`, `form` e os acima.
        if mem_obj.pendencia_confirmacao:
            # converte em action ou em form
            # Aqui um mock simples de form
            payload["form"] = mem_obj.pendencia_confirmacao

        # Retorna o dict sem as chaves vazias ou com [] opcionalmente, 
        # mas por hora vamos limpar campos nulos para não sujar o payload desnecessariamente.
        return {k: v for k, v in payload.items() if v}
