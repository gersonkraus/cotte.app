import re

with open("sistema/app/services/internal_copilot_data_executor.py", "r") as f:
    content = f.read()

# We need to change InternalCopilotDataExecutor.execute to catch exceptions and handle handled=False
old_code = """        semantic_payload = await try_handle_semantic_autonomy(
            mensagem=semantic_message,
            sessao_id=sessao_id,
            db=db,
            current_user=current_user,
            engine=ENGINE_ANALYTICS,
            request_id=request_id,
            confirmation_token=None,
            override_args=override_args,
        )
        if not isinstance(semantic_payload, dict):
            return SemanticDataExecutionResult(
                executed=False,
                used_engine=ENGINE_ANALYTICS,
                semantic_message=semantic_message,
                skip_reason="semantic_runtime_unavailable",
            )

        return SemanticDataExecutionResult(
            executed=True,
            used_engine=ENGINE_ANALYTICS,
            semantic_message=semantic_message,
            semantic_payload=semantic_payload,
            artifact_patch=_build_artifact_patch(agent_run, semantic_payload),
        )"""

new_code = """        try:
            semantic_payload = await try_handle_semantic_autonomy(
                mensagem=semantic_message,
                sessao_id=sessao_id,
                db=db,
                current_user=current_user,
                engine=ENGINE_ANALYTICS,
                request_id=request_id,
                confirmation_token=None,
                override_args=override_args,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[DataExecutor] Falha na autonomia semântica analítica: {e}")
            semantic_payload = None

        if not isinstance(semantic_payload, dict) or semantic_payload.get("handled") is False:
            return SemanticDataExecutionResult(
                executed=False,
                used_engine=ENGINE_ANALYTICS,
                semantic_message=semantic_message,
                skip_reason="semantic_runtime_unavailable" if not semantic_payload else "handled_false",
                artifact_patch=None
            )

        return SemanticDataExecutionResult(
            executed=True,
            used_engine=ENGINE_ANALYTICS,
            semantic_message=semantic_message,
            semantic_payload=semantic_payload,
            artifact_patch=_build_artifact_patch(agent_run, semantic_payload),
        )"""

content = content.replace(old_code, new_code)

with open("sistema/app/services/internal_copilot_data_executor.py", "w") as f:
    f.write(content)
