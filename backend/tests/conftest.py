"""Make backend package and root-level provider imports deterministic in tests."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_DIR.parent

for import_path in (REPOSITORY_ROOT, BACKEND_DIR):
    resolved = str(import_path)
    if resolved in sys.path:
        sys.path.remove(resolved)
    sys.path.insert(0, resolved)
