"""
The Guardian - Security, Safety, and Risk Management

Focuses on protecting systems, data, and users from threats and risks.
Ensures compliance, security, and reliability.
"""

from typing import Dict, List, Any
from ..persona import Persona, PersonaResponse, PersonaPriority
from ..blackboard import BlackboardEntry


class GuardianPersona(Persona):
    """
    The Guardian protects against risks and ensures safety
    
    Key traits:
    - Security-focused
    - Risk-aware
    - Compliance-minded
    - Defensive thinking
    - Quality assurance
    """
    
    def __init__(self):
        super().__init__(
            persona_id="guardian",
            name="The Guardian",
            description="Security and risk management expert focused on protection and compliance",
            expertise_domains=[
                "security",
                "risk management",
                "compliance",
                "data protection",
                "reliability",
                "disaster recovery",
                "audit",
                "quality assurance"
            ],
            personality_traits=[
                "cautious",
                "thorough",
                "protective",
                "detail-oriented",
                "skeptical"
            ]
        )
    
    async def analyze(self,
                     query: str,
                     context: Dict[str, Any],
                     related_entries: List[BlackboardEntry]) -> PersonaResponse:
        """Analyze from a security and risk perspective"""
        
        confidence = self.calculate_confidence(query, context)
        
        # Risk assessment
        risks = self._identify_risks(query, context)
        security_implications = self._assess_security_implications(context)
        compliance_check = self._check_compliance(context)
        
        # Build recommendation
        if risks['critical_risks']:
            recommendation = f"CRITICAL: Address {risks['highest_risk']} before proceeding"
        elif security_implications['vulnerabilities']:
            recommendation = f"Implement security measures: {security_implications['required_measures']}"
        elif compliance_check['issues']:
            recommendation = f"Ensure compliance with {compliance_check['regulations']} before deployment"
        else:
            recommendation = "Proceed with standard security practices and monitoring"
        
        concerns = []
        for risk in risks['risk_list']:
            concerns.append(f"{risk['type']}: {risk['description']}")
        if security_implications.get('data_exposure'):
            concerns.append("Potential for sensitive data exposure")
        if compliance_check.get('audit_risk'):
            concerns.append("May trigger compliance audit requirements")
        
        opportunities = []
        if security_implications.get('security_improvement'):
            opportunities.append("Opportunity to strengthen security posture")
        if risks.get('risk_mitigation_available'):
            opportunities.append("Known mitigation strategies available")
        
        return PersonaResponse(
            persona_id=self.persona_id,
            persona_name=self.name,
            recommendation=recommendation,
            reasoning=self._explain_guardian_thinking(risks, security_implications, compliance_check),
            confidence=confidence,
            priority=self._determine_risk_priority(risks, security_implications),
            concerns=concerns,
            opportunities=opportunities,
            data_points={
                'risk_level': risks['overall_risk_level'],
                'security_score': security_implications['security_score'],
                'compliance_status': compliance_check['status'],
                'critical_risks': len(risks.get('critical_risks', []))
            },
            tags={'security', 'risk', 'compliance', 'protection'}
        )
    
    def calculate_confidence(self, query: str, context: Dict[str, Any]) -> float:
        """Calculate confidence in risk assessment"""
        confidence = 0.7  # Guardians are confident in identifying risks
        
        if context.get('security_audit_done'):
            confidence += 0.15
        if context.get('known_vulnerabilities'):
            confidence += 0.1
        if context.get('untested_code'):
            confidence -= 0.15
        if 'security' in query.lower() or 'risk' in query.lower():
            confidence += 0.1
            
        return max(0.4, min(0.95, confidence))
    
    def _identify_risks(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Identify potential risks"""
        risk_list = []
        overall_risk = "low"
        
        # Check for common risk patterns
        query_lower = query.lower()
        if 'database' in query_lower or 'data' in query_lower:
            risk_list.append({'type': 'data', 'description': 'Data integrity or loss risk'})
        if 'api' in query_lower or 'external' in query_lower:
            risk_list.append({'type': 'integration', 'description': 'External dependency risk'})
        if 'user' in query_lower or 'authentication' in query_lower:
            risk_list.append({'type': 'access', 'description': 'Unauthorized access risk'})
        if 'ai' in query_lower or 'biometric' in query_lower:
            risk_list.append({'type': 'privacy', 'description': 'Privacy and biometric data risk'})
        
        critical_risks = [r for r in risk_list if context.get(f"{r['type']}_critical", False)]
        
        if critical_risks:
            overall_risk = "critical"
        elif len(risk_list) > 2:
            overall_risk = "high"
        elif risk_list:
            overall_risk = "medium"
        
        return {
            'risk_list': risk_list,
            'critical_risks': critical_risks,
            'highest_risk': critical_risks[0]['description'] if critical_risks else None,
            'overall_risk_level': overall_risk,
            'risk_mitigation_available': context.get('mitigation_strategies', False)
        }
    
    def _assess_security_implications(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess security implications"""
        security_score = 0.7  # Default moderate security
        vulnerabilities = []
        
        if context.get('uses_encryption', True):
            security_score += 0.1
        if context.get('authentication_required', True):
            security_score += 0.1
        if context.get('exposes_api', False):
            security_score -= 0.15
            vulnerabilities.append("API exposure")
        if context.get('handles_pii', False):
            vulnerabilities.append("PII handling")
        
        return {
            'security_score': min(1.0, max(0.0, security_score)),
            'vulnerabilities': vulnerabilities,
            'data_exposure': context.get('handles_pii', False),
            'required_measures': "encryption, authentication, audit logging" if vulnerabilities else "standard",
            'security_improvement': security_score < 0.8
        }
    
    def _check_compliance(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check compliance requirements"""
        issues = []
        regulations = []
        
        if context.get('handles_pii'):
            regulations.append("GDPR/CCPA")
        if context.get('financial_data'):
            regulations.append("PCI-DSS")
        if context.get('healthcare_data'):
            regulations.append("HIPAA")
        
        return {
            'status': 'compliant' if not regulations else 'review_required',
            'issues': issues,
            'regulations': ', '.join(regulations),
            'audit_risk': len(regulations) > 0
        }
    
    def _explain_guardian_thinking(self, risks, security, compliance) -> str:
        """Explain security and risk reasoning"""
        reasoning = f"Risk assessment: {risks['overall_risk_level']} risk level. "
        reasoning += f"Security score: {security['security_score']:.0%}. "
        
        if risks['critical_risks']:
            reasoning += f"Critical risks identified requiring immediate attention. "
        if security['vulnerabilities']:
            reasoning += f"Security vulnerabilities: {', '.join(security['vulnerabilities'])}. "
        if compliance['status'] != 'compliant':
            reasoning += f"Compliance review needed for {compliance['regulations']}. "
        
        reasoning += "Defensive measures and monitoring essential for protection."
        return reasoning
    
    def _determine_risk_priority(self, risks: Dict[str, Any], security: Dict[str, Any]) -> PersonaPriority:
        """Determine priority based on risk level"""
        if risks['overall_risk_level'] == 'critical' or security['security_score'] < 0.3:
            return PersonaPriority.CRITICAL
        if risks['overall_risk_level'] == 'high' or security['vulnerabilities']:
            return PersonaPriority.HIGH
        if risks['overall_risk_level'] == 'low':
            return PersonaPriority.LOW
        return PersonaPriority.MEDIUM