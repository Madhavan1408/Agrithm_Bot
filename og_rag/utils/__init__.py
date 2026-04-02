"""
utils/__init__.py
─────────────────
Adds project root (rag/) to sys.path so all utils
can import agrithm_config without path hacks.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))