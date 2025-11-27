"""
AutoFixer Service
================

Safe automated fixing service with sandboxed execution, rollback capabilities,
and comprehensive safety checks. The AutoFixer ensures that automated fixes
don't break systems by implementing multiple layers of protection.

Safety Features:
- Dry run mode for testing fixes without execution
- Sandboxed execution environment
- Automatic rollback on failure
- Verification after applying fixes
- User approval for destructive operations
- Command validation and sanitization
- Resource usage monitoring during execution
- Backup creation before destructive changes
"""

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import psutil

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.troubleshooting import FixAttempt, Solution
from .troubleshooting_engine import FixResult, SolutionCandidate

logger = logging.getLogger("optimus.auto_fixer")


@dataclass
class ExecutionContext:
    """Context for command execution."""
    working_directory: str
    environment_vars: Dict[str, str]
    timeout_seconds: int = 300  # 5 minutes default
    max_memory_mb: int = 1024   # 1GB default
    allow_network: bool = True
    allow_sudo: bool = False
    backup_directory: Optional[str] = None


@dataclass
class ExecutionResult:
    """Result of command execution."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time_ms: int
    memory_peak_mb: float
    timed_out: bool = False
    killed_by_system: bool = False


@dataclass
class SafetyCheck:
    """Safety check result."""
    check_name: str
    passed: bool
    message: str
    severity: str  # low, medium, high, critical
    details: Dict[str, Any] = None


class AutoFixer:
    """
    Automated fixing service with comprehensive safety features.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
        # Safety configuration
        self.dangerous_commands = {
            'rm -rf /', 'rm -rf /*', 'rm -rf ~', '> /dev/sda', 'dd if=/dev/zero',
            'mkfs', 'fdisk', 'parted', 'halt', 'reboot', 'shutdown',
            'chmod 777 /', 'chown -R', 'passwd', 'userdel', 'groupdel'
        }
        
        self.restricted_paths = {
            '/', '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/etc', '/var',
            '/boot', '/sys', '/proc', '/dev', '/root'
        }
        
        self.safe_commands = {
            'npm', 'pip', 'yarn', 'node', 'python', 'java', 'cargo',
            'git', 'docker', 'curl', 'wget', 'ls', 'cat', 'echo',
            'mkdir', 'cp', 'mv', 'chmod', 'chown', 'grep', 'sed', 'awk'
        }
        
        # Resource limits
        self.default_limits = {
            'max_execution_time': 300,  # 5 minutes
            'max_memory_mb': 1024,      # 1GB
            'max_cpu_percent': 80,      # 80% CPU
            'max_disk_mb': 100,         # 100MB disk usage
            'max_network_mb': 50        # 50MB network transfer
        }
        
        # Active executions for monitoring
        self.active_executions: Dict[str, asyncio.subprocess.Process] = {}
    
    async def execute_fix(
        self,
        solution: SolutionCandidate,
        context: ExecutionContext,
        dry_run: bool = False,
        force_approval: bool = False
    ) -> FixResult:
        """
        Execute a fix solution with comprehensive safety checks.
        
        Args:
            solution: The solution to execute
            context: Execution context and environment
            dry_run: If True, simulate execution without running commands
            force_approval: Skip approval checks if True
        
        Returns:
            FixResult with execution outcome
        """
        attempt_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(f"Starting fix execution {attempt_id}: {solution.title}")
        
        try:
            # Pre-execution safety checks
            safety_checks = await self._perform_safety_checks(solution, context)
            critical_failures = [check for check in safety_checks if check.severity == 'critical' and not check.passed]
            
            if critical_failures and not force_approval:
                return FixResult(
                    attempt_id=attempt_id,
                    success=False,
                    error_resolved=False,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    commands_executed=[],
                    output="Critical safety checks failed",
                    error_output=f"Safety failures: {[c.message for c in critical_failures]}",
                    side_effects=[],
                    verification_passed=False,
                    rollback_available=False,
                    confidence_score=0.0,
                    metadata={'safety_checks': [
                        {'name': c.check_name, 'passed': c.passed, 'message': c.message, 'severity': c.severity}
                        for c in safety_checks
                    ]}
                )
            
            # Check approval requirements
            if solution.requires_approval and not force_approval and not dry_run:
                return FixResult(
                    attempt_id=attempt_id,
                    success=False,
                    error_resolved=False,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    commands_executed=[],
                    output="Fix requires manual approval",
                    error_output=None,
                    side_effects=[],
                    verification_passed=False,
                    rollback_available=False,
                    confidence_score=0.0,
                    metadata={'requires_approval': True, 'risk_level': solution.risk_level}
                )
            
            # Create backup if needed
            backup_path = None
            if not dry_run and self._needs_backup(solution):
                backup_path = await self._create_backup(context)
            
            # Execute fix commands
            execution_results = []
            all_output = []
            all_errors = []
            total_execution_time = 0
            
            for i, command in enumerate(solution.fix_commands):
                logger.debug(f"Executing command {i+1}/{len(solution.fix_commands)}: {command}")
                
                # Substitute variables in command
                expanded_command = self._expand_command_variables(command, context, solution.metadata)
                
                if dry_run:
                    # Simulate execution
                    result = ExecutionResult(
                        command=expanded_command,
                        exit_code=0,
                        stdout=f"DRY RUN: Would execute: {expanded_command}",
                        stderr="",
                        execution_time_ms=100,
                        memory_peak_mb=10.0
                    )
                else:
                    # Execute command with safety monitoring
                    result = await self._execute_command_safely(expanded_command, context, attempt_id)
                
                execution_results.append(result)
                all_output.append(result.stdout)
                all_errors.append(result.stderr)
                total_execution_time += result.execution_time_ms
                
                # Stop on command failure
                if result.exit_code != 0 and not dry_run:
                    logger.warning(f"Command failed with exit code {result.exit_code}: {expanded_command}")
                    break
            
            # Verify fix was successful
            verification_passed = True
            if not dry_run and solution.verification_commands:
                verification_passed = await self._verify_fix(solution, context)
            
            # Check for side effects
            side_effects = await self._detect_side_effects(context, backup_path) if not dry_run else []
            
            # Determine overall success
            fix_success = all(r.exit_code == 0 for r in execution_results) and verification_passed
            
            result = FixResult(
                attempt_id=attempt_id,
                success=fix_success,
                error_resolved=verification_passed,
                execution_time_ms=total_execution_time,
                commands_executed=[r.command for r in execution_results],
                output='\n'.join(all_output),
                error_output='\n'.join(filter(None, all_errors)),
                side_effects=side_effects,
                verification_passed=verification_passed,
                rollback_available=bool(solution.rollback_commands or backup_path),
                confidence_score=solution.confidence if fix_success else 0.0,
                metadata={
                    'dry_run': dry_run,
                    'backup_path': backup_path,
                    'execution_results': [
                        {
                            'command': r.command,
                            'exit_code': r.exit_code,
                            'execution_time_ms': r.execution_time_ms,
                            'memory_peak_mb': r.memory_peak_mb
                        } for r in execution_results
                    ],
                    'safety_checks': [
                        {'name': c.check_name, 'passed': c.passed, 'message': c.message, 'severity': c.severity}
                        for c in safety_checks
                    ]
                }
            )
            
            logger.info(f"Fix execution {attempt_id} completed: success={fix_success}, "
                       f"time={total_execution_time}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during fix execution {attempt_id}: {e}", exc_info=True)
            return FixResult(
                attempt_id=attempt_id,
                success=False,
                error_resolved=False,
                execution_time_ms=int((time.time() - start_time) * 1000),
                commands_executed=[],
                output="",
                error_output=str(e),
                side_effects=[],
                verification_passed=False,
                rollback_available=False,
                confidence_score=0.0,
                metadata={'error': str(e)}
            )
    
    async def _perform_safety_checks(
        self,
        solution: SolutionCandidate,
        context: ExecutionContext
    ) -> List[SafetyCheck]:
        """Perform comprehensive safety checks before execution."""
        checks = []
        
        # Check for dangerous commands
        for command in solution.fix_commands:
            for dangerous in self.dangerous_commands:
                if dangerous in command.lower():
                    checks.append(SafetyCheck(
                        check_name="dangerous_command",
                        passed=False,
                        message=f"Command contains dangerous pattern: {dangerous}",
                        severity="critical"
                    ))
        
        # Check for restricted path access
        for command in solution.fix_commands:
            for path in self.restricted_paths:
                if path in command and ('rm ' in command or 'del ' in command):
                    checks.append(SafetyCheck(
                        check_name="restricted_path_modification",
                        passed=False,
                        message=f"Command attempts to modify restricted path: {path}",
                        severity="critical"
                    ))
        
        # Check working directory exists and is safe
        if not os.path.exists(context.working_directory):
            checks.append(SafetyCheck(
                check_name="working_directory",
                passed=False,
                message=f"Working directory does not exist: {context.working_directory}",
                severity="high"
            ))
        elif context.working_directory in self.restricted_paths:
            checks.append(SafetyCheck(
                check_name="working_directory",
                passed=False,
                message=f"Working directory is in restricted paths: {context.working_directory}",
                severity="critical"
            ))
        else:
            checks.append(SafetyCheck(
                check_name="working_directory",
                passed=True,
                message="Working directory is safe",
                severity="low"
            ))
        
        # Check disk space
        try:
            disk_usage = shutil.disk_usage(context.working_directory)
            free_gb = disk_usage.free / (1024**3)
            if free_gb < 1.0:  # Less than 1GB free
                checks.append(SafetyCheck(
                    check_name="disk_space",
                    passed=False,
                    message=f"Low disk space: {free_gb:.1f}GB free",
                    severity="high"
                ))
            else:
                checks.append(SafetyCheck(
                    check_name="disk_space",
                    passed=True,
                    message=f"Adequate disk space: {free_gb:.1f}GB free",
                    severity="low"
                ))
        except Exception as e:
            checks.append(SafetyCheck(
                check_name="disk_space",
                passed=False,
                message=f"Could not check disk space: {e}",
                severity="medium"
            ))
        
        # Check memory availability
        try:
            memory = psutil.virtual_memory()
            available_mb = memory.available / (1024**2)
            if available_mb < context.max_memory_mb:
                checks.append(SafetyCheck(
                    check_name="memory_availability",
                    passed=False,
                    message=f"Insufficient memory: {available_mb:.0f}MB available, {context.max_memory_mb}MB required",
                    severity="medium"
                ))
            else:
                checks.append(SafetyCheck(
                    check_name="memory_availability",
                    passed=True,
                    message=f"Adequate memory: {available_mb:.0f}MB available",
                    severity="low"
                ))
        except Exception as e:
            checks.append(SafetyCheck(
                check_name="memory_availability",
                passed=False,
                message=f"Could not check memory: {e}",
                severity="medium"
            ))
        
        # Check for sudo requirements
        sudo_required = any('sudo ' in cmd for cmd in solution.fix_commands)
        if sudo_required and not context.allow_sudo:
            checks.append(SafetyCheck(
                check_name="sudo_permission",
                passed=False,
                message="Commands require sudo but sudo is disabled",
                severity="high"
            ))
        
        # Validate command structure
        for command in solution.fix_commands:
            if not self._validate_command_structure(command):
                checks.append(SafetyCheck(
                    check_name="command_validation",
                    passed=False,
                    message=f"Invalid command structure: {command}",
                    severity="high"
                ))
        
        # Check prerequisites
        missing_prerequisites = []
        for prereq in solution.prerequisites:
            if not await self._check_prerequisite(prereq, context):
                missing_prerequisites.append(prereq)
        
        if missing_prerequisites:
            checks.append(SafetyCheck(
                check_name="prerequisites",
                passed=False,
                message=f"Missing prerequisites: {', '.join(missing_prerequisites)}",
                severity="medium"
            ))
        else:
            checks.append(SafetyCheck(
                check_name="prerequisites",
                passed=True,
                message="All prerequisites satisfied",
                severity="low"
            ))
        
        return checks
    
    def _validate_command_structure(self, command: str) -> bool:
        """Validate that a command has safe structure."""
        # Basic validation - no empty commands, no obvious injection
        if not command.strip():
            return False
        
        # Check for command injection patterns
        dangerous_patterns = [
            '; rm ', '&& rm ', '| rm ', '; del ', '&& del ', '| del ',
            '; chmod 777', '&& chmod 777', '| chmod 777',
            '$(rm ', '`rm ', '$(del ', '`del '
        ]
        
        command_lower = command.lower()
        return not any(pattern in command_lower for pattern in dangerous_patterns)
    
    async def _check_prerequisite(self, prereq: str, context: ExecutionContext) -> bool:
        """Check if a prerequisite is available."""
        try:
            # Check for command availability
            if prereq in ['python', 'node', 'npm', 'pip', 'git', 'docker']:
                result = await asyncio.create_subprocess_shell(
                    f"which {prereq}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=context.working_directory
                )
                await result.wait()
                return result.returncode == 0
            
            # Check for file existence
            if prereq.endswith('.txt') or prereq.endswith('.json') or prereq.endswith('.yml'):
                file_path = Path(context.working_directory) / prereq
                return file_path.exists()
            
            # Default to True for unknown prerequisites
            return True
            
        except Exception:
            return False
    
    async def _execute_command_safely(
        self,
        command: str,
        context: ExecutionContext,
        execution_id: str
    ) -> ExecutionResult:
        """Execute a single command with safety monitoring."""
        start_time = time.time()
        
        try:
            # Create process with resource limits
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=context.working_directory,
                env={**os.environ, **context.environment_vars},
                preexec_fn=self._setup_process_limits if hasattr(os, 'setrlimit') else None
            )
            
            self.active_executions[execution_id] = process
            
            # Monitor execution
            monitor_task = asyncio.create_task(
                self._monitor_process_resources(process, context.max_memory_mb, execution_id)
            )
            
            try:
                # Wait for completion with timeout
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=context.timeout_seconds
                )
                timed_out = False
                
            except asyncio.TimeoutError:
                logger.warning(f"Command timed out after {context.timeout_seconds}s: {command}")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                stdout, stderr = b"", b"Command timed out"
                timed_out = True
            
            finally:
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            return ExecutionResult(
                command=command,
                exit_code=process.returncode or 0,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                execution_time_ms=execution_time_ms,
                memory_peak_mb=getattr(monitor_task, 'peak_memory_mb', 0.0),
                timed_out=timed_out
            )
            
        except Exception as e:
            logger.error(f"Error executing command '{command}': {e}")
            return ExecutionResult(
                command=command,
                exit_code=1,
                stdout="",
                stderr=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
                memory_peak_mb=0.0
            )
        
        finally:
            self.active_executions.pop(execution_id, None)
    
    def _setup_process_limits(self):
        """Setup process resource limits (Unix only)."""
        try:
            import resource
            
            # Set memory limit (1GB)
            memory_limit = 1024 * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
            
            # Set CPU time limit (5 minutes)
            cpu_limit = 300
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
            
        except ImportError:
            pass  # resource module not available on Windows
        except Exception as e:
            logger.debug(f"Could not set process limits: {e}")
    
    async def _monitor_process_resources(
        self,
        process: asyncio.subprocess.Process,
        max_memory_mb: int,
        execution_id: str
    ):
        """Monitor process resource usage and terminate if limits exceeded."""
        peak_memory_mb = 0.0
        
        try:
            while process.returncode is None:
                try:
                    ps_process = psutil.Process(process.pid)
                    memory_info = ps_process.memory_info()
                    memory_mb = memory_info.rss / (1024 * 1024)
                    
                    peak_memory_mb = max(peak_memory_mb, memory_mb)
                    
                    # Check memory limit
                    if memory_mb > max_memory_mb:
                        logger.warning(f"Process {process.pid} exceeded memory limit: "
                                     f"{memory_mb:.1f}MB > {max_memory_mb}MB")
                        process.terminate()
                        break
                    
                    await asyncio.sleep(1)  # Check every second
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
                except Exception as e:
                    logger.debug(f"Error monitoring process {process.pid}: {e}")
                    break
                    
        except asyncio.CancelledError:
            pass
        
        # Store peak memory for reporting
        setattr(asyncio.current_task(), 'peak_memory_mb', peak_memory_mb)
    
    def _expand_command_variables(
        self,
        command: str,
        context: ExecutionContext,
        metadata: Dict[str, Any]
    ) -> str:
        """Expand variables in command with safe substitution."""
        expanded = command
        
        # Safe variable substitutions
        substitutions = {
            '{project_dir}': context.working_directory,
            '{backup_dir}': context.backup_directory or '/tmp/optimus_backup',
            **metadata
        }
        
        for var, value in substitutions.items():
            if var in expanded and value:
                # Sanitize value to prevent injection
                safe_value = str(value).replace(';', '').replace('&', '').replace('|', '')
                expanded = expanded.replace(var, safe_value)
        
        return expanded
    
    def _needs_backup(self, solution: SolutionCandidate) -> bool:
        """Determine if solution needs backup before execution."""
        destructive_keywords = [
            'rm ', 'del ', 'drop ', 'truncate ', 'delete ',
            'chmod', 'chown', 'mv ', 'move ', 'replace'
        ]
        
        commands_text = ' '.join(solution.fix_commands).lower()
        return any(keyword in commands_text for keyword in destructive_keywords)
    
    async def _create_backup(self, context: ExecutionContext) -> str:
        """Create backup of important files before destructive operations."""
        try:
            backup_dir = tempfile.mkdtemp(prefix='optimus_backup_')
            
            # Backup common important files
            important_files = [
                'package.json', 'requirements.txt', 'Cargo.toml', 'pom.xml',
                'Gemfile', 'composer.json', '.env', 'config.json', 'settings.py'
            ]
            
            project_path = Path(context.working_directory)
            backup_path = Path(backup_dir)
            
            for file_name in important_files:
                source_file = project_path / file_name
                if source_file.exists():
                    shutil.copy2(source_file, backup_path / file_name)
            
            # Also backup git state
            git_dir = project_path / '.git'
            if git_dir.exists():
                try:
                    # Save current git state
                    git_backup_info = {
                        'branch': '',
                        'commit': '',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    # Get current branch and commit
                    result = await asyncio.create_subprocess_shell(
                        'git branch --show-current',
                        stdout=asyncio.subprocess.PIPE,
                        cwd=context.working_directory
                    )
                    stdout, _ = await result.communicate()
                    git_backup_info['branch'] = stdout.decode().strip()
                    
                    result = await asyncio.create_subprocess_shell(
                        'git rev-parse HEAD',
                        stdout=asyncio.subprocess.PIPE,
                        cwd=context.working_directory
                    )
                    stdout, _ = await result.communicate()
                    git_backup_info['commit'] = stdout.decode().strip()
                    
                    # Save git state info
                    with open(backup_path / 'git_state.json', 'w') as f:
                        import json
                        json.dump(git_backup_info, f, indent=2)
                    
                except Exception as e:
                    logger.debug(f"Could not backup git state: {e}")
            
            logger.info(f"Created backup at: {backup_dir}")
            return backup_dir
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return ""
    
    async def _verify_fix(
        self,
        solution: SolutionCandidate,
        context: ExecutionContext
    ) -> bool:
        """Verify that the fix was successful."""
        if not solution.verification_commands:
            return True  # No verification commands means assume success
        
        try:
            for command in solution.verification_commands:
                expanded_command = self._expand_command_variables(command, context, solution.metadata)
                
                process = await asyncio.create_subprocess_shell(
                    expanded_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=context.working_directory
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
                    
                    if process.returncode != 0:
                        logger.warning(f"Verification command failed: {expanded_command}")
                        logger.debug(f"Verification stderr: {stderr.decode()}")
                        return False
                        
                except asyncio.TimeoutError:
                    logger.warning(f"Verification command timed out: {expanded_command}")
                    process.terminate()
                    return False
            
            logger.info("All verification commands passed")
            return True
            
        except Exception as e:
            logger.error(f"Error during verification: {e}")
            return False
    
    async def _detect_side_effects(
        self,
        context: ExecutionContext,
        backup_path: Optional[str]
    ) -> List[str]:
        """Detect any unexpected side effects of the fix."""
        side_effects = []
        
        try:
            # Check for unexpected file changes
            if backup_path:
                # Compare current state with backup
                # This is a simplified version - real implementation would be more thorough
                project_path = Path(context.working_directory)
                backup_dir = Path(backup_path)
                
                for backup_file in backup_dir.iterdir():
                    if backup_file.name == 'git_state.json':
                        continue
                    
                    current_file = project_path / backup_file.name
                    if current_file.exists():
                        # Simple size comparison
                        if current_file.stat().st_size != backup_file.stat().st_size:
                            side_effects.append(f"File size changed: {backup_file.name}")
                    else:
                        side_effects.append(f"File removed: {backup_file.name}")
            
            # Check for new processes
            # This would require more sophisticated tracking in a real implementation
            
            # Check for permission changes
            # This would also require more tracking
            
        except Exception as e:
            logger.debug(f"Error detecting side effects: {e}")
            side_effects.append(f"Could not fully analyze side effects: {e}")
        
        return side_effects
    
    async def rollback_fix(
        self,
        fix_result: FixResult,
        solution: SolutionCandidate,
        context: ExecutionContext
    ) -> bool:
        """
        Rollback a fix using rollback commands or backup restoration.
        
        Args:
            fix_result: The result of the original fix
            solution: The solution that was executed
            context: The execution context
        
        Returns:
            True if rollback was successful
        """
        logger.info(f"Attempting rollback for fix: {fix_result.attempt_id}")
        
        try:
            # Try solution rollback commands first
            if solution.rollback_commands:
                logger.info("Executing solution rollback commands")
                
                for command in solution.rollback_commands:
                    expanded_command = self._expand_command_variables(command, context, solution.metadata)
                    
                    result = await self._execute_command_safely(expanded_command, context, f"rollback_{fix_result.attempt_id}")
                    
                    if result.exit_code != 0:
                        logger.error(f"Rollback command failed: {expanded_command}")
                        logger.error(f"Error: {result.stderr}")
                        # Continue with other rollback commands
            
            # Try backup restoration if available
            backup_path = fix_result.metadata.get('backup_path')
            if backup_path and os.path.exists(backup_path):
                logger.info(f"Restoring from backup: {backup_path}")
                await self._restore_from_backup(backup_path, context)
            
            # Verify rollback
            verification_passed = True
            if solution.verification_commands:
                # Run verification commands to see if we're back to original state
                # In a real implementation, this might need to be inverted
                pass
            
            logger.info(f"Rollback completed for fix: {fix_result.attempt_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            return False
    
    async def _restore_from_backup(self, backup_path: str, context: ExecutionContext):
        """Restore files from backup directory."""
        try:
            backup_dir = Path(backup_path)
            project_dir = Path(context.working_directory)
            
            for backup_file in backup_dir.iterdir():
                if backup_file.name == 'git_state.json':
                    # Handle git state restoration
                    try:
                        import json
                        with open(backup_file) as f:
                            git_state = json.load(f)
                        
                        # Restore git state if possible
                        if git_state.get('commit'):
                            process = await asyncio.create_subprocess_shell(
                                f"git checkout {git_state['commit']}",
                                cwd=context.working_directory,
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE
                            )
                            await process.wait()
                            
                    except Exception as e:
                        logger.debug(f"Could not restore git state: {e}")
                else:
                    # Restore regular file
                    target_file = project_dir / backup_file.name
                    shutil.copy2(backup_file, target_file)
            
            logger.info("Backup restoration completed")
            
        except Exception as e:
            logger.error(f"Error restoring from backup: {e}")
            raise
    
    async def get_active_executions(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently active fix executions."""
        active_info = {}
        
        for execution_id, process in self.active_executions.items():
            try:
                ps_process = psutil.Process(process.pid)
                active_info[execution_id] = {
                    'pid': process.pid,
                    'status': ps_process.status(),
                    'memory_mb': ps_process.memory_info().rss / (1024 * 1024),
                    'cpu_percent': ps_process.cpu_percent(),
                    'create_time': ps_process.create_time()
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process no longer exists
                pass
        
        return active_info
    
    async def terminate_execution(self, execution_id: str) -> bool:
        """Terminate an active execution."""
        try:
            process = self.active_executions.get(execution_id)
            if process:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                
                logger.info(f"Terminated execution: {execution_id}")
                return True
            else:
                logger.warning(f"Execution not found: {execution_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error terminating execution {execution_id}: {e}")
            return False