"""
Main entry point for Fincept Terminal
"""

import sys
import os

# Add src to path for imports
_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO = os.path.dirname(_SRC)
sys.path.insert(0, _SRC)
os.chdir(_REPO)

from global_trading.settings import load_settings

load_settings()

from fincept_terminal.main import main

if __name__ == "__main__":
    sys.exit(main())
