#!/usr/bin/env python3
"""
Coordinator Agent
Main orchestrator for the multi-agent registration system
Author: vinayakkumar9000
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

from .base_agent import BaseAgent, AgentResult, AgentContext, AgentStatus
from ai_model_router import ModelRouter
from domain_intelligence import DomainIntelligence, RegistrationAttempt
import logging

# ============================================================================
# WORKFLOW CONFIGURATION
# ============================================================================

class WorkflowStrategy:
    """Available workflow strategies."""
    EMAIL_ONLY = "email_only"
    EMAIL_OTP = "email_otp"
    MAGIC_LINK = "magic_link"
    MULTI_STEP = "multi_step"
    COMPLEX = "complex"

# ============================================================================
# COORDINATOR AGENT
# ============================================================================

class CoordinatorAgent(BaseAgent):
    """
    Coordinator Agent - Main orchestrator for registration workflows.
    
    Responsibilities:
    - Entry point for all registrations
    - Orchestrate agent execution
    - Select models dynamically
    - Control budget
    - Aggregate results
    """
    
    def __init__(
        self,
        model_router: ModelRouter,
        domain_intelligence: DomainIntelligence,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Coordinator Agent.
        
        Args:
            model_router: Model router instance
            domain_intelligence: Domain intelligence database
            logger: Optional logger instance
        """
        super().__init__("coordinator", model_router, logger)
        self.domain_intelligence = domain_intelligence
        self.active_workflows = {}
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute coordinated registration workflow.
        
        Args:
            context: Execution context
        
        Returns:
            AgentResult with workflow outcome
        """
        start_time = time.time()
        workflow_id = context.workflow_id
        
        try:
            self.logger.info(f"Starting workflow {workflow_id} for {context.domain}")
            
            # Store workflow
            self.active_workflows[workflow_id] = {
                "status": "running",
                "start_time": datetime.utcnow().isoformat(),
                "domain": context.domain,
                "url": context.url
            }
            
            # Get domain profile for intelligence
            domain_profile = self.domain_intelligence.get_or_create_profile(context.domain)
            context.metadata["domain_profile"] = domain_profile
            
            # Phase 1: Site Analysis
            self.logger.info(f"[{workflow_id}] Phase 1: Site Analysis")
            site_analysis = await self._analyze_site(context)
            
            if site_analysis.status != AgentStatus.SUCCESS:
                return self._create_failure_result(
                    workflow_id, start_time, "Site analysis failed",
                    site_analysis.error
                )
            
            context.previous_results["site_analysis"] = site_analysis.data
            
            # Phase 2: Registration Planning
            self.logger.info(f"[{workflow_id}] Phase 2: Registration Planning")
            plan = await self._create_plan(context, site_analysis.data)
            
            if plan.status != AgentStatus.SUCCESS:
                return self._create_failure_result(
                    workflow_id, start_time, "Planning failed",
                    plan.error
                )
            
            context.previous_results["plan"] = plan.data
            
            # Phase 3: Execute Plan
            self.logger.info(f"[{workflow_id}] Phase 3: Executing Plan")
            execution_result = await self._execute_plan(context, plan.data)
            
            if execution_result.status != AgentStatus.SUCCESS:
                # Attempt recovery
                self.logger.warning(f"[{workflow_id}] Execution failed, attempting recovery")
                recovery_result = await self._attempt_recovery(
                    context, execution_result
                )
                
                if recovery_result.status == AgentStatus.SUCCESS:
                    execution_result = recovery_result
                else:
                    return self._create_failure_result(
                        workflow_id, start_time,
                        "Execution and recovery failed",
                        execution_result.error
                    )
            
            # Phase 4: Verification
            self.logger.info(f"[{workflow_id}] Phase 4: Verification")
            verification = await self._verify_success(context, execution_result.data)
            
            # Calculate total cost and time
            total_cost = (
                site_analysis.cost +
                plan.cost +
                execution_result.cost +
                verification.cost
            )
            
            execution_time = time.time() - start_time
            
            # Record attempt
            self._record_attempt(
                context,
                verification.status == AgentStatus.SUCCESS,
                execution_time,
                total_cost,
                verification.data
            )
            
            # Update workflow status
            self.active_workflows[workflow_id]["status"] = "completed"
            self.active_workflows[workflow_id]["success"] = (
                verification.status == AgentStatus.SUCCESS
            )
            
            # Create result
            result_data = {
                "workflow_id": workflow_id,
                "domain": context.domain,
                "strategy": plan.data.get("strategy", "unknown"),
                "site_analysis": site_analysis.data,
                "plan": plan.data,
                "execution": execution_result.data,
                "verification": verification.data,
                "models_used": {
                    "site_analyzer": site_analysis.model_used,
                    "planner": plan.model_used,
                    "executor": execution_result.model_used,
                    "verifier": verification.model_used
                },
                "total_cost": total_cost,
                "execution_time": execution_time
            }
            
            confidence = self.get_confidence(result_data)
            
            return AgentResult(
                agent_name=self.name,
                status=verification.status,
                data=result_data,
                confidence=confidence,
                execution_time=execution_time,
                cost=total_cost,
                model_used="coordinator"
            )
            
        except Exception as e:
            self.logger.error(f"[{workflow_id}] Coordinator error: {str(e)}")
            return self._create_failure_result(
                workflow_id, start_time,
                "Coordinator exception",
                str(e)
            )
    
    def get_confidence(self, result: Dict[str, Any]) -> float:
        """
        Calculate confidence score for workflow result.
        
        Args:
            result: Workflow result data
        
        Returns:
            Confidence score (0.0 - 1.0)
        """
        verification = result.get("verification", {})
        verification_confidence = verification.get("confidence", 0.0)
        
        # Weight verification heavily
        base_confidence = verification_confidence * 0.7
        
        # Add bonus for successful execution
        if result.get("execution", {}).get("success", False):
            base_confidence += 0.2
        
        # Add bonus for known domain
        domain_profile = result.get("site_analysis", {}).get("domain_profile")
        if domain_profile and domain_profile.get("total_attempts", 0) > 0:
            success_rate = domain_profile.get("success_rate", 0.0)
            base_confidence += success_rate * 0.1
        
        return min(base_confidence, 1.0)
    
    # ========================================================================
    # WORKFLOW PHASES
    # ========================================================================
    
    async def _analyze_site(self, context: AgentContext) -> AgentResult:
        """
        Phase 1: Analyze target site.
        
        Returns:
            AgentResult with site analysis
        """
        # For now, return basic analysis
        # Will be replaced with SiteAnalyzerAgent
        
        domain_profile = context.metadata.get("domain_profile")
        
        analysis_data = {
            "domain": context.domain,
            "framework": domain_profile.framework if domain_profile else "unknown",
            "verification": domain_profile.verification_type if domain_profile else "unknown",
            "complexity": domain_profile.complexity_score if domain_profile else 0.5,
            "anti_bot": domain_profile.anti_bot_mechanisms if domain_profile else [],
            "known_selectors": domain_profile.known_selectors if domain_profile else {},
            "success_rate": domain_profile.success_rate if domain_profile else 0.0
        }
        
        return AgentResult(
            agent_name="site_analyzer",
            status=AgentStatus.SUCCESS,
            data=analysis_data,
            confidence=0.8,
            execution_time=0.1,
            cost=0.0,
            model_used="cached"
        )
    
    async def _create_plan(
        self,
        context: AgentContext,
        site_analysis: Dict[str, Any]
    ) -> AgentResult:
        """
        Phase 2: Create registration plan.
        
        Returns:
            AgentResult with execution plan
        """
        # Determine strategy based on site analysis
        verification = site_analysis.get("verification", "unknown")
        
        if verification == "magic_link":
            strategy = WorkflowStrategy.MAGIC_LINK
        elif verification == "otp":
            strategy = WorkflowStrategy.EMAIL_OTP
        elif verification == "email":
            strategy = WorkflowStrategy.EMAIL_ONLY
        else:
            strategy = WorkflowStrategy.MULTI_STEP
        
        # Create plan steps
        steps = self._generate_steps(strategy, site_analysis)
        
        plan_data = {
            "strategy": strategy,
            "steps": steps,
            "estimated_time": len(steps) * 10,
            "complexity": site_analysis.get("complexity", 0.5)
        }
        
        return AgentResult(
            agent_name="planner",
            status=AgentStatus.SUCCESS,
            data=plan_data,
            confidence=0.85,
            execution_time=0.2,
            cost=0.0,
            model_used="rule_based"
        )
    
    def _generate_steps(
        self,
        strategy: str,
        site_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate execution steps based on strategy."""
        base_steps = [
            {"action": "navigate", "target": "signup_page"},
            {"action": "analyze_form", "target": "registration_form"},
            {"action": "fill_fields", "target": "form_fields"},
            {"action": "submit_form", "target": "submit_button"}
        ]
        
        if strategy == WorkflowStrategy.EMAIL_OTP:
            base_steps.extend([
                {"action": "wait_email", "timeout": 60},
                {"action": "extract_otp", "source": "email"},
                {"action": "enter_otp", "target": "otp_field"},
                {"action": "submit_otp", "target": "verify_button"}
            ])
        elif strategy == WorkflowStrategy.MAGIC_LINK:
            base_steps.extend([
                {"action": "wait_email", "timeout": 60},
                {"action": "extract_link", "type": "magic"},
                {"action": "navigate", "target": "magic_link"}
            ])
        
        base_steps.append({"action": "verify_success"})
        
        return base_steps
    
    async def _execute_plan(
        self,
        context: AgentContext,
        plan: Dict[str, Any]
    ) -> AgentResult:
        """
        Phase 3: Execute registration plan.
        
        Returns:
            AgentResult with execution outcome
        """
        # Placeholder for actual execution
        # Will be replaced with proper agent execution
        
        execution_data = {
            "success": True,
            "steps_completed": len(plan.get("steps", [])),
            "fields_filled": {
                "email": "test@example.com",
                "password": "generated"
            },
            "verification_method": plan.get("strategy")
        }
        
        return AgentResult(
            agent_name="executor",
            status=AgentStatus.SUCCESS,
            data=execution_data,
            confidence=0.8,
            execution_time=30.0,
            cost=0.005,
            model_used="gpt-5.4-mini"
        )
    
    async def _verify_success(
        self,
        context: AgentContext,
        execution_data: Dict[str, Any]
    ) -> AgentResult:
        """
        Phase 4: Verify registration success.
        
        Returns:
            AgentResult with verification outcome
        """
        # Placeholder for actual verification
        # Will be replaced with VerificationAgent
        
        verification_data = {
            "success": execution_data.get("success", False),
            "method": "dashboard_check",
            "evidence": ["url_changed", "session_cookie"],
            "confidence": 0.9
        }
        
        status = AgentStatus.SUCCESS if verification_data["success"] else AgentStatus.FAILURE
        
        return AgentResult(
            agent_name="verifier",
            status=status,
            data=verification_data,
            confidence=verification_data["confidence"],
            execution_time=2.0,
            cost=0.001,
            model_used="gpt-5.4-mini"
        )
    
    async def _attempt_recovery(
        self,
        context: AgentContext,
        failed_result: AgentResult
    ) -> AgentResult:
        """
        Attempt to recover from failure.
        
        Returns:
            AgentResult with recovery outcome
        """
        self.logger.info(f"Attempting recovery for {context.workflow_id}")
        
        # Placeholder for RecoveryAgent
        # For now, return failure
        
        return AgentResult(
            agent_name="recovery",
            status=AgentStatus.FAILURE,
            data={"recovery_attempted": True, "success": False},
            confidence=0.0,
            execution_time=1.0,
            cost=0.0,
            error="Recovery not yet implemented"
        )
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _record_attempt(
        self,
        context: AgentContext,
        success: bool,
        execution_time: float,
        total_cost: float,
        verification_data: Dict[str, Any]
    ):
        """Record registration attempt in domain intelligence."""
        attempt = RegistrationAttempt(
            domain=context.domain,
            workflow_id=context.workflow_id,
            success=success,
            execution_time=execution_time,
            total_cost=total_cost,
            verification_method=verification_data.get("method"),
            fields_detected=context.previous_results.get("fields", {}),
            selectors_used=context.previous_results.get("selectors", {}),
            error_type=verification_data.get("error_type"),
            error_message=verification_data.get("error_message"),
            models_used=self._get_models_used(context)
        )
        
        self.domain_intelligence.record_attempt(attempt)
    
    def _get_models_used(self, context: AgentContext) -> List[str]:
        """Extract list of models used in workflow."""
        models = []
        for result in context.previous_results.values():
            if isinstance(result, dict) and "model_used" in result:
                model = result["model_used"]
                if model and model not in models:
                    models.append(model)
        return models
    
    def _create_failure_result(
        self,
        workflow_id: str,
        start_time: float,
        reason: str,
        error: Optional[str] = None
    ) -> AgentResult:
        """Create failure result."""
        execution_time = time.time() - start_time
        
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.FAILURE,
            data={
                "workflow_id": workflow_id,
                "reason": reason
            },
            confidence=0.0,
            execution_time=execution_time,
            cost=0.0,
            error=error
        )
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of active workflow."""
        return self.active_workflows.get(workflow_id)
    
    def list_active_workflows(self) -> List[str]:
        """List all active workflow IDs."""
        return [
            wf_id for wf_id, wf in self.active_workflows.items()
            if wf.get("status") == "running"
        ]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def run_registration(
    url: str,
    budget: float = 0.10,
    timeout: int = 300,
    model_router: Optional[ModelRouter] = None,
    domain_intelligence: Optional[DomainIntelligence] = None
) -> AgentResult:
    """
    Convenience function to run a registration workflow.
    
    Args:
        url: Target registration URL
        budget: Maximum budget in dollars
        timeout: Maximum time in seconds
        model_router: Optional model router instance
        domain_intelligence: Optional domain intelligence instance
    
    Returns:
        AgentResult with workflow outcome
    """
    from urllib.parse import urlparse
    from .base_agent import create_agent_context
    
    # Initialize components if not provided
    if model_router is None:
        model_router = ModelRouter()
    
    if domain_intelligence is None:
        domain_intelligence = DomainIntelligence()
    
    # Create coordinator
    coordinator = CoordinatorAgent(model_router, domain_intelligence)
    
    # Create context
    workflow_id = str(uuid.uuid4())
    context = create_agent_context(
        workflow_id=workflow_id,
        url=url,
        budget=budget,
        timeout=timeout
    )
    
    # Execute workflow
    result = await coordinator.execute_with_retry(context, max_attempts=2)
    
    return result


# ============================================================================
# CLI FOR TESTING
# ============================================================================

if __name__ == "__main__":
    from rich.console import Console
    import asyncio
    
    console = Console()
    
    console.print("\n[bold cyan]Coordinator Agent - Test[/bold cyan]\n")
    
    async def test():
        # Test registration workflow
        result = await run_registration(
            url="https://example.com/signup",
            budget=0.10,
            timeout=300
        )
        
        console.print(f"[cyan]Workflow Result:[/cyan]")
        console.print(f"  Status: {result.status.value}")
        console.print(f"  Confidence: {result.confidence:.2f}")
        console.print(f"  Time: {result.execution_time:.2f}s")
        console.print(f"  Cost: ${result.cost:.6f}")
        
        if result.data:
            console.print(f"\n[cyan]Workflow Details:[/cyan]")
            console.print(f"  Workflow ID: {result.data.get('workflow_id')}")
            console.print(f"  Strategy: {result.data.get('strategy')}")
            console.print(f"  Domain: {result.data.get('domain')}")
    
    asyncio.run(test())
