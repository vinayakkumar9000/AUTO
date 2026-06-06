#!/usr/bin/env python3
"""
Learning Agent
Persistent learning system that improves over time
Author: vinayakkumar9000
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base_agent import BaseAgent, AgentResult, AgentContext, AgentStatus
from ai_model_router import ModelRouter
from domain_intelligence import DomainIntelligence, RegistrationAttempt
import logging

# ============================================================================
# LEARNING AGENT
# ============================================================================

class LearningAgent(BaseAgent):
    """
    Learning Agent - Continuous improvement through learning.
    
    Responsibilities:
    - Store successful patterns
    - Update domain intelligence
    - Track success rates
    - Rank selectors by performance
    - Identify improvement opportunities
    - Generate insights
    """
    
    def __init__(
        self,
        model_router: ModelRouter,
        domain_intelligence: DomainIntelligence,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Learning Agent.
        
        Args:
            model_router: Model router instance
            domain_intelligence: Domain intelligence database
            logger: Optional logger instance
        """
        super().__init__("learning", model_router, logger)
        self.domain_intelligence = domain_intelligence
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Learn from registration attempt.
        
        Args:
            context: Execution context with attempt results
        
        Returns:
            AgentResult with learning insights
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Learning from attempt for {context.domain}")
            
            # Get attempt results
            attempt_data = context.metadata.get("attempt_results", {})
            
            if not attempt_data:
                return self._create_error_result(
                    start_time,
                    "No attempt results provided"
                )
            
            # Extract learning data
            success = attempt_data.get("success", False)
            selectors_used = attempt_data.get("selectors_used", {})
            execution_time = attempt_data.get("execution_time", 0)
            total_cost = attempt_data.get("total_cost", 0)
            
            # Update domain profile
            profile_updated = self._update_domain_profile(
                context.domain,
                success,
                selectors_used,
                attempt_data
            )
            
            # Update selector performance
            if selectors_used:
                self._update_selector_performance(
                    context.domain,
                    selectors_used,
                    success
                )
            
            # Generate insights
            insights = self._generate_insights(
                context.domain,
                attempt_data
            )
            
            # Identify improvements
            improvements = self._identify_improvements(
                context.domain,
                attempt_data
            )
            
            learning_data = {
                "domain": context.domain,
                "success": success,
                "profile_updated": profile_updated,
                "selectors_learned": len(selectors_used),
                "insights": insights,
                "improvements": improvements,
                "execution_time": execution_time,
                "cost": total_cost
            }
            
            confidence = 1.0 if profile_updated else 0.5
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.SUCCESS,
                data=learning_data,
                confidence=confidence,
                execution_time=execution_time,
                cost=0.0,
                model_used="learning_system"
            )
            
        except Exception as e:
            self.logger.error(f"Learning error: {str(e)}")
            return self._create_error_result(start_time, str(e))
    
    def get_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate confidence score for learning."""
        if result.get("profile_updated"):
            return 1.0
        return 0.5
    
    # ========================================================================
    # LEARNING METHODS
    # ========================================================================
    
    def _update_domain_profile(
        self,
        domain: str,
        success: bool,
        selectors_used: Dict[str, str],
        attempt_data: Dict[str, Any]
    ) -> bool:
        """Update domain profile with new data."""
        try:
            profile = self.domain_intelligence.get_or_create_profile(domain)
            
            # Update attempt counts
            profile.total_attempts += 1
            if success:
                profile.successful_attempts += 1
            else:
                profile.failed_attempts += 1
            
            # Update success rate
            profile.success_rate = (
                profile.successful_attempts / profile.total_attempts
            )
            
            # Update known selectors on success
            if success and selectors_used:
                for field_type, selector in selectors_used.items():
                    if field_type not in profile.known_selectors:
                        profile.known_selectors[field_type] = []
                    
                    if selector not in profile.known_selectors[field_type]:
                        profile.known_selectors[field_type].insert(0, selector)
                        self.logger.info(f"Learned new selector for {field_type}: {selector}")
            
            # Update framework if detected
            if "framework" in attempt_data:
                profile.framework = attempt_data["framework"]
            
            # Update verification type
            if "verification_type" in attempt_data:
                profile.verification_type = attempt_data["verification_type"]
            
            # Update anti-bot mechanisms
            if "anti_bot" in attempt_data:
                for mechanism in attempt_data["anti_bot"]:
                    if mechanism not in profile.anti_bot_mechanisms:
                        profile.anti_bot_mechanisms.append(mechanism)
            
            # Update OTP timing
            if "otp_wait_time" in attempt_data:
                otp_time = attempt_data["otp_wait_time"]
                if profile.otp_average_seconds:
                    # Running average
                    profile.otp_average_seconds = int(
                        (profile.otp_average_seconds + otp_time) / 2
                    )
                else:
                    profile.otp_average_seconds = otp_time
            
            # Save profile
            self.domain_intelligence.update_profile(profile)
            
            self.logger.info(
                f"Updated profile for {domain}: "
                f"success_rate={profile.success_rate:.2%}, "
                f"attempts={profile.total_attempts}"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating profile: {e}")
            return False
    
    def _update_selector_performance(
        self,
        domain: str,
        selectors_used: Dict[str, str],
        success: bool
    ) -> None:
        """Update selector performance tracking."""
        try:
            for field_type, selector in selectors_used.items():
                # This is handled by domain_intelligence internally
                pass
        except Exception as e:
            self.logger.error(f"Error updating selector performance: {e}")
    
    # ========================================================================
    # INSIGHTS GENERATION
    # ========================================================================
    
    def _generate_insights(
        self,
        domain: str,
        attempt_data: Dict[str, Any]
    ) -> List[str]:
        """Generate insights from attempt."""
        insights = []
        
        # Get domain profile
        profile = self.domain_intelligence.get_profile(domain)
        
        if not profile:
            return insights
        
        # Success rate insights
        if profile.total_attempts >= 5:
            if profile.success_rate >= 0.9:
                insights.append(f"High success rate ({profile.success_rate:.0%}) - selectors are reliable")
            elif profile.success_rate < 0.5:
                insights.append(f"Low success rate ({profile.success_rate:.0%}) - needs improvement")
        
        # Selector insights
        if profile.known_selectors:
            field_count = len(profile.known_selectors)
            insights.append(f"Learned {field_count} field selectors")
        
        # OTP timing insights
        if profile.otp_average_seconds:
            insights.append(f"Average OTP arrival: {profile.otp_average_seconds}s")
        
        # Anti-bot insights
        if profile.anti_bot_mechanisms:
            mechanisms = ", ".join(profile.anti_bot_mechanisms)
            insights.append(f"Anti-bot detected: {mechanisms}")
        
        return insights
    
    def _identify_improvements(
        self,
        domain: str,
        attempt_data: Dict[str, Any]
    ) -> List[str]:
        """Identify potential improvements."""
        improvements = []
        
        # Get domain profile
        profile = self.domain_intelligence.get_profile(domain)
        
        if not profile:
            return improvements
        
        # Success rate improvements
        if profile.success_rate < 0.7 and profile.total_attempts >= 3:
            improvements.append("Consider using AI for field detection")
            improvements.append("Review and update selector patterns")
        
        # Timing improvements
        if attempt_data.get("execution_time", 0) > 60:
            improvements.append("Optimize wait times and reduce delays")
        
        # Cost improvements
        if attempt_data.get("total_cost", 0) > 0.01:
            improvements.append("Consider using cheaper models for simple tasks")
        
        # Selector improvements
        if not profile.known_selectors or len(profile.known_selectors) < 2:
            improvements.append("Need to learn more field selectors")
        
        return improvements
    
    # ========================================================================
    # ANALYTICS
    # ========================================================================
    
    def get_domain_analytics(self, domain: str) -> Dict[str, Any]:
        """Get analytics for a specific domain."""
        profile = self.domain_intelligence.get_profile(domain)
        
        if not profile:
            return {}
        
        return {
            "domain": domain,
            "success_rate": profile.success_rate,
            "total_attempts": profile.total_attempts,
            "successful_attempts": profile.successful_attempts,
            "failed_attempts": profile.failed_attempts,
            "known_selectors": len(profile.known_selectors),
            "framework": profile.framework,
            "verification_type": profile.verification_type,
            "complexity": profile.complexity_score,
            "last_success": profile.last_success,
            "last_failure": profile.last_failure
        }
    
    def get_global_analytics(self) -> Dict[str, Any]:
        """Get global analytics across all domains."""
        stats = self.domain_intelligence.get_statistics()
        
        return {
            "total_domains": stats.get("total_domains", 0),
            "average_success_rate": stats.get("avg_success_rate", 0.0),
            "total_attempts": stats.get("total_attempts", 0),
            "total_successes": stats.get("total_successes", 0),
            "recent_attempts": stats.get("recent_attempts", 0)
        }
    
    def get_best_performing_domains(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get best performing domains."""
        # This would query domain_intelligence for top domains
        # Placeholder implementation
        return []
    
    def get_improvement_opportunities(self) -> List[Dict[str, Any]]:
        """Identify domains that need improvement."""
        # This would query domain_intelligence for low-performing domains
        # Placeholder implementation
        return []
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _create_error_result(
        self,
        start_time: float,
        error: str
    ) -> AgentResult:
        """Create error result."""
        execution_time = time.time() - start_time
        
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.ERROR,
            data={},
            confidence=0.0,
            execution_time=execution_time,
            cost=0.0,
            error=error
        )


# ============================================================================
# CLI FOR TESTING
# ============================================================================

if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table
    import asyncio
    from ai_model_router import ModelRouter
    from .base_agent import create_agent_context
    
    console = Console()
    
    console.print("\n[bold cyan]Learning Agent - Test[/bold cyan]\n")
    
    async def test():
        router = ModelRouter()
        db = DomainIntelligence()
        agent = LearningAgent(router, db)
        
        # Simulate successful attempt
        context = create_agent_context(
            workflow_id="test-123",
            url="https://example.com/signup"
        )
        
        context.metadata["attempt_results"] = {
            "success": True,
            "selectors_used": {
                "email": "input[name='email']",
                "password": "input[type='password']"
            },
            "execution_time": 45.2,
            "total_cost": 0.0023,
            "framework": "react",
            "verification_type": "otp",
            "otp_wait_time": 25
        }
        
        console.print("[cyan]Learning from successful attempt...[/cyan]")
        result = await agent.execute(context)
        
        console.print(f"\n[green]Learning Result:[/green]")
        console.print(f"  Status: {result.status.value}")
        console.print(f"  Profile Updated: {result.data.get('profile_updated')}")
        console.print(f"  Selectors Learned: {result.data.get('selectors_learned')}")
        
        if result.data.get("insights"):
            console.print(f"\n[cyan]Insights:[/cyan]")
            for insight in result.data["insights"]:
                console.print(f"  • {insight}")
        
        if result.data.get("improvements"):
            console.print(f"\n[yellow]Improvements:[/yellow]")
            for improvement in result.data["improvements"]:
                console.print(f"  • {improvement}")
        
        # Show analytics
        console.print(f"\n[cyan]Domain Analytics:[/cyan]")
        analytics = agent.get_domain_analytics("example.com")
        for key, value in analytics.items():
            console.print(f"  {key}: {value}")
    
    asyncio.run(test())
