import re

with open("sistema/app/services/internal_copilot_data_executor.py", "r") as f:
    content = f.read()

# Replace inline logging
old_inline = """        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[DataExecutor] Falha na autonomia semântica analítica: {e}")
            semantic_payload = None"""

new_inline = """        except Exception as e:
            logger.warning(f"[DataExecutor] Falha na autonomia semântica analítica: {e}")
            semantic_payload = None"""

content = content.replace(old_inline, new_inline)

# Add import logging at the top after typing
old_import = """from typing import Any

from pydantic import BaseModel"""

new_import = """import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)"""

content = content.replace(old_import, new_import)

with open("sistema/app/services/internal_copilot_data_executor.py", "w") as f:
    f.write(content)
