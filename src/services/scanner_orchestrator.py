"""
Scanner Orchestrator Service
============================

Orchestrates and coordinates all scanning activities across the Optimus system.
Features include:

- Centralized scanning workflow management
- Parallel execution of scanner components
- Progress tracking and status reporting
- Incremental scanning for efficiency
- Integration with knowledge graph and memory systems
- Council of Minds integration for intelligent analysis
- Automatic scheduling and periodic rescans
- Error handling and retry mechanisms
- Performance optimization and resource management

Components coordinated:
- Enhanced project scanner
- Runtime monitor
- Project analyzer
- Knowledge graph integration
- Memory system integration
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from ..config import get_settings
from ..models import Project
from ..council.memory_integration import MemoryIntegration
from ..council.knowledge_graph_integration import KnowledgeGraphIntegration
from ..council.orchestrator import CouncilOrchestrator

from .enhanced_scanner import EnhancedProjectScanner, ProjectAnalysis, ScanMetrics
from .runtime_monitor import RuntimeMonitor
from .project_analyzer import ProjectAnalyzer, ProjectAnalysisResult


logger = logging.getLogger("optimus.scanner_orchestrator")


class ScanType(Enum):
    """Types of scans that can be performed."""
    FULL = "full"              # Complete scan of all components
    INCREMENTAL = "incremental"  # Only scan changed projects
    RUNTIME_ONLY = "runtime"    # Only runtime monitoring
    ANALYSIS_ONLY = "analysis"  # Only code analysis
    DISCOVERY_ONLY = "discovery"  # Only project discovery


class ScanStatus(Enum):
    """Status of scan operations."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScanJob:
    """Represents a scanning job with its configuration and status."""
    id: str
    scan_type: ScanType
    status: ScanStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    total_projects: int = 0
    processed_projects: int = 0
    errors: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    project_filter: Optional[List[str]] = None  # Specific projects to scan
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorMetrics:
    """Performance metrics for the orchestrator."""
    total_scans: int = 0
    successful_scans: int = 0
    failed_scans: int = 0
    average_scan_time: float = 0.0
    projects_discovered: int = 0
    vulnerabilities_found: int = 0
    quality_issues_found: int = 0
    active_projects: int = 0
    last_full_scan: Optional[datetime] = None


class ScannerOrchestrator:
    """Orchestrates all scanning activities for comprehensive project analysis."""
    
    def __init__(self, session: AsyncSession, memory_integration: MemoryIntegration = None,
                 kg_integration: KnowledgeGraphIntegration = None, 
                 council_orchestrator: CouncilOrchestrator = None):
        self.session = session
        self.settings = get_settings()
        self.memory = memory_integration
        self.kg = kg_integration
        self.council = council_orchestrator
        
        # Initialize scanner components
        self.project_scanner = EnhancedProjectScanner(session, memory_integration, kg_integration)
        self.runtime_monitor = RuntimeMonitor(session, memory_integration, kg_integration)
        self.project_analyzer = ProjectAnalyzer(session, memory_integration, kg_integration)
        
        # Job tracking
        self.active_jobs: Dict[str, ScanJob] = {}
        self.job_history: List[ScanJob] = []
        self.metrics = OrchestratorMetrics()
        
        # Configuration
        self.max_concurrent_jobs = 3
        self.max_projects_per_batch = 10
        self.scan_timeout_minutes = 30
        self.incremental_scan_interval = timedelta(hours=1)
        self.full_scan_interval = timedelta(hours=24)
        
        # State tracking
        self.last_incremental_scan = None
        self.last_full_scan = None
        self.project_checksums: Dict[str, str] = {}  # For incremental scanning
        
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
    
    async def initialize(self) -> None:
        """Initialize the orchestrator and all components."""
        logger.info("Initializing Scanner Orchestrator")
        
        try:
            # Initialize runtime monitor
            await self.runtime_monitor.initialize()
            
            # Load existing project data for incremental scanning
            await self._load_project_state()
            
            # Start background monitoring
            await self._start_background_monitoring()
            
            logger.info("Scanner Orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Scanner Orchestrator: {e}", exc_info=True)
            raise
    
    async def _load_project_state(self) -> None:
        """Load existing project state for incremental scanning."""
        try:
            stmt = select(Project).where(Project.status != "inactive")
            result = await self.session.execute(stmt)
            projects = result.scalars().all()
            
            for project in projects:
                if project.path and Path(project.path).exists():
                    checksum = await self._calculate_project_checksum(project.path)
                    self.project_checksums[project.path] = checksum
            
            logger.info(f"Loaded state for {len(self.project_checksums)} projects")
            
        except Exception as e:
            logger.error(f"Error loading project state: {e}")
    
    async def _calculate_project_checksum(self, project_path: str) -> str:
        """Calculate checksum for project to detect changes."""
        try:
            import hashlib
            
            project_dir = Path(project_path)
            hasher = hashlib.md5()
            
            # Include modification times of key files
            key_files = []
            for pattern in ["*.py", "*.js", "*.ts", "package.json", "requirements.txt", "Cargo.toml"]:
                key_files.extend(list(project_dir.glob(pattern)))
                key_files.extend(list(project_dir.glob(f"*/{pattern}")))
            
            # Sort for consistent ordering
            key_files = sorted(set(key_files))[:50]  # Limit to 50 files
            
            for file_path in key_files:
                try:
                    stat = file_path.stat()
                    hasher.update(f"{file_path.name}:{stat.st_mtime}".encode())
                except OSError:
                    continue
            
            return hasher.hexdigest()
            
        except Exception as e:
            logger.debug(f"Error calculating checksum for {project_path}: {e}")
            return "unknown"
    
    async def _start_background_monitoring(self) -> None:
        """Start background monitoring tasks."""
        try:
            # Runtime monitoring task
            runtime_task = asyncio.create_task(
                self.runtime_monitor.continuous_monitoring(interval_seconds=60)
            )
            self._background_tasks.add(runtime_task)
            runtime_task.add_done_callback(self._background_tasks.discard)
            
            # Scheduled scanning task
            scheduler_task = asyncio.create_task(self._scheduled_scanning_loop())
            self._background_tasks.add(scheduler_task)
            scheduler_task.add_done_callback(self._background_tasks.discard)
            
            logger.info("Background monitoring tasks started")
            
        except Exception as e:
            logger.error(f"Error starting background monitoring: {e}")
    
    async def _scheduled_scanning_loop(self) -> None:
        """Main loop for scheduled scanning operations."""
        logger.info("Starting scheduled scanning loop")
        
        try:
            while True:
                now = datetime.now(timezone.utc)
                
                # Check if incremental scan is due
                if (not self.last_incremental_scan or 
                    now - self.last_incremental_scan >= self.incremental_scan_interval):
                    
                    logger.info("Starting scheduled incremental scan")
                    job = await self.start_scan(ScanType.INCREMENTAL, 
                                              config={"scheduled": True, "background": True})
                    self.last_incremental_scan = now
                
                # Check if full scan is due
                elif (not self.last_full_scan or 
                      now - self.last_full_scan >= self.full_scan_interval):
                    
                    logger.info("Starting scheduled full scan")
                    job = await self.start_scan(ScanType.FULL, 
                                              config={"scheduled": True, "background": True})
                    self.last_full_scan = now
                
                # Sleep for 10 minutes before next check
                await asyncio.sleep(600)
        
        except asyncio.CancelledError:
            logger.info("Scheduled scanning loop cancelled")
        except Exception as e:
            logger.error(f"Error in scheduled scanning loop: {e}", exc_info=True)
    
    async def start_scan(self, scan_type: ScanType, 
                        project_filter: Optional[List[str]] = None,
                        config: Optional[Dict[str, Any]] = None) -> str:
        """Start a new scanning job."""
        import uuid
        
        job_id = str(uuid.uuid4())[:8]
        
        job = ScanJob(
            id=job_id,
            scan_type=scan_type,
            status=ScanStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            project_filter=project_filter,
            config=config or {}
        )
        
        self.active_jobs[job_id] = job
        
        logger.info(f"Starting {scan_type.value} scan job {job_id}")
        
        # Start the scan task
        scan_task = asyncio.create_task(self._execute_scan(job))
        scan_task.add_done_callback(lambda t: self._cleanup_job(job_id))
        
        return job_id
    
    async def _execute_scan(self, job: ScanJob) -> None:
        """Execute a scanning job."""
        try:
            job.status = ScanStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            
            logger.info(f"Executing {job.scan_type.value} scan {job.id}")
            
            if job.scan_type == ScanType.FULL:
                await self._execute_full_scan(job)
            elif job.scan_type == ScanType.INCREMENTAL:
                await self._execute_incremental_scan(job)
            elif job.scan_type == ScanType.RUNTIME_ONLY:
                await self._execute_runtime_scan(job)
            elif job.scan_type == ScanType.ANALYSIS_ONLY:
                await self._execute_analysis_scan(job)
            elif job.scan_type == ScanType.DISCOVERY_ONLY:
                await self._execute_discovery_scan(job)
            
            job.status = ScanStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.progress = 100.0
            
            # Update metrics
            self._update_metrics(job, success=True)
            
            # Trigger Council analysis if configured
            if self.council and not job.config.get("background", False):
                await self._trigger_council_analysis(job)
            
            logger.info(f"Scan {job.id} completed successfully")
            
        except asyncio.CancelledError:
            job.status = ScanStatus.CANCELLED
            logger.info(f"Scan {job.id} was cancelled")
        except Exception as e:
            job.status = ScanStatus.FAILED
            job.errors.append(str(e))
            self._update_metrics(job, success=False)
            logger.error(f"Scan {job.id} failed: {e}", exc_info=True)
        finally:
            job.completed_at = job.completed_at or datetime.now(timezone.utc)
    
    async def _execute_full_scan(self, job: ScanJob) -> None:
        """Execute a full comprehensive scan."""
        logger.info(f"Starting full scan {job.id}")
        
        # Phase 1: Project Discovery
        job.progress = 10.0
        logger.info("Phase 1: Project Discovery")
        project_analyses = await self.project_scanner.scan_projects()
        
        job.total_projects = len(project_analyses)
        job.results["discovered_projects"] = job.total_projects
        
        # Phase 2: Save discovered projects
        job.progress = 20.0
        logger.info("Phase 2: Saving discovered projects")
        saved_projects = []
        
        for analysis in project_analyses:
            project_id = await self.project_scanner.save_project_analysis(analysis)
            if project_id:
                saved_projects.append(project_id)
                
                # Update checksum for incremental scanning
                checksum = await self._calculate_project_checksum(analysis.basic_info["path"])
                self.project_checksums[analysis.basic_info["path"]] = checksum
        
        job.results["saved_projects"] = len(saved_projects)
        
        # Phase 3: Detailed Analysis (parallel batches)
        job.progress = 40.0
        logger.info("Phase 3: Detailed project analysis")
        
        analysis_results = []
        for i in range(0, len(saved_projects), self.max_projects_per_batch):
            batch = saved_projects[i:i + self.max_projects_per_batch]
            batch_results = await self._analyze_project_batch(batch)
            analysis_results.extend(batch_results)
            
            job.processed_projects += len(batch)
            job.progress = 40.0 + (job.processed_projects / job.total_projects) * 30.0
        
        job.results["analysis_results"] = len(analysis_results)
        
        # Phase 4: Runtime Monitoring
        job.progress = 80.0
        logger.info("Phase 4: Runtime monitoring")
        await self.runtime_monitor.scan_processes()
        await self.runtime_monitor.scan_services()
        if self.runtime_monitor.docker_client:
            await self.runtime_monitor.scan_containers()
        
        # Phase 5: Knowledge Graph Integration
        job.progress = 90.0
        logger.info("Phase 5: Knowledge graph integration")
        if self.kg:
            await self._integrate_scan_results_with_kg(project_analyses, analysis_results)
        
        # Phase 6: Memory Integration
        job.progress = 95.0
        logger.info("Phase 6: Memory integration")
        if self.memory:
            await self._integrate_scan_results_with_memory(job, project_analyses, analysis_results)
        
        # Compile final results
        job.results.update({
            "scan_type": "full",
            "total_vulnerabilities": sum(len(r.security_issues) for r in analysis_results),
            "total_quality_issues": sum(len(r.quality_issues) for r in analysis_results),
            "average_score": sum(r.overall_score for r in analysis_results) / len(analysis_results) if analysis_results else 0,
            "runtime_processes": len(self.runtime_monitor.known_processes),
            "runtime_services": len(self.runtime_monitor.known_services)
        })
        
        self.metrics.last_full_scan = datetime.now(timezone.utc)
    
    async def _execute_incremental_scan(self, job: ScanJob) -> None:
        """Execute an incremental scan for changed projects only."""
        logger.info(f"Starting incremental scan {job.id}")
        
        # Find changed projects
        changed_projects = await self._find_changed_projects()
        job.total_projects = len(changed_projects)
        job.results["changed_projects"] = job.total_projects
        
        if not changed_projects:
            logger.info("No changed projects found for incremental scan")
            job.progress = 100.0
            return
        
        # Phase 1: Re-scan changed projects
        job.progress = 20.0
        logger.info(f"Phase 1: Re-scanning {len(changed_projects)} changed projects")
        
        analysis_results = []
        for i, project_path in enumerate(changed_projects):
            try:
                # Get project ID
                stmt = select(Project.id).where(Project.path == project_path)
                result = await self.session.execute(stmt)
                project_id = result.scalar_one_or_none()
                
                if project_id:
                    # Analyze the project
                    analysis = await self.project_analyzer.analyze_project(project_path, str(project_id))
                    analysis_results.append(analysis)
                    
                    # Update checksum
                    checksum = await self._calculate_project_checksum(project_path)
                    self.project_checksums[project_path] = checksum
                
                job.processed_projects += 1
                job.progress = 20.0 + (job.processed_projects / job.total_projects) * 60.0
                
            except Exception as e:
                logger.error(f"Error analyzing changed project {project_path}: {e}")
                job.errors.append(f"Analysis failed for {project_path}: {str(e)}")
        
        # Phase 2: Runtime monitoring update
        job.progress = 85.0
        await self.runtime_monitor.scan_processes()
        
        # Phase 3: Update integrations
        job.progress = 95.0
        if self.memory and analysis_results:
            await self._integrate_incremental_results_with_memory(job, analysis_results)
        
        job.results.update({
            "scan_type": "incremental",
            "analyzed_projects": len(analysis_results),
            "total_vulnerabilities": sum(len(r.security_issues) for r in analysis_results),
            "total_quality_issues": sum(len(r.quality_issues) for r in analysis_results)
        })
    
    async def _find_changed_projects(self) -> List[str]:
        """Find projects that have changed since last scan."""
        changed_projects = []
        
        try:
            for project_path, old_checksum in self.project_checksums.items():
                if Path(project_path).exists():
                    current_checksum = await self._calculate_project_checksum(project_path)
                    if current_checksum != old_checksum:
                        changed_projects.append(project_path)
            
        except Exception as e:
            logger.error(f"Error finding changed projects: {e}")
        
        return changed_projects
    
    async def _execute_runtime_scan(self, job: ScanJob) -> None:
        """Execute runtime monitoring only."""
        logger.info(f"Starting runtime scan {job.id}")
        
        job.progress = 25.0
        await self.runtime_monitor.scan_processes()
        
        job.progress = 50.0
        await self.runtime_monitor.scan_services()
        
        job.progress = 75.0
        if self.runtime_monitor.docker_client:
            await self.runtime_monitor.scan_containers()
        
        job.progress = 90.0
        system_metrics = await self.runtime_monitor.collect_system_metrics()
        
        job.results.update({
            "scan_type": "runtime",
            "processes": len(self.runtime_monitor.known_processes),
            "services": len(self.runtime_monitor.known_services),
            "containers": len(self.runtime_monitor.known_containers),
            "system_metrics": system_metrics.__dict__
        })
    
    async def _execute_analysis_scan(self, job: ScanJob) -> None:
        """Execute code analysis only for existing projects."""
        logger.info(f"Starting analysis scan {job.id}")
        
        # Get projects to analyze
        if job.project_filter:
            project_paths = job.project_filter
        else:
            stmt = select(Project.path, Project.id).where(Project.status == "active")
            result = await self.session.execute(stmt)
            projects = result.fetchall()
            project_paths = [(path, str(id_)) for path, id_ in projects if Path(path).exists()]
        
        job.total_projects = len(project_paths)
        analysis_results = []
        
        for i, (project_path, project_id) in enumerate(project_paths):
            try:
                analysis = await self.project_analyzer.analyze_project(project_path, project_id)
                analysis_results.append(analysis)
                
                job.processed_projects += 1
                job.progress = (job.processed_projects / job.total_projects) * 90.0
                
            except Exception as e:
                logger.error(f"Error analyzing project {project_path}: {e}")
                job.errors.append(f"Analysis failed for {project_path}: {str(e)}")
        
        job.results.update({
            "scan_type": "analysis",
            "analyzed_projects": len(analysis_results),
            "total_vulnerabilities": sum(len(r.security_issues) for r in analysis_results),
            "total_quality_issues": sum(len(r.quality_issues) for r in analysis_results),
            "average_score": sum(r.overall_score for r in analysis_results) / len(analysis_results) if analysis_results else 0
        })
    
    async def _execute_discovery_scan(self, job: ScanJob) -> None:
        """Execute project discovery only."""
        logger.info(f"Starting discovery scan {job.id}")
        
        job.progress = 30.0
        project_analyses = await self.project_scanner.scan_projects()
        
        job.progress = 70.0
        saved_projects = []
        
        for analysis in project_analyses:
            project_id = await self.project_scanner.save_project_analysis(analysis)
            if project_id:
                saved_projects.append(project_id)
        
        job.total_projects = len(project_analyses)
        job.processed_projects = len(saved_projects)
        
        job.results.update({
            "scan_type": "discovery",
            "discovered_projects": len(project_analyses),
            "saved_projects": len(saved_projects)
        })
    
    async def _analyze_project_batch(self, project_ids: List[str]) -> List[ProjectAnalysisResult]:
        """Analyze a batch of projects in parallel."""
        tasks = []
        
        for project_id in project_ids:
            # Get project path
            stmt = select(Project.path).where(Project.id == project_id)
            result = await self.session.execute(stmt)
            project_path = result.scalar_one_or_none()
            
            if project_path and Path(project_path).exists():
                task = asyncio.create_task(
                    self.project_analyzer.analyze_project(project_path, project_id)
                )
                tasks.append(task)
        
        if not tasks:
            return []
        
        # Wait for all analyses to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        successful_results = []
        for result in results:
            if isinstance(result, ProjectAnalysisResult):
                successful_results.append(result)
            else:
                logger.error(f"Project analysis failed: {result}")
        
        return successful_results
    
    async def _integrate_scan_results_with_kg(self, project_analyses: List[ProjectAnalysis], 
                                            analysis_results: List[ProjectAnalysisResult]) -> None:
        """Integrate scan results with knowledge graph."""
        if not self.kg:
            return
        
        try:
            # Add technology nodes and relationships
            technologies = set()
            
            for analysis in project_analyses:
                for lang in analysis.tech_stack.get("languages", []):
                    technologies.add(("Language", lang))
                for fw in analysis.frameworks:
                    technologies.add(("Framework", fw))
                for tool in analysis.build_tools:
                    technologies.add(("BuildTool", tool))
            
            # Add technology nodes
            for node_type, name in technologies:
                node_id = f"{node_type.lower()}_{name.replace(' ', '_')}"
                await self.kg.add_node(node_id, node_type, {"name": name})
            
            # Add security vulnerability patterns
            vulnerability_patterns = defaultdict(int)
            for result in analysis_results:
                for issue in result.security_issues:
                    pattern_key = f"{issue.category}_{issue.severity}"
                    vulnerability_patterns[pattern_key] += 1
            
            # Store patterns in knowledge graph
            for pattern, count in vulnerability_patterns.items():
                pattern_id = f"vuln_pattern_{pattern}"
                await self.kg.add_node(pattern_id, "VulnerabilityPattern", {
                    "pattern": pattern,
                    "frequency": count,
                    "last_seen": datetime.now(timezone.utc).isoformat()
                })
            
        except Exception as e:
            logger.error(f"Error integrating with knowledge graph: {e}")
    
    async def _integrate_scan_results_with_memory(self, job: ScanJob, 
                                                project_analyses: List[ProjectAnalysis],
                                                analysis_results: List[ProjectAnalysisResult]) -> None:
        """Integrate scan results with memory system."""
        if not self.memory:
            return
        
        try:
            # Store scan summary
            scan_context = {
                "type": "scan_summary",
                "job_id": job.id,
                "scan_type": job.scan_type.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "projects_analyzed": len(analysis_results),
                "total_vulnerabilities": sum(len(r.security_issues) for r in analysis_results),
                "total_quality_issues": sum(len(r.quality_issues) for r in analysis_results),
                "average_score": sum(r.overall_score for r in analysis_results) / len(analysis_results) if analysis_results else 0,
                "technologies_found": list(set(
                    lang for analysis in project_analyses 
                    for lang in analysis.tech_stack.get("languages", [])
                )),
                "common_issues": self._extract_common_issues(analysis_results)
            }
            
            await self.memory.store_context("scan_results", scan_context)
            
        except Exception as e:
            logger.error(f"Error integrating with memory system: {e}")
    
    async def _integrate_incremental_results_with_memory(self, job: ScanJob,
                                                       analysis_results: List[ProjectAnalysisResult]) -> None:
        """Store incremental scan results in memory."""
        if not self.memory:
            return
        
        try:
            incremental_context = {
                "type": "incremental_scan",
                "job_id": job.id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "changed_projects": len(analysis_results),
                "new_vulnerabilities": sum(len(r.security_issues) for r in analysis_results),
                "improvement_trends": self._calculate_improvement_trends(analysis_results)
            }
            
            await self.memory.store_context("incremental_scan", incremental_context)
            
        except Exception as e:
            logger.error(f"Error storing incremental results: {e}")
    
    def _extract_common_issues(self, analysis_results: List[ProjectAnalysisResult]) -> Dict[str, int]:
        """Extract common issues across all analyzed projects."""
        issue_counts = defaultdict(int)
        
        for result in analysis_results:
            # Security issues
            for issue in result.security_issues:
                issue_counts[f"security_{issue.category}"] += 1
            
            # Quality issues
            for issue in result.quality_issues:
                issue_counts[f"quality_{issue.category}"] += 1
        
        # Return top 10 most common issues
        return dict(sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10])
    
    def _calculate_improvement_trends(self, analysis_results: List[ProjectAnalysisResult]) -> Dict[str, Any]:
        """Calculate improvement trends from analysis results."""
        # This would compare with historical data to show trends
        # For now, return basic statistics
        
        if not analysis_results:
            return {}
        
        return {
            "average_security_score": sum(max(0, 100 - len(r.security_issues) * 10) for r in analysis_results) / len(analysis_results),
            "average_quality_score": sum(max(0, 100 - len(r.quality_issues) * 5) for r in analysis_results) / len(analysis_results),
            "projects_with_tests": sum(1 for r in analysis_results if r.test_analysis.total_tests > 0),
            "projects_with_good_docs": sum(1 for r in analysis_results if r.documentation.quality_level in ["good", "excellent"])
        }
    
    async def _trigger_council_analysis(self, job: ScanJob) -> None:
        """Trigger Council of Minds analysis for scan results."""
        if not self.council:
            return
        
        try:
            # Prepare analysis context
            context = {
                "scan_job": job.id,
                "scan_type": job.scan_type.value,
                "results": job.results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Request Council analysis
            discussion_topic = f"Analysis of {job.scan_type.value} scan results"
            if job.results.get("total_vulnerabilities", 0) > 0 or job.results.get("total_quality_issues", 0) > 0:
                discussion_topic = f"Security and quality review for {job.scan_type.value} scan"
            
            await self.council.start_deliberation(discussion_topic, context)
            
        except Exception as e:
            logger.error(f"Error triggering Council analysis: {e}")
    
    def _update_metrics(self, job: ScanJob, success: bool) -> None:
        """Update orchestrator metrics."""
        self.metrics.total_scans += 1
        
        if success:
            self.metrics.successful_scans += 1
        else:
            self.metrics.failed_scans += 1
        
        if job.started_at and job.completed_at:
            scan_duration = (job.completed_at - job.started_at).total_seconds()
            # Update running average
            total_successful = self.metrics.successful_scans
            if total_successful > 0:
                self.metrics.average_scan_time = (
                    (self.metrics.average_scan_time * (total_successful - 1) + scan_duration) / total_successful
                )
        
        # Update other metrics from job results
        if "discovered_projects" in job.results:
            self.metrics.projects_discovered += job.results["discovered_projects"]
        if "total_vulnerabilities" in job.results:
            self.metrics.vulnerabilities_found += job.results["total_vulnerabilities"]
        if "total_quality_issues" in job.results:
            self.metrics.quality_issues_found += job.results["total_quality_issues"]
    
    def _cleanup_job(self, job_id: str) -> None:
        """Clean up completed job."""
        if job_id in self.active_jobs:
            job = self.active_jobs.pop(job_id)
            self.job_history.append(job)
            
            # Keep only last 100 jobs in history
            if len(self.job_history) > 100:
                self.job_history = self.job_history[-100:]
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a scanning job."""
        job = self.active_jobs.get(job_id)
        if not job:
            # Check job history
            for historical_job in self.job_history:
                if historical_job.id == job_id:
                    job = historical_job
                    break
        
        if not job:
            return None
        
        return {
            "id": job.id,
            "scan_type": job.scan_type.value,
            "status": job.status.value,
            "progress": job.progress,
            "total_projects": job.total_projects,
            "processed_projects": job.processed_projects,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "errors": job.errors,
            "results": job.results
        }
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running scanning job."""
        job = self.active_jobs.get(job_id)
        if job and job.status == ScanStatus.RUNNING:
            job.status = ScanStatus.CANCELLED
            logger.info(f"Cancelled scan job {job_id}")
            return True
        return False
    
    async def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator status."""
        return {
            "active_jobs": len(self.active_jobs),
            "active_job_details": [
                {
                    "id": job.id,
                    "type": job.scan_type.value,
                    "status": job.status.value,
                    "progress": job.progress
                } for job in self.active_jobs.values()
            ],
            "metrics": {
                "total_scans": self.metrics.total_scans,
                "successful_scans": self.metrics.successful_scans,
                "failed_scans": self.metrics.failed_scans,
                "success_rate": (self.metrics.successful_scans / self.metrics.total_scans * 100) if self.metrics.total_scans > 0 else 0,
                "average_scan_time": self.metrics.average_scan_time,
                "projects_discovered": self.metrics.projects_discovered,
                "vulnerabilities_found": self.metrics.vulnerabilities_found,
                "quality_issues_found": self.metrics.quality_issues_found,
                "last_full_scan": self.metrics.last_full_scan.isoformat() if self.metrics.last_full_scan else None
            },
            "runtime_monitor": await self.runtime_monitor.get_system_overview(),
            "next_scheduled_scan": self._get_next_scheduled_scan(),
            "system_health": "healthy" if len(self.active_jobs) < self.max_concurrent_jobs else "busy"
        }
    
    def _get_next_scheduled_scan(self) -> Dict[str, Optional[str]]:
        """Calculate when next scheduled scans will occur."""
        now = datetime.now(timezone.utc)
        
        next_incremental = None
        next_full = None
        
        if self.last_incremental_scan:
            next_incremental = (self.last_incremental_scan + self.incremental_scan_interval).isoformat()
        else:
            next_incremental = now.isoformat()
        
        if self.last_full_scan:
            next_full = (self.last_full_scan + self.full_scan_interval).isoformat()
        else:
            next_full = now.isoformat()
        
        return {
            "next_incremental": next_incremental,
            "next_full": next_full
        }
    
    async def shutdown(self) -> None:
        """Shutdown the orchestrator and cleanup resources."""
        logger.info("Shutting down Scanner Orchestrator")
        
        # Cancel all background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Cancel active jobs
        for job_id in list(self.active_jobs.keys()):
            await self.cancel_job(job_id)
        
        logger.info("Scanner Orchestrator shutdown complete")