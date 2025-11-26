"""
Optimus Council of Minds - Multi-Persona Intelligence System

A blackboard-based architecture where 15 specialized personas collaborate
to make intelligent decisions through weighted consensus.
"""

from .blackboard import Blackboard, BlackboardEntry
from .persona import Persona, PersonaResponse
from .consensus import ConsensusEngine
from .orchestrator import Orchestrator
from .personas import (
    StrategistPersona,
    PragmatistPersona,
    InnovatorPersona,
    GuardianPersona,
    AnalystPersona
)

__all__ = [
    'Blackboard',
    'BlackboardEntry',
    'Persona',
    'PersonaResponse',
    'ConsensusEngine',
    'Orchestrator',
    'StrategistPersona',
    'PragmatistPersona',
    'InnovatorPersona',
    'GuardianPersona',
    'AnalystPersona'
]