#!/usr/bin/env python3
"""
Test the Optimus Council of Minds

Demonstrates multi-persona deliberation on various project decisions.
"""

import asyncio
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.markdown import Markdown

from src.council.orchestrator import Orchestrator, DeliberationRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

console = Console()


async def test_deliberation(orchestrator: Orchestrator, query: str, context: dict = None):
    """Run a test deliberation and display results"""
    
    console.print(f"\n[bold cyan]📋 Query:[/bold cyan] {query}")
    console.print("[dim]Council is deliberating...[/dim]\n")
    
    # Create request
    request = DeliberationRequest(
        query=query,
        context=context or {},
        topic=f"test_{query[:20].replace(' ', '_')}"
    )
    
    # Deliberate
    result = await orchestrator.deliberate(request)
    
    # Display consensus
    consensus_panel = Panel(
        f"[bold green]{result.consensus.decision}[/bold green]\n\n"
        f"[yellow]Confidence:[/yellow] {result.consensus.confidence:.0%}\n"
        f"[yellow]Agreement:[/yellow] {result.consensus.agreement_level:.0%}\n"
        f"[yellow]Priority:[/yellow] {result.consensus.priority.value}\n"
        f"[yellow]Method:[/yellow] {result.consensus.method_used.value}",
        title="🎯 Council Decision",
        border_style="green"
    )
    console.print(consensus_panel)
    
    # Display individual persona responses
    table = Table(title="🎭 Persona Responses", show_header=True)
    table.add_column("Persona", style="cyan")
    table.add_column("Recommendation", style="white")
    table.add_column("Confidence", style="yellow")
    table.add_column("Priority", style="magenta")
    
    for response in result.persona_responses:
        table.add_row(
            response.persona_name,
            response.recommendation[:60] + "..." if len(response.recommendation) > 60 else response.recommendation,
            f"{response.confidence:.0%}",
            str(response.priority.value)
        )
    
    console.print(table)
    
    # Show rationale
    console.print(f"\n[bold]Rationale:[/bold] {result.consensus.rationale}")
    
    # Show any dissent
    if result.consensus.dissenting_personas:
        console.print(f"\n[yellow]Dissenting views from:[/yellow] {', '.join(result.consensus.dissenting_personas)}")
        for persona, view in result.consensus.alternative_views.items():
            console.print(f"  • {persona}: {view[:100]}...")
    
    # Show statistics
    stats = result.statistics
    console.print(f"\n[dim]Deliberation took {stats['deliberation_time']:.2f}s with "
                 f"{stats['blackboard_entries']} blackboard entries[/dim]")
    
    return result


async def main():
    """Run test scenarios"""
    
    console.print(Panel.fit(
        "[bold cyan]Optimus Council of Minds Test Suite[/bold cyan]\n"
        "Testing multi-persona deliberation system",
        border_style="cyan"
    ))
    
    # Initialize orchestrator
    orchestrator = Orchestrator()
    await orchestrator.initialize()
    
    # Test scenarios
    scenarios = [
        {
            "query": "Should we refactor our legacy authentication system?",
            "context": {
                "project_age_days": 730,
                "technical_debt_high": True,
                "team_bandwidth": 0.6,
                "security_audit_done": False,
                "user_count": 5000,
                "performance_issues": True
            }
        },
        {
            "query": "Should we add AI-powered code review to our development workflow?",
            "context": {
                "team_experience": True,
                "open_to_experimentation": True,
                "current_review_time": "2 days average",
                "code_quality_issues": True,
                "budget_available": True
            }
        },
        {
            "query": "Should we migrate from monolith to microservices architecture?",
            "context": {
                "current_architecture": "monolith",
                "scaling_issues": True,
                "team_size": 15,
                "deployment_frequency": "monthly",
                "clear_requirements": False,
                "complexity": "very_high"
            }
        },
        {
            "query": "Should we open-source our internal development tools?",
            "context": {
                "tools_maturity": "stable",
                "competitive_advantage": False,
                "maintenance_burden": 0.3,
                "community_interest": True,
                "security_reviewed": True,
                "documentation_quality": "good"
            }
        }
    ]
    
    # Run each scenario
    for i, scenario in enumerate(scenarios, 1):
        console.print(f"\n[bold magenta]═══ Scenario {i} of {len(scenarios)} ═══[/bold magenta]")
        await test_deliberation(orchestrator, scenario["query"], scenario["context"])
        
        if i < len(scenarios):
            console.print("\n[dim]Press Enter to continue to next scenario...[/dim]")
            input()
    
    # Show performance summary
    console.print("\n[bold cyan]═══ Persona Performance Summary ═══[/bold cyan]\n")
    
    performance = await orchestrator.get_persona_performance()
    
    perf_table = Table(title="Persona Activity Metrics", show_header=True)
    perf_table.add_column("Persona", style="cyan")
    perf_table.add_column("Participation", style="white")
    perf_table.add_column("Consensus Rate", style="green")
    perf_table.add_column("Avg Confidence", style="yellow")
    perf_table.add_column("Primary Expertise", style="magenta")
    
    for persona_id, metrics in performance.items():
        perf_table.add_row(
            metrics['name'],
            str(metrics['participation_count']),
            f"{metrics['consensus_rate']:.0%}",
            f"{metrics['avg_confidence']:.0%}",
            ", ".join(metrics['expertise_domains'][:2])
        )
    
    console.print(perf_table)
    
    # Show deliberation history summary
    console.print("\n[bold cyan]═══ Deliberation History ═══[/bold cyan]\n")
    
    history = await orchestrator.get_deliberation_history()
    
    for i, delib in enumerate(history, 1):
        console.print(f"{i}. [yellow]{delib['query'][:60]}...[/yellow]")
        console.print(f"   Decision: [green]{delib['decision'][:80]}...[/green]")
        console.print(f"   Confidence: {delib['confidence']:.0%} | Agreement: {delib['agreement']:.0%}")
        console.print()
    
    console.print("[bold green]✅ Council of Minds test complete![/bold green]")


if __name__ == "__main__":
    asyncio.run(main())