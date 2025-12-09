"""
Optimus Project Orchestration Service

This package provides comprehensive project lifecycle management including:
- Project launching and process management
- Environment switching and configuration
- Resource allocation and monitoring  
- Deployment automation and rollback
- Backup coordination and recovery

The orchestrator is the central control system for managing all project operations
in the Optimus ecosystem.
"""

from .project_launcher import ProjectLauncher
from .environment_manager import EnvironmentManager
from .resource_allocator import ResourceAllocator
from .deployment_assistant import DeploymentAssistant
from .backup_coordinator import BackupCoordinator

__all__ = [
    "ProjectLauncher",
    "EnvironmentManager", 
    "ResourceAllocator",
    "DeploymentAssistant",
    "BackupCoordinator"
]