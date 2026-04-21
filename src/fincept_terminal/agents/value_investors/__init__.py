"""
Value Investors Module for Fincept Terminal
AI agents based on famous value investing principles
"""

from .buffett import BuffettAgent
from .graham import GrahamAgent
from .lynch import LynchAgent
from .dunlap import IanDunlapAgent

__all__ = [
    "BuffettAgent",
    "GrahamAgent", 
    "LynchAgent",
    "IanDunlapAgent",
]
