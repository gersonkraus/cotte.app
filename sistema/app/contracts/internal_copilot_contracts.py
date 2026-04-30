from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class LiveArtifact:
    should_render_artifact: bool = False
    chart: Optional[Dict[str, Any]] = None
    table: Optional[List[Dict[str, Any]]] = None
    form: Optional[Dict[str, Any]] = None

@dataclass
class SessionWorkingMemory:
    route: str = "technical"  # "technical", "analytics", etc.
    context_sections: Dict[str, str] = field(default_factory=dict)
    actions: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class InternalTechnicalFlowPayload:
    resposta: str
    chart: Optional[Dict[str, Any]] = None
    table: Optional[List[Dict[str, Any]]] = None
    form: Optional[Dict[str, Any]] = None
    actions: List[Any] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    trace: List[Dict[str, Any]] = field(default_factory=list)
    
@dataclass
class InternalResultEnvelope:
    success: bool
    flow_id: str
    payload: InternalTechnicalFlowPayload
    metrics: Dict[str, Any] = field(default_factory=dict)
