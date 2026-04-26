"""
In-memory store.
Swap this module for a SQLAlchemy/Redis layer later without touching route logic.
"""
from typing import Dict
from app.models.monitor import Monitor

# In-memory store for monitors
monitors: Dict[str, Monitor] = {}
