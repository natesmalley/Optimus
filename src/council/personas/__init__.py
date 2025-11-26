"""
The Council of Minds - Optimus Personas

Core technical personas and life-aspect personas that form the foundation 
of multi-perspective intelligence for both technical and life decisions.
"""

# Technical Personas (Core)
from .strategist import StrategistPersona
from .pragmatist import PragmatistPersona
from .innovator import InnovatorPersona
from .guardian import GuardianPersona
from .analyst import AnalystPersona

# Life-Aspect Personas
from .philosopher import PhilosopherPersona
from .healer import HealerPersona
from .socialite import SocialitePersona
from .economist import EconomistPersona
from .creator import CreatorPersona
from .scholar import ScholarPersona
from .explorer import ExplorerPersona
from .mentor import MentorPersona

# Core technical personas always active
CORE_PERSONAS = [
    StrategistPersona,
    PragmatistPersona,
    InnovatorPersona,
    GuardianPersona,
    AnalystPersona
]

# Life-aspect personas for holistic decision making
LIFE_PERSONAS = [
    PhilosopherPersona,
    HealerPersona,
    SocialitePersona,
    EconomistPersona,
    CreatorPersona,
    ScholarPersona,
    ExplorerPersona,
    MentorPersona
]

# All personas combined
ALL_PERSONAS = CORE_PERSONAS + LIFE_PERSONAS

__all__ = [
    # Technical personas
    'StrategistPersona',
    'PragmatistPersona', 
    'InnovatorPersona',
    'GuardianPersona',
    'AnalystPersona',
    # Life-aspect personas
    'PhilosopherPersona',
    'HealerPersona',
    'SocialitePersona',
    'EconomistPersona',
    'CreatorPersona',
    'ScholarPersona',
    'ExplorerPersona',
    'MentorPersona',
    # Collections
    'CORE_PERSONAS',
    'LIFE_PERSONAS',
    'ALL_PERSONAS'
]