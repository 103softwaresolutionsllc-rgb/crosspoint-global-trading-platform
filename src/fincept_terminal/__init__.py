"""
Fincept Terminal - State-of-the-art financial intelligence platform
with CFA-level analytics, AI automation, and unlimited data connectivity.
"""

__version__ = "4.0.2"
__author__ = "Fincept Corporation"
__email__ = "support@fincept.in"

from .analytics.dcf import DCFModel
from .analytics.portfolio import PortfolioOptimizer
from .analytics.risk import RiskMetrics
from .agents.base import BaseAgent

__all__ = [
    "DCFModel",
    "PortfolioOptimizer", 
    "RiskMetrics",
    "BaseAgent",
]
