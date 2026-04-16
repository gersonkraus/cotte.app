import sys
from app.services.assistant_autonomy.semantic_model import build_semantic_system_prompt
from app.services.assistant_autonomy.capability_layer import gather_capabilities

caps = gather_capabilities(1, False)
print(caps)
