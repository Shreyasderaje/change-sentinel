import sys
from pathlib import Path

# Make sure the project root is importable when pytest is invoked from
# any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
