"""Make backend package and root-level provider imports deterministic in tests."""

import os
import sys
from pathlib import Path

# Establish the test configuration before any test module can import the app.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ENVIRONMENT"] = "development"
os.environ["JWT_SECRET"] = "test-only-jwt-secret-for-isolated-backend-suite-2026"
os.environ["SARVAM_API_KEY"] = "test-only-dummy-sarvam-key"

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_DIR.parent

for import_path in (REPOSITORY_ROOT, BACKEND_DIR):
    resolved = str(import_path)
    if resolved in sys.path:
        sys.path.remove(resolved)
    sys.path.insert(0, resolved)
