"""
pytest configuration — TruthLens AI/ML Service
Ensures the ai-ml/ directory root is on sys.path so all imports resolve.
"""

import sys
from pathlib import Path

# Add the ai-ml/ root directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
