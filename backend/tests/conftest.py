from __future__ import annotations

import sys
from pathlib import Path


# Ensure `import app...` works when running pytest from backend/
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
