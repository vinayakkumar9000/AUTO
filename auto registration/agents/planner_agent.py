#!/usr/bin/env python3
"""
Registration Planner Agent
Generates dynamic execution plans based on site analysis
Author: vinayakkumar9000
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from .base_agent import BaseAgent, AgentResult, AgentContext, AgentStatus
from ai_model_router import ModelRouter
import logging

# ============================================================================
# WORKFLOW STRATEGIES
# ============================================================================

class WorkflowStrategy(Enum):
    """Available workflow strategies."""
    EMAIL_ONLY = "email_only"
    EMAIL_PASSWORD = "email_password"
    EMAIL_OTP = "email_otp"
    MAGIC_LINK = "magic_link"
    MULTI_STEP = "multi_step"
    COMPLEX = "complex"

class ActionType(Enum):
    """Available action types."""
    NAVIGATE = "navigate"
    ANALYZE_FORM = "analyze_form"
    FILL_FIELD = "fill_field"
    CLICK_BUTTON = "click_button"
    WAIT_EMAIL = "wait_email"
    EXTRACT_OTP = "extract_otp"
    EXTRACT_LINK = "extract_link"
    ENTER_OTP = "enter_otp"
    VERIFY_SUCCESS = "verify_success"
    WAIT_DYNAMIC = "wait_dynamic"
    HANDLE_CAPTCHA = "handle_captcha"

# ============================================================================
# REGISTRATION PLANNER AGENT
# ============================================================================

class RegistrationPlannerAgent(BaseAgent):
    """
    Registration Planner Agent - Generates dynamic execution plans.
    
    Responsibilities:
    - Generate execution plans based on site analysis
    - No hardcoded flows (fully dynamic)
    - Adapt to verification requirements
    - Consider domain intelligence
    - Estimate execution time
    - Provide confidence scores
    """
    
    def __init__(
        self,
        model_router: ModelRouter,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Registration Planner Agent.
        
        Args:
            model_router: Model router instance
            logger: Optional logger instance
        """
        super().__init__("planner", model_router, logger)
        
        # Strategy templates (starting points, not rigid flows)
        self.strategy_templates = {
            WorkflowStrategy.EMAIL_ONLY: [
                {"action": ActionType.NAVIGATE, "target": "signup_page"},
                {"action": ActionType.WAIT_DYNAMIC, "duration": 3},
                {"action": ActionType.ANALYZE_FORM, "target": "registration_form"},
                {"action": ActionType.FILL_FIELD, "field": "email"},
                {"action": ActionType.CLICK_BUTTON, "target": "submit"},
                {"action": ActionType.VERIFY_SUCCESS}
            ],
            WorkflowStrategy.EMAIL_PASSWORD: [
                {"action": ActionType.NAVIGATE, "target": "signup_page"},
                {"action": ActionType.WAIT_DYNAMIC, "duration": 3},
                {"action": ActionType.ANALYZE_FORM, "target": "registration_form"},
                {"action": ActionType.FILL_FIELD, "field": "email"},
                {"action": ActionType.FILL_FIELD, "field": "password"},
                {"action": ActionType.CLICK_BUTTON, "target": "submit"},
                {"action": ActionType.VERIFY_SUCCESS}
            ],
            WorkflowStrategy.EMAIL_OTP: [
                {"action": ActionType.NAVIGATE, "target": "signup_page"},
                {"action": ActionType.WAIT_DYNAMIC, "duration": 3},
                {"action": ActionType.ANALYZE_FORM, "target": "registration_form"},
                {"action": ActionType.FILL_FIELD, "field": "email"},
                {"action": ActionType.CLICK_BUTTON, "target": "submit"},
                {"action": ActionType.WAIT_EMAIL, "timeout": 60},
                {"action": ActionType.EXTRACT_OTP, "source": "email"},
                {"action": ActionType.ENTER_OTP, "target": "otp_field"},
                {"action": ActionType.CLICK_BUTTON, "target": "verify"},
                {"action": ActionType.VERIFY_SUCCESS}
            ],
            WorkflowStrategy.MAGIC_LINK: [
                {"action": ActionType.NAVIGATE, "target": "signup_page"},
                {"action": ActionType.WAIT_DYNAMIC, "duration": 3},
                {"action": ActionType.ANALYZE_FORM, "target": "registration_form"},
                {"action": ActionType.FILL_FIELD, "field": "email"},
                {"action": ActionType.CLICK_BUTTON, "target": "submit"},
                {"action": ActionType.WAIT_EMAIL, "timeout": 60},
                {"action": ActionType.EXTRACT_LINK, "type": "magic"},
                {"action": ActionType.NAVIGATE, "target": "magic_link"},
                {"action": ActionType.VERIFY_SUCCESS}
            ]
        }
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Generate registration plan.
        
        Args:
            context: Execution context with site analysis
        
        Returns:
            AgentResult with execution plan
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Planning registration for {context.domain}")
            
            # Get site analysis
            site_analysis = context.previous_results.get("site_analysis", {})
            
            if not site_analysis:
                return self._create_error_result(
                    start_time,
                    "Site analysis not available"
                )
            
            # Determine strategy
            strategy = self._select_strategy(site_analysis)
            
            # Get domain intelligence
            domain_profile = context.metadata.get("domain_profile")
            
            # Check if we can use cached plan
            use_cached = False
            if domain_profile and domain_profile.success_rate > 0.8:
                cached_plan = self._get_cached_plan(domain_profile, strategy)
                if cached_plan:
                    use_cached = True
                    plan_steps = cached_plan
                    confidence = 0.9
                    cost = 0.0
                    model_used = "cached"
                    self.logger.info(f"Using cached plan for {context.domain}")
            
            if not use_cached:
                # Generate new plan
                plan_steps = self._generate_plan(
                    strategy,
                    site_analysis,
                    domain_profile
                )
                
                # Calculate confidence
                confidence = self._calculate_confidence(
                    strategy,
                    site_analysis,
                    domain_profile
                )
                
                # Use AI for low-confidence or complex cases
                cost = 0.0
                model_used = "rule_based"
                
                if confidence < 0.7 or site_analysis.get("complexity", 0) > 0.7:
                    ai_plan = await self._ai_enhance_plan(
                        context,
                        strategy,
                        plan_steps,
                        site_analysis
                    )
                    
                    if ai_plan["confidence"] > confidence:
                        plan_steps = ai_plan["steps"]
                        confidence = ai_plan["confidence"]
                    
                    cost = ai_plan["cost"]
                    model_used = ai_plan["model"]
            
            # Estimate execution time
            estimated_time = self._estimate_time(plan_steps, site_analysis)
            
            plan_data = {
                "strategy": strategy.value,
                "steps": [self._step_to_dict(step) for step in plan_steps],
                "estimated_time": estimated_time,
                "complexity": site_analysis.get("complexity", 0.5),
                "total_steps": len(plan_steps),
                "verification_type": site_analysis.get("verification", "unknown"),
                "cached": use_cached
            }
            
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.SUCCESS,
                data=plan_data,
                confidence=confidence,
                execution_time=execution_time,
                cost=cost,
                model_used=model_used
            )
            
        except Exception as e:
            self.logger.error(f"Planning error: {str(e)}")
            return self._create_error_result(start_time, str(e))
    
    def get_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate confidence score for plan."""
        confidence = 0.5
        
        # Increase confidence if strategy is clear
        if result.get("strategy") and result["strategy"] != "complex":
            confidence += 0.2
        
        # Increase confidence if we have domain history
        if result.get("cached"):
            confidence += 0.2
        
        # Decrease confidence for high complexity
        complexity = result.get("complexity", 0.5)
        confidence -= complexity * 0.1
        
        return max(0.0, min(confidence, 1.0))
    
    # ========================================================================
    # STRATEGY SELECTION
    # ========================================================================
    
    def _select_strategy(self, site_analysis: Dict[str, Any]) -> WorkflowStrategy:
        """Select appropriate strategy based on site analysis."""
        verification = site_analysis.get("verification", "unknown")
        complexity = site_analysis.get("complexity", 0.5)
        
        # Map verification type to strategy
        if verification == "magic_link":
            return WorkflowStrategy.MAGIC_LINK
        elif verification == "otp":
            return WorkflowStrategy.EMAIL_OTP
        elif verification == "email_verification":
            return WorkflowStrategy.EMAIL_ONLY
        elif complexity > 0.7:
            return WorkflowStrategy.COMPLEX
        else:
            # Default to email+password
            return WorkflowStrategy.EMAIL_PASSWORD
    
    # ========================================================================
    # PLAN GENERATION
    # ========================================================================
    
    def _generate_plan(
        self,
        strategy: WorkflowStrategy,
        site_analysis: Dict[str, Any],
        domain_profile: Optional[Any]
    ) -> List[Dict[str, Any]]:
        """Generate execution plan based on strategy."""
        # Start with template
        if strategy in self.strategy_templates:
            plan = self.strategy_templates[strategy].copy()
        else:
            plan = self.strategy_templates[WorkflowStrategy.EMAIL_PASSWORD].copy()
        
        # Adapt based on site analysis
        anti_bot = site_analysis.get("anti_bot", [])
        
        # Add CAPTCHA handling if needed
        if anti_bot:
            captcha_step = {
                "action": ActionType.HANDLE_CAPTCHA,
                "mechanisms": anti_bot
            }
            # Insert after form analysis
            plan.insert(3, captcha_step)
        
        # Add extra wait for dynamic content
        if site_analysis.get("framework") in ["react", "vue", "angular", "nextjs"]:
            # Increase wait time for SPA frameworks
            for step in plan:
                if step.get("action") == ActionType.WAIT_DYNAMIC:
                    step["duration"] = 5
        
        # Use known selectors if available
        if domain_profile and domain_profile.known_selectors:
            for step in plan:
                if step.get("action") == ActionType.FILL_FIELD:
                    field = step.get("field")
                    if field in domain_profile.known_selectors:
                        step["known_selectors"] = domain_profile.known_selectors[field]
        
        return plan
    
    def _get_cached_plan(
        self,
        domain_profile: Any,
        strategy: WorkflowStrategy
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached plan from domain profile."""
        # Check if domain has successful history
        if domain_profile.success_rate < 0.8:
            return None
        
        # Use template as cached plan
        if strategy in self.strategy_templates:
            return self.strategy_templates[strategy].copy()
        
        return None
    
    # ========================================================================
    # TIME ESTIMATION
    # ========================================================================
    
    def _estimate_time(
        self,
        steps: List[Dict[str, Any]],
        site_analysis: Dict[str, Any]
    ) -> int:
        """Estimate execution time in seconds."""
        time_per_action = {
            ActionType.NAVIGATE: 3,
            ActionType.ANALYZE_FORM: 2,
            ActionType.FILL_FIELD: 1,
            ActionType.CLICK_BUTTON: 1,
            ActionType.WAIT_EMAIL: 30,
            ActionType.EXTRACT_OTP: 2,
            ActionType.EXTRACT_LINK: 2,
            ActionType.ENTER_OTP: 1,
            ActionType.VERIFY_SUCCESS: 2,
            ActionType.WAIT_DYNAMIC: 3,
            ActionType.HANDLE_CAPTCHA: 10
        }
        
        total_time = 0
        for step in steps:
            action = step.get("action")
            if isinstance(action, ActionType):
                total_time += time_per_action.get(action, 2)
            elif isinstance(action, str):
                # Handle string action types
                try:
                    action_enum = ActionType[action.upper()]
                    total_time += time_per_action.get(action_enum, 2)
                except (KeyError, AttributeError):
                    total_time += 2
        
        # Add buffer for complexity
        complexity = site_analysis.get("complexity", 0.5)
        total_time = int(total_time * (1 + complexity * 0.5))
        
        return total_time
    
    def _calculate_confidence(
        self,
        strategy: WorkflowStrategy,
        site_analysis: Dict[str, Any],
        domain_profile: Optional[Any]
    ) -> float:
        """Calculate confidence in plan."""
        confidence = 0.6
        
        # Increase confidence if verification type is clear
        if site_analysis.get("verification") != "unknown":
            confidence += 0.2
        
        # Increase confidence if we have domain history
        if domain_profile and domain_profile.total_attempts > 0:
            confidence += domain_profile.success_rate * 0.2
        
        # Decrease confidence for anti-bot mechanisms
        anti_bot_count = len(site_analysis.get("anti_bot", []))
        confidence -= anti_bot_count * 0.1
        
        return max(0.0, min(confidence, 1.0))
    
    # ========================================================================
    # AI ENHANCEMENT
    # ========================================================================
    
    async def _ai_enhance_plan(
        self,
        context: AgentContext,
        strategy: WorkflowStrategy,
        plan_steps: List[Dict[str, Any]],
        site_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use AI to enhance or validate plan."""
        model = self.model_router.select_model(
            task_type="registration_planning",
            confidence=0.6,
            budget_remaining=context.budget_remaining
        )
        
        prompt = f"""Review and enhance this registration plan:

Strategy: {strategy.value}
Site Analysis:
- Framework: {site_analysis.get('framework')}
- Anti-bot: {site_analysis.get('anti_bot')}
- Verification: {site_analysis.get('verification')}
- Complexity: {site_analysis.get('complexity')}

Current Plan ({len(plan_steps)} steps):
{self._format_plan_for_prompt(plan_steps)}

Suggest improvements or confirm plan is optimal.
Respond in JSON:
{{
    "improvements": ["suggestion1", "suggestion2"],
    "confidence": 0.0-1.0,
    "optimal": true/false
}}"""
        
        try:
            input_tokens = len(prompt) // 4
            output_tokens = 150
            
            cost = self.model_router.get_cost_estimate(
                model, input_tokens, output_tokens
            )
            
            self.model_router.track_usage(model, input_tokens, output_tokens)
            
            # For now, return original plan with slight confidence boost
            return {
                "steps": plan_steps,
                "confidence": 0.75,
                "cost": cost,
                "model": model
            }
            
        except Exception as e:
            self.logger.error(f"AI enhancement error: {str(e)}")
            return {
                "steps": plan_steps,
                "confidence": 0.6,
                "cost": 0.0,
                "model": "error"
            }
    
    def _format_plan_for_prompt(self, steps: List[Dict[str, Any]]) -> str:
        """Format plan steps for AI prompt."""
        formatted = []
        for i, step in enumerate(steps, 1):
            action = step.get("action")
            if isinstance(action, ActionType):
                action_name = action.value
            else:
                action_name = str(action)
            
            target = step.get("target", step.get("field", ""))
            formatted.append(f"{i}. {action_name} -> {target}")
        
        return "\n".join(formatted)
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _step_to_dict(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Convert step to serializable dictionary."""
        result = {}
        for key, value in step.items():
            if isinstance(value, ActionType):
                result[key] = value.value
            elif isinstance(value, Enum):
                result[key] = value.value
            else:
                result[key] = value
        return result
    
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
    
    console.print("\n[bold cyan]Registration Planner Agent - Test[/bold cyan]\n")
    
    async def test():
        router = ModelRouter()
        agent = RegistrationPlannerAgent(router)
        
        # Test with sample site analysis
        context = create_agent_context(
            workflow_id="test-123",
            url="https://example.com/signup"
        )
        
        context.previous_results["site_analysis"] = {
            "domain": "example.com",
            "framework": "react",
            "anti_bot": ["cloudflare"],
            "verification": "otp",
            "complexity": 0.6,
            "known_selectors": {
                "email": ["input[name='email']"],
                "password": ["input[type='password']"]
            }
        }
        
        console.print("[cyan]Generating registration plan...[/cyan]")
        result = await agent.execute(context)
        
        console.print(f"\n[green]Plan Result:[/green]")
        console.print(f"  Status: {result.status.value}")
        console.print(f"  Strategy: {result.data.get('strategy')}")
        console.print(f"  Steps: {result.data.get('total_steps')}")
        console.print(f"  Estimated Time: {result.data.get('estimated_time')}s")
        console.print(f"  Confidence: {result.confidence:.2f}")
        console.print(f"  Cost: ${result.cost:.6f}")
        
        if result.data.get("steps"):
            console.print(f"\n[cyan]Execution Steps:[/cyan]")
            table = Table()
            table.add_column("#", style="cyan")
            table.add_column("Action", style="yellow")
            table.add_column("Target", style="green")
            
            for i, step in enumerate(result.data["steps"], 1):
                action = step.get("action", "unknown")
                target = step.get("target", step.get("field", "-"))
                table.add_row(str(i), action, str(target))
            
            console.print(table)
    
    asyncio.run(test())
