"""Base classes for AI Agents."""
from __future__ import annotations

import logging
from typing import Any, List, Optional, Protocol, Dict
from pydantic import BaseModel, Field

from app.ai.service import ia_service

logger = logging.getLogger(__name__)

class AgentResponse(BaseModel):
    """Standardized response from an agent."""
    content: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=list)

class Agent(Protocol):
    """Protocol for AI Agents."""
    name: str
    system_prompt: str
    
    async def __call__(self, messages: List[Dict[str, str]], **kwargs) -> AgentResponse:
        ...

class BaseAgent:
    """Base implementation for Agents using LiteLLM."""
    def __init__(
        self, 
        name: str, 
        system_prompt: str, 
        tools: Optional[List[Dict[str, Any]]] = None,
        model_override: Optional[str] = None
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self.model_override = model_override

    async def __call__(self, messages: List[Dict[str, str]], **kwargs) -> AgentResponse:
        """Executes the agent loop."""
        logger.info(f"Agent {self.name} called with {len(messages)} messages.")
        
        # Prepare messages with system prompt
        all_messages = [{"role": "system", "content": self.system_prompt}] + messages
        
        # Call LLM
        response = await ia_service.chat(
            messages=all_messages,
            tools=self.tools,
            model_override=self.model_override,
            **kwargs
        )
        
        # Parse response
        choices = response.get("choices", [])
        if not choices:
            return AgentResponse(content="Sem resposta do agente.", metadata=response)
        
        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content") or ""
        tool_calls = message.get("tool_calls") or []
        
        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            metadata=response
        )
