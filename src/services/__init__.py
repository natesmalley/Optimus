"""
Services module for Optimus backend.
Contains business logic and external integrations.
"""

from .scanner import ProjectScanner
from .monitor import RuntimeMonitor

# Optional imports that may fail
try:
    from .troubleshooting_engine import TroubleshootingEngine
except ImportError:
    TroubleshootingEngine = None
    
try:
    from .solution_library import SolutionLibrary
except ImportError:
    SolutionLibrary = None
    
try:
    from .auto_fixer import AutoFixer
except ImportError:
    AutoFixer = None
    
try:
    from .solution_search import SolutionSearchService
except ImportError:
    SolutionSearchService = None
    
try:
    from .troubleshooting_integration import TroubleshootingIntegrationService
except ImportError:
    TroubleshootingIntegrationService = None

__all__ = [
    "ProjectScanner",
    "RuntimeMonitor",
    "TroubleshootingEngine",
    "SolutionLibrary", 
    "AutoFixer",
    "SolutionSearchService",
    "TroubleshootingIntegrationService",
]