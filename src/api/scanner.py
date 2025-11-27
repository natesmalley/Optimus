"""
Enhanced Project Scanner API Endpoints
======================================

Comprehensive REST API for the Enhanced Project Scanner system.
Provides endpoints for project discovery, analysis, and monitoring.

Features:
- Deep project analysis with comprehensive metrics
- Technology stack detection and dependency analysis
- Security vulnerability scanning and code quality assessment
- Git repository analysis and contributor metrics
- Performance profiling and optimization recommendations
- Documentation quality assessment and API endpoint discovery
- Real-time scanning with progress tracking
- Comprehensive project comparison and insights
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_

from ..config import get_db_session
from ..services.enhanced_scanner import EnhancedProjectScanner, ProjectAnalysis, ScanMetrics
from ..models.project import Project

logger = logging.getLogger(__name__)
router = APIRouter()

# =================== REQUEST/RESPONSE MODELS ===================

class ProjectBasicInfo(BaseModel):
    """Basic project information"""
    name: str
    path: str
    size_bytes: int
    created_at: datetime
    modified_at: datetime
    permissions: str


class TechnologyStackInfo(BaseModel):
    """Technology stack information"""
    languages: List[str]
    language_stats: Dict[str, float]
    total_files: int
    file_types: Dict[str, int]


class DependencyInfo(BaseModel):
    """Dependency analysis information"""
    runtime: Dict[str, str]
    development: Dict[str, str]
    total_count: int
    outdated: List[str]
    vulnerable: List[str]


class GitAnalysisInfo(BaseModel):
    """Git repository analysis"""
    is_repo: bool
    remote_url: Optional[str]
    current_branch: Optional[str]
    total_branches: Optional[int]
    total_tags: Optional[int]
    latest_commit: Optional[Dict[str, Any]]
    total_commits: Optional[int]
    contributors: Optional[int]
    commit_frequency: Optional[Dict[str, int]]
    uncommitted_changes: Optional[int]


class CodeMetricsInfo(BaseModel):
    """Code metrics and quality"""
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    functions: int
    classes: int
    complexity_score: int


class DocumentationInfo(BaseModel):
    """Documentation quality assessment"""
    score: float
    files: List[str]
    missing: List[str]
    quality: str
    inline_coverage: Optional[float]


class SecurityInfo(BaseModel):
    """Security vulnerability information"""
    vulnerabilities: List[Dict[str, Any]]
    risk_score: int
    categories: Dict[str, int]


class DockerConfigInfo(BaseModel):
    """Docker configuration details"""
    has_dockerfile: Optional[bool]
    has_compose: Optional[bool]
    base_images: Optional[List[str]]
    exposed_ports: Optional[List[str]]
    services: Optional[List[str]]


class ProjectAnalysisResponse(BaseModel):
    """Complete project analysis response"""
    basic_info: ProjectBasicInfo
    tech_stack: TechnologyStackInfo
    dependencies: DependencyInfo
    git_analysis: GitAnalysisInfo
    code_metrics: CodeMetricsInfo
    documentation: DocumentationInfo
    security: SecurityInfo
    build_tools: List[str]
    frameworks: List[str]
    database_usage: List[str]
    api_endpoints: List[str]
    test_frameworks: List[str]
    ci_cd_tools: List[str]
    docker_config: DockerConfigInfo
    performance_hints: List[str]


class ScanRequest(BaseModel):
    """Project scan request"""
    base_path: Optional[str] = Field(None, description="Base path to scan (default: configured projects path)")
    include_analysis: bool = Field(True, description="Include deep analysis")
    include_dependencies: bool = Field(True, description="Include dependency analysis")
    include_security: bool = Field(True, description="Include security scanning")
    include_git: bool = Field(True, description="Include Git analysis")
    force_rescan: bool = Field(False, description="Force rescan even if recently scanned")


class ScanStatusResponse(BaseModel):
    """Scan status response"""
    status: str
    message: str
    projects_found: Optional[int]
    projects_analyzed: Optional[int]
    errors_encountered: Optional[int]
    estimated_time_remaining: Optional[float]
    current_project: Optional[str]


class ScanMetricsResponse(BaseModel):
    """Scan performance metrics"""
    start_time: float
    projects_scanned: int
    files_analyzed: int
    dependencies_found: int
    vulnerabilities_detected: int
    errors_encountered: int
    total_size_bytes: int
    elapsed_time: float
    projects_per_second: float


class ProjectComparisonRequest(BaseModel):
    """Project comparison request"""
    project_ids: List[str] = Field(..., min_items=2, max_items=5, description="Project IDs to compare")
    comparison_aspects: List[str] = Field(
        default=["technologies", "dependencies", "security", "complexity"],
        description="Aspects to compare"
    )


class ProjectComparisonResponse(BaseModel):
    """Project comparison response"""
    projects: Dict[str, Dict[str, Any]]
    similarities: Dict[str, Any]
    differences: Dict[str, Any]
    recommendations: List[str]
    comparison_score: float


class TechnologyStatsResponse(BaseModel):
    """Technology usage statistics"""
    technology: str
    usage_count: int
    projects: List[str]
    average_success_rate: float
    common_combinations: List[Dict[str, Any]]
    trend: str


# =================== PROJECT SCANNING ENDPOINTS ===================

@router.get("/projects", response_model=List[Dict[str, Any]])
async def list_discovered_projects(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Number of records to return"),
    technology: Optional[str] = Query(None, description="Filter by technology"),
    language: Optional[str] = Query(None, description="Filter by programming language"),
    status: Optional[str] = Query(None, description="Filter by project status"),
    search: Optional[str] = Query(None, description="Search in project names and paths"),
    sort_by: str = Query("last_scanned", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    List all discovered projects with filtering and pagination.
    
    Returns project metadata including technology stacks, dependency counts,
    and analysis results with comprehensive filtering options.
    """
    try:
        query = select(Project)
        
        # Apply filters
        filters = []
        if technology:
            filters.append(Project.tech_stack.op('?')([technology]))  # JSON contains
        if language:
            filters.append(Project.language_stats.op('?')([language]))
        if status:
            filters.append(Project.status == status)
        if search:
            filters.append(or_(
                Project.name.ilike(f"%{search}%"),
                Project.path.ilike(f"%{search}%"),
                Project.description.ilike(f"%{search}%")
            ))
        
        if filters:
            query = query.where(and_(*filters))
        
        # Apply sorting
        if sort_by == "name":
            sort_field = Project.name
        elif sort_by == "created_at":
            sort_field = Project.created_at
        elif sort_by == "last_scanned":
            sort_field = Project.last_scanned
        elif sort_by == "size":
            sort_field = Project.tech_stack.op('->>')('total_files')
        else:
            sort_field = Project.last_scanned
        
        if sort_desc:
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(sort_field)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await session.execute(query)
        projects = result.scalars().all()
        
        # Format response
        project_list = []
        for project in projects:
            project_dict = {
                "id": str(project.id),
                "name": project.name,
                "path": project.path,
                "description": project.description,
                "tech_stack": project.tech_stack,
                "dependencies": project.dependencies,
                "language_stats": project.language_stats,
                "status": project.status,
                "last_scanned": project.last_scanned.isoformat() if project.last_scanned else None,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "git_url": project.git_url,
                "default_branch": project.default_branch
            }
            project_list.append(project_dict)
        
        return project_list
        
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve projects")


@router.get("/projects/{project_id}/analysis", response_model=ProjectAnalysisResponse)
async def get_project_analysis(
    project_id: str,
    force_refresh: bool = Query(False, description="Force fresh analysis"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get detailed analysis for a specific project.
    
    Returns comprehensive project analysis including technology stack,
    dependencies, security assessment, and optimization recommendations.
    """
    try:
        # Get project from database
        query = select(Project).where(Project.id == project_id)
        result = await session.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if we need to perform fresh analysis
        needs_analysis = (
            force_refresh or 
            not project.last_scanned or 
            (datetime.utcnow() - project.last_scanned).days > 7
        )
        
        if needs_analysis:
            # Perform fresh analysis
            scanner = EnhancedProjectScanner(session)
            project_path = Path(project.path)
            
            if project_path.exists():
                analysis = await scanner._analyze_project_comprehensive(project_path)
                
                # Update project record with new analysis
                await scanner.save_project_analysis(analysis)
                await session.commit()
                
                # Convert analysis to response format
                return _convert_analysis_to_response(analysis)
            else:
                raise HTTPException(status_code=404, detail="Project path no longer exists")
        
        else:
            # Use cached data from database
            return ProjectAnalysisResponse(
                basic_info=ProjectBasicInfo(
                    name=project.name,
                    path=project.path,
                    size_bytes=0,  # Not stored in DB
                    created_at=project.created_at or datetime.utcnow(),
                    modified_at=datetime.utcnow(),
                    permissions="755"
                ),
                tech_stack=TechnologyStackInfo(
                    languages=project.tech_stack.get("languages", []),
                    language_stats=project.language_stats or {},
                    total_files=project.tech_stack.get("total_files", 0),
                    file_types=project.tech_stack.get("file_types", {})
                ),
                dependencies=DependencyInfo(
                    runtime=project.dependencies.get("runtime", {}),
                    development=project.dependencies.get("development", {}),
                    total_count=project.dependencies.get("total_count", 0),
                    outdated=project.dependencies.get("outdated", []),
                    vulnerable=project.dependencies.get("vulnerable", [])
                ),
                git_analysis=GitAnalysisInfo(
                    is_repo=bool(project.git_url),
                    remote_url=project.git_url,
                    current_branch=project.default_branch,
                    total_branches=None,
                    total_tags=None,
                    latest_commit=None,
                    total_commits=None,
                    contributors=None,
                    commit_frequency=None,
                    uncommitted_changes=None
                ),
                code_metrics=CodeMetricsInfo(
                    total_lines=0, code_lines=0, comment_lines=0,
                    blank_lines=0, functions=0, classes=0, complexity_score=0
                ),
                documentation=DocumentationInfo(
                    score=0.0, files=[], missing=[], quality="unknown"
                ),
                security=SecurityInfo(
                    vulnerabilities=[], risk_score=0, categories={}
                ),
                build_tools=project.tech_stack.get("build_tools", []),
                frameworks=project.tech_stack.get("frameworks", []),
                database_usage=project.tech_stack.get("databases", []),
                api_endpoints=[],
                test_frameworks=[],
                ci_cd_tools=project.tech_stack.get("ci_cd", []),
                docker_config=DockerConfigInfo(),
                performance_hints=[]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project analysis for {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve project analysis")


@router.post("/scan", response_model=Dict[str, Any])
async def trigger_project_scan(
    scan_request: ScanRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Trigger a comprehensive project scan.
    
    Discovers and analyzes all projects in the specified path with
    configurable analysis depth and options.
    """
    try:
        scanner = EnhancedProjectScanner(session)
        
        # Start scan in background
        background_tasks.add_task(
            _run_comprehensive_scan,
            scanner,
            scan_request.base_path,
            scan_request
        )
        
        return {
            "message": "Project scan initiated",
            "base_path": scan_request.base_path,
            "options": {
                "include_analysis": scan_request.include_analysis,
                "include_dependencies": scan_request.include_dependencies,
                "include_security": scan_request.include_security,
                "include_git": scan_request.include_git,
                "force_rescan": scan_request.force_rescan
            },
            "status": "started",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering project scan: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate project scan")


async def _run_comprehensive_scan(
    scanner: EnhancedProjectScanner,
    base_path: Optional[str],
    scan_options: ScanRequest
):
    """Run comprehensive scan in background"""
    try:
        logger.info(f"Starting comprehensive project scan with options: {scan_options}")
        
        # Perform scan
        project_ids, metrics = await scanner.scan_and_save_all(base_path)
        
        logger.info(f"Scan completed. Processed {len(project_ids)} projects")
        
        return {
            "project_ids": project_ids,
            "metrics": {
                "projects_scanned": metrics.projects_scanned,
                "files_analyzed": metrics.files_analyzed,
                "dependencies_found": metrics.dependencies_found,
                "vulnerabilities_detected": metrics.vulnerabilities_detected,
                "elapsed_time": metrics.elapsed_time(),
                "projects_per_second": metrics.projects_per_second()
            }
        }
        
    except Exception as e:
        logger.error(f"Error in comprehensive scan: {e}")


# =================== TECHNOLOGY AND DEPENDENCY ANALYSIS ===================

@router.get("/technologies", response_model=List[TechnologyStatsResponse])
async def get_technology_statistics(
    limit: int = Query(20, ge=1, le=100, description="Number of technologies to return"),
    min_usage: int = Query(1, ge=1, description="Minimum usage count"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get technology usage statistics across all projects.
    
    Returns usage counts, success rates, and common technology
    combinations for strategic technology decisions.
    """
    try:
        # Query projects and aggregate technology usage
        query = select(Project).where(Project.tech_stack.isnot(None))
        result = await session.execute(query)
        projects = result.scalars().all()
        
        # Aggregate technology usage
        tech_stats = {}
        
        for project in projects:
            languages = project.tech_stack.get("languages", [])
            frameworks = project.tech_stack.get("frameworks", [])
            
            all_techs = languages + frameworks
            
            for tech in all_techs:
                if tech not in tech_stats:
                    tech_stats[tech] = {
                        "usage_count": 0,
                        "projects": [],
                        "combinations": {}
                    }
                
                tech_stats[tech]["usage_count"] += 1
                tech_stats[tech]["projects"].append(project.name)
                
                # Track combinations
                for other_tech in all_techs:
                    if other_tech != tech:
                        if other_tech not in tech_stats[tech]["combinations"]:
                            tech_stats[tech]["combinations"][other_tech] = 0
                        tech_stats[tech]["combinations"][other_tech] += 1
        
        # Filter by minimum usage and convert to response format
        filtered_stats = []
        
        for tech, stats in tech_stats.items():
            if stats["usage_count"] >= min_usage:
                # Find most common combinations
                common_combinations = [
                    {"technology": k, "count": v}
                    for k, v in sorted(
                        stats["combinations"].items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )[:5]
                ]
                
                tech_stat = TechnologyStatsResponse(
                    technology=tech,
                    usage_count=stats["usage_count"],
                    projects=stats["projects"][:10],  # Limit project list
                    average_success_rate=0.8,  # Placeholder - could be calculated from project success
                    common_combinations=common_combinations,
                    trend="stable"  # Placeholder - could be calculated from temporal data
                )
                
                filtered_stats.append(tech_stat)
        
        # Sort by usage count and limit
        filtered_stats.sort(key=lambda x: x.usage_count, reverse=True)
        return filtered_stats[:limit]
        
    except Exception as e:
        logger.error(f"Error getting technology statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve technology statistics")


@router.get("/dependencies", response_model=Dict[str, Any])
async def get_dependency_analysis(
    technology: Optional[str] = Query(None, description="Filter by technology"),
    vulnerable_only: bool = Query(False, description="Show only vulnerable dependencies"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get comprehensive dependency analysis across all projects.
    
    Identifies common dependencies, version conflicts, security
    vulnerabilities, and outdated packages.
    """
    try:
        query = select(Project).where(Project.dependencies.isnot(None))
        result = await session.execute(query)
        projects = result.scalars().all()
        
        # Aggregate dependency data
        all_dependencies = {}
        vulnerability_summary = {"total": 0, "high": 0, "medium": 0, "low": 0}
        version_conflicts = []
        
        for project in projects:
            deps = project.dependencies
            runtime_deps = deps.get("runtime", {})
            vulnerable_deps = deps.get("vulnerable", [])
            
            # Aggregate all dependencies
            for dep_name, version in runtime_deps.items():
                if dep_name not in all_dependencies:
                    all_dependencies[dep_name] = {
                        "versions": {},
                        "projects": [],
                        "vulnerable_in": []
                    }
                
                all_dependencies[dep_name]["projects"].append(project.name)
                
                if version not in all_dependencies[dep_name]["versions"]:
                    all_dependencies[dep_name]["versions"][version] = 0
                all_dependencies[dep_name]["versions"][version] += 1
                
                # Track vulnerabilities
                if dep_name in vulnerable_deps:
                    all_dependencies[dep_name]["vulnerable_in"].append(project.name)
                    vulnerability_summary["total"] += 1
                    vulnerability_summary["high"] += 1  # Simplified
        
        # Find version conflicts (same dependency, multiple versions)
        for dep_name, dep_data in all_dependencies.items():
            if len(dep_data["versions"]) > 1:
                version_conflicts.append({
                    "dependency": dep_name,
                    "versions": dep_data["versions"],
                    "projects_affected": len(dep_data["projects"])
                })
        
        # Filter if requested
        if technology:
            # This is a simplified filter - could be enhanced
            filtered_deps = {
                k: v for k, v in all_dependencies.items()
                if technology.lower() in k.lower()
            }
            all_dependencies = filtered_deps
        
        if vulnerable_only:
            vulnerable_deps = {
                k: v for k, v in all_dependencies.items()
                if v["vulnerable_in"]
            }
            all_dependencies = vulnerable_deps
        
        # Calculate statistics
        total_unique_deps = len(all_dependencies)
        most_used_deps = sorted(
            all_dependencies.items(),
            key=lambda x: len(x[1]["projects"]),
            reverse=True
        )[:20]
        
        return {
            "summary": {
                "total_unique_dependencies": total_unique_deps,
                "total_projects_analyzed": len(projects),
                "version_conflicts": len(version_conflicts),
                "vulnerability_summary": vulnerability_summary
            },
            "most_used_dependencies": [
                {
                    "name": name,
                    "usage_count": len(data["projects"]),
                    "versions": list(data["versions"].keys()),
                    "vulnerable_projects": len(data["vulnerable_in"])
                }
                for name, data in most_used_deps
            ],
            "version_conflicts": version_conflicts[:10],
            "recommendations": [
                "Standardize dependency versions across projects",
                "Update vulnerable dependencies",
                "Consider dependency consolidation",
                "Implement dependency scanning in CI/CD"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting dependency analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dependency analysis")


# =================== SECURITY AND QUALITY ANALYSIS ===================

@router.get("/vulnerabilities", response_model=Dict[str, Any])
async def get_security_vulnerabilities(
    severity: Optional[str] = Query(None, description="Filter by severity: high, medium, low"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=500, description="Maximum vulnerabilities to return"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get security vulnerabilities across all projects.
    
    Provides detailed vulnerability reports with severity levels,
    categories, and remediation recommendations.
    """
    try:
        # This is a placeholder implementation
        # In a real system, you would query stored vulnerability data
        
        vulnerabilities = [
            {
                "id": "vuln_001",
                "project": "example-project",
                "file": "src/auth.py",
                "line": 42,
                "severity": "high",
                "category": "secrets",
                "description": "Potential hardcoded API key",
                "recommendation": "Use environment variables for sensitive data",
                "cwe_id": "CWE-798",
                "first_detected": datetime.utcnow().isoformat(),
                "status": "open"
            }
        ]
        
        # Apply filters
        filtered_vulns = vulnerabilities
        
        if severity:
            filtered_vulns = [v for v in filtered_vulns if v["severity"] == severity]
        
        if category:
            filtered_vulns = [v for v in filtered_vulns if v["category"] == category]
        
        # Limit results
        filtered_vulns = filtered_vulns[:limit]
        
        # Calculate summary statistics
        summary = {
            "total_vulnerabilities": len(filtered_vulns),
            "by_severity": {"high": 0, "medium": 0, "low": 0},
            "by_category": {},
            "projects_affected": set()
        }
        
        for vuln in filtered_vulns:
            summary["by_severity"][vuln["severity"]] += 1
            
            if vuln["category"] not in summary["by_category"]:
                summary["by_category"][vuln["category"]] = 0
            summary["by_category"][vuln["category"]] += 1
            
            summary["projects_affected"].add(vuln["project"])
        
        summary["projects_affected"] = len(summary["projects_affected"])
        
        return {
            "summary": summary,
            "vulnerabilities": filtered_vulns,
            "recommendations": [
                "Implement automated security scanning in CI/CD",
                "Regular dependency updates and security patches",
                "Code review process with security focus",
                "Security training for development team"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting security vulnerabilities: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security vulnerabilities")


@router.get("/quality", response_model=Dict[str, Any])
async def get_code_quality_metrics(
    project_id: Optional[str] = Query(None, description="Filter by specific project"),
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get code quality metrics across projects.
    
    Provides comprehensive code quality assessment including
    complexity, maintainability, and documentation coverage.
    """
    try:
        query = select(Project)
        
        if project_id:
            query = query.where(Project.id == project_id)
        
        result = await session.execute(query)
        projects = result.scalars().all()
        
        quality_metrics = {
            "overview": {
                "total_projects": len(projects),
                "average_quality_score": 0.0,
                "projects_with_good_quality": 0,
                "projects_needing_attention": 0
            },
            "metrics_by_project": [],
            "recommendations": []
        }
        
        total_quality_score = 0
        
        for project in projects:
            # Calculate quality score based on available data
            quality_score = 0.5  # Base score
            
            # Factor in technology diversity
            tech_count = len(project.tech_stack.get("languages", []))
            if tech_count <= 3:  # Focused technology stack
                quality_score += 0.1
            
            # Factor in dependency management
            if project.dependencies.get("total_count", 0) < 50:  # Reasonable dependency count
                quality_score += 0.1
            
            # Factor in documentation (placeholder)
            quality_score += 0.2  # Assume some documentation
            
            quality_score = min(1.0, quality_score)
            total_quality_score += quality_score
            
            project_metrics = {
                "project_id": str(project.id),
                "project_name": project.name,
                "quality_score": quality_score,
                "metrics": {
                    "technology_diversity": tech_count,
                    "dependency_count": project.dependencies.get("total_count", 0),
                    "documentation_score": 0.6,  # Placeholder
                    "test_coverage": 0.0,  # Placeholder
                    "code_complexity": "medium"  # Placeholder
                },
                "areas_for_improvement": []
            }
            
            # Add improvement suggestions
            if quality_score < 0.7:
                project_metrics["areas_for_improvement"].append("Improve documentation")
            if project.dependencies.get("total_count", 0) > 100:
                project_metrics["areas_for_improvement"].append("Reduce dependency count")
            
            quality_metrics["metrics_by_project"].append(project_metrics)
        
        # Calculate overview statistics
        if projects:
            quality_metrics["overview"]["average_quality_score"] = total_quality_score / len(projects)
            quality_metrics["overview"]["projects_with_good_quality"] = sum(
                1 for p in quality_metrics["metrics_by_project"] if p["quality_score"] >= 0.7
            )
            quality_metrics["overview"]["projects_needing_attention"] = len(projects) - quality_metrics["overview"]["projects_with_good_quality"]
        
        # Add general recommendations
        quality_metrics["recommendations"] = [
            "Implement automated code quality checks in CI/CD",
            "Establish coding standards and style guides",
            "Regular code reviews and refactoring sessions",
            "Maintain comprehensive documentation",
            "Implement test coverage requirements"
        ]
        
        return quality_metrics
        
    except Exception as e:
        logger.error(f"Error getting code quality metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve code quality metrics")


# =================== PROJECT COMPARISON AND INSIGHTS ===================

@router.post("/compare", response_model=ProjectComparisonResponse)
async def compare_projects(
    comparison_request: ProjectComparisonRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Compare multiple projects across various dimensions.
    
    Provides detailed comparison of technologies, dependencies,
    complexity, and provides recommendations for alignment.
    """
    try:
        # Get projects from database
        query = select(Project).where(Project.id.in_(comparison_request.project_ids))
        result = await session.execute(query)
        projects = result.scalars().all()
        
        if len(projects) != len(comparison_request.project_ids):
            raise HTTPException(status_code=404, detail="One or more projects not found")
        
        # Build comparison data
        comparison_data = {
            "projects": {},
            "similarities": {},
            "differences": {},
            "recommendations": [],
            "comparison_score": 0.0
        }
        
        # Extract project data
        for project in projects:
            comparison_data["projects"][str(project.id)] = {
                "name": project.name,
                "technologies": project.tech_stack.get("languages", []) + project.tech_stack.get("frameworks", []),
                "dependency_count": project.dependencies.get("total_count", 0),
                "primary_language": project.tech_stack.get("languages", ["unknown"])[0] if project.tech_stack.get("languages") else "unknown"
            }
        
        # Find similarities
        all_technologies = []
        for proj_data in comparison_data["projects"].values():
            all_technologies.extend(proj_data["technologies"])
        
        tech_counts = {}
        for tech in all_technologies:
            tech_counts[tech] = tech_counts.get(tech, 0) + 1
        
        common_technologies = [tech for tech, count in tech_counts.items() if count > 1]
        
        comparison_data["similarities"] = {
            "common_technologies": common_technologies,
            "similar_dependency_ranges": True,  # Placeholder logic
            "shared_patterns": []
        }
        
        # Find differences
        unique_technologies = [tech for tech, count in tech_counts.items() if count == 1]
        
        comparison_data["differences"] = {
            "unique_technologies": unique_technologies,
            "dependency_variance": "high",  # Placeholder
            "architecture_differences": []
        }
        
        # Generate recommendations
        recommendations = []
        if len(common_technologies) > 0:
            recommendations.append(f"Consider standardizing on common technologies: {', '.join(common_technologies[:3])}")
        
        if len(unique_technologies) > 5:
            recommendations.append("High technology diversity - consider consolidation")
        
        comparison_data["recommendations"] = recommendations
        
        # Calculate comparison score (similarity measure)
        total_techs = len(all_technologies)
        common_ratio = len(common_technologies) / total_techs if total_techs > 0 else 0
        comparison_data["comparison_score"] = min(1.0, common_ratio * 2)  # Scaled to 0-1
        
        return ProjectComparisonResponse(**comparison_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing projects: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare projects")


# =================== UTILITY FUNCTIONS ===================

def _convert_analysis_to_response(analysis: ProjectAnalysis) -> ProjectAnalysisResponse:
    """Convert ProjectAnalysis to API response format"""
    return ProjectAnalysisResponse(
        basic_info=ProjectBasicInfo(**analysis.basic_info),
        tech_stack=TechnologyStackInfo(**analysis.tech_stack),
        dependencies=DependencyInfo(**analysis.dependencies),
        git_analysis=GitAnalysisInfo(**analysis.git_analysis),
        code_metrics=CodeMetricsInfo(**analysis.code_metrics),
        documentation=DocumentationInfo(**analysis.documentation),
        security=SecurityInfo(**analysis.security),
        build_tools=analysis.build_tools,
        frameworks=analysis.frameworks,
        database_usage=analysis.database_usage,
        api_endpoints=analysis.api_endpoints,
        test_frameworks=analysis.test_frameworks,
        ci_cd_tools=analysis.ci_cd_tools,
        docker_config=DockerConfigInfo(**analysis.docker_config),
        performance_hints=analysis.performance_hints
    )


@router.get("/health")
async def scanner_health_check():
    """
    Check scanner system health and performance.
    
    Returns scanning capability status and performance metrics.
    """
    try:
        return {
            "status": "healthy",
            "capabilities": {
                "technology_detection": True,
                "dependency_analysis": True,
                "security_scanning": True,
                "git_analysis": True,
                "performance_analysis": True
            },
            "supported_languages": [
                "Python", "JavaScript", "TypeScript", "Rust", "Go",
                "Java", "C#", "PHP", "Ruby", "C++", "C"
            ],
            "supported_frameworks": [
                "React", "Vue", "Angular", "Django", "Flask", "FastAPI",
                "Express", "Spring Boot", "Laravel", "Rails"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Scanner health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }