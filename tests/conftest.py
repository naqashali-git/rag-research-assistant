"""
Pytest configuration and fixtures.

Ensures rag_assistant package can be imported from tests.
"""

import sys
import os
from pathlib import Path

# Add the repository root to Python path so tests can import rag_assistant
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

# Also set PYTHONPATH environment variable
os.environ['PYTHONPATH'] = str(repo_root)