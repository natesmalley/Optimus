#!/usr/bin/env python3
"""
Demo: Optimus Council of Minds in Action
Shows how 5 personas deliberate on project decisions
"""

import asyncio
from src.council.orchestrator import Orchestrator, DeliberationRequest

async def demo():
    print("=" * 60)
    print("🤖 OPTIMUS COUNCIL OF MINDS - DEMONSTRATION")
    print("=" * 60)
    print()
    
    # Initialize the Council
    print("Initializing the Council of Minds...")
    orchestrator = Orchestrator()
    await orchestrator.initialize()
    print(f"✅ Council ready with {len(orchestrator.personas)} personas\n")
    
    # Example query
    query = "Should we migrate our monolithic application to microservices?"
    
    context = {
        "current_architecture": "monolith",
        "team_size": 8,
        "user_count": 50000,
        "scaling_issues": True,
        "team_experience": False,
        "clear_requirements": True,
        "deployment_frequency": "weekly",
        "performance_issues": True,
        "technical_debt_high": True
    }
    
    print("=" * 60)
    print("QUERY:", query)
    print("=" * 60)
    print("\nContext provided:")
    for key, value in context.items():
        print(f"  • {key}: {value}")
    
    print("\n🧠 Council is deliberating...")
    print("-" * 60)
    
    # Create deliberation request
    request = DeliberationRequest(
        query=query,
        context=context,
        topic="microservices_migration"
    )
    
    # Get the decision
    result = await orchestrator.deliberate(request)
    
    # Display individual persona thoughts
    print("\n📊 INDIVIDUAL PERSONA PERSPECTIVES:")
    print("-" * 60)
    
    for response in result.persona_responses:
        print(f"\n🎭 {response.persona_name}")
        print(f"   Recommendation: {response.recommendation}")
        print(f"   Confidence: {response.confidence:.0%}")
        print(f"   Priority: {response.priority.name}")
        print(f"   Reasoning: {response.reasoning[:150]}...")
        
        if response.concerns:
            print(f"   ⚠️  Concerns: {response.concerns[0]}")
        if response.opportunities:
            print(f"   💡 Opportunity: {response.opportunities[0]}")
    
    # Display consensus
    print("\n" + "=" * 60)
    print("🎯 COUNCIL CONSENSUS")
    print("=" * 60)
    
    consensus = result.consensus
    print(f"\nDecision: {consensus.decision}")
    print(f"Confidence: {consensus.confidence:.0%}")
    print(f"Agreement Level: {consensus.agreement_level:.0%}")
    print(f"Priority: {consensus.priority.name}")
    print(f"Method Used: {consensus.method_used.value}")
    
    print(f"\nRationale: {consensus.rationale}")
    
    if consensus.dissenting_personas:
        print(f"\n⚠️  Dissenting Personas: {', '.join(consensus.dissenting_personas)}")
        for persona, alt_view in list(consensus.alternative_views.items())[:2]:
            print(f"   • {persona}: {alt_view[:100]}...")
    
    # Display statistics
    stats = result.statistics
    print(f"\n📈 DELIBERATION STATISTICS:")
    print(f"   • Time taken: {stats['deliberation_time']:.2f} seconds")
    print(f"   • Blackboard entries: {stats['blackboard_entries']}")
    print(f"   • Concerns raised: {stats['concerns_raised']}")
    print(f"   • Opportunities identified: {stats['opportunities_identified']}")
    print(f"   • Average confidence: {stats['avg_confidence']:.0%}")
    
    # Explain the decision
    print("\n" + "=" * 60)
    print("💭 DECISION EXPLANATION")
    print("=" * 60)
    
    explanation = await orchestrator.explain_decision("microservices_migration")
    print(explanation)
    
    print("\n✅ Council deliberation complete!")
    print("\nThe Optimus Council of Minds provides multi-perspective intelligence")
    print("where every decision benefits from diverse expert viewpoints.")

if __name__ == "__main__":
    asyncio.run(demo())