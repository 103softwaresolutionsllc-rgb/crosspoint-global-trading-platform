"""
AI Agents Module for Fincept Terminal
37 agents across Trader/Investor, Economic, and Geopolitics frameworks
"""

from .base import BaseAgent, AgentResult
from .value_investors.buffett import BuffettAgent
from .value_investors.graham import GrahamAgent
from .value_investors.lynch import LynchAgent
from .value_investors.dunlap import IanDunlapAgent

__all__ = [
    "BaseAgent",
    "AgentResult",
    "BuffettAgent",
    "GrahamAgent", 
    "LynchAgent",
    "IanDunlapAgent",
]
