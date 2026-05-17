"""Specialized agent for casual conversation."""
from __future__ import annotations

from typing import List, Dict, Any
from app.ai.agents.base import BaseAgent

class ConversationalAgent(BaseAgent):
    """Agent for small talk and greetings."""
    def __init__(self, model_override: str | None = None):
        system_prompt = (
            "Você é a IA do Sistema COTTE. Você é prestativo, educado e focado em ajudar o usuário "
            "a gerir sua empresa de forma eficiente.\n\n"
            "DIRETRIZES:\n"
            "1. Responda a saudações de forma calorosa.\n"
            "2. Se o usuário estiver apenas conversando, mantenha o tom profissional mas amigável.\n"
            "3. Sempre que possível, lembre o usuário de que você pode ajudá-lo com orçamentos, "
            "financeiro e catálogo."
        )
        
        super().__init__(
            name="ConversationalAgent",
            system_prompt=system_prompt,
            model_override=model_override
        )
