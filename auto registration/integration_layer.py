#!/usr/bin/env python3
"""
Integration Layer
Bridge between multi-agent system and existing v4 registration system
Author: vinayakkumar9000
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import logging

from agents.coordinator_agent import CoordinatorAgent
from agents.base_agent import AgentContext, AgentStatus, create_agent_context
from ai_model_router import ModelRouter
from domain_intelligence import DomainIntelligence

# ============================================================================
# WORKFLOW STATE
# ============================================================================

class WorkflowState(Enum):
    """Workflow execution states."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"

# ============================================================================
# INTEGRATION LAYER
# ============================================================================

class IntegrationLayer:
    """
    Integration Layer - Bridge between agents and v4 system.
    
    Responsibilities:
    - Execute agent workflows
    - Manage state transitions
    - Handle callbacks to v4 system
    - Coordinate between old and new systems
    - Provide unified interface
    """
    
    def __init__(
        self,
        model_router: ModelRouter,
        domain_intelligence: DomainIntelligence,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Integration Layer.
        
        Args:
            model_router: Model router instance
            domain_intelligence: Domain intelligence database
            logger: Optional logger instance
        """
        self.model_router = model_router
        self.domain_intelligence = domain_intelligence
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize coordinator
        self.coordinator = CoordinatorAgent(
            model_router=model_router,
            domain_intelligence=domain_intelligence,
            logger=self.logger
        )
        
        # Active workflows
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        
        # Callbacks for v4 system
        self.callbacks: Dict[str, List[Callable]] = {
            "on_start": [],
            "on_progress": [],
            "on_success": [],
            "on_failure": [],
            "on_complete": []
        }
    
    # ========================================================================
    # WORKFLOW EXECUTION
    # ========================================================================
    
    async def execute_registration(
        self,
        url: str,
        email: Optional[str] = None,
        identity_data: Optional[Dict[str, Any]] = None,
        budget: float = 0.01,
        timeout: int = 180
    ) -> Dict[str, Any]:
        """
        Execute registration workflow using multi-agent system.
        
        Args:
            url: Registration URL
            email: Optional pre-generated email
            identity_data: Optional identity data
            budget: Maximum budget for AI calls
            timeout: Maximum execution time in seconds
        
        Returns:
            Registration result dictionary
        """
        workflow_id = self._generate_workflow_id()
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting registration workflow {workflow_id} for {url}")
            
            # Create workflow state
            workflow_state = {
                "id": workflow_id,
                "url": url,
                "state": WorkflowState.RUNNING,
                "start_time": start_time,
                "budget": budget,
                "budget_used": 0.0,
                "steps_completed": [],
                "current_step": None
            }
            
            self.active_workflows[workflow_id] = workflow_state
            
            # Trigger on_start callbacks
            await self._trigger_callbacks("on_start", workflow_state)
            
            # Create agent context
            context = create_agent_context(
                workflow_id=workflow_id,
                url=url,
                budget_remaining=budget
            )
            
            # Add identity data if provided
            if identity_data:
                context.metadata["identity_data"] = identity_data
            
            if email:
                context.metadata["email"] = email
            
            # Execute coordinator
            result = await asyncio.wait_for(
                self.coordinator.execute(context),
                timeout=timeout
            )
            
            # Update workflow state
            workflow_state["budget_used"] = result.cost
            workflow_state["execution_time"] = time.time() - start_time
            
            if result.status == AgentStatus.SUCCESS:
                workflow_state["state"] = WorkflowState.SUCCESS
                await self._trigger_callbacks("on_success", workflow_state)
            elif result.status == AgentStatus.PARTIAL:
                workflow_state["state"] = WorkflowState.PARTIAL
            else:
                workflow_state["state"] = WorkflowState.FAILED
                await self._trigger_callbacks("on_failure", workflow_state)
            
            # Trigger on_complete callbacks
            await self._trigger_callbacks("on_complete", workflow_state)
            
            # Convert to v4-compatible format
            return self._convert_to_v4_format(result, workflow_state)
            
        except asyncio.TimeoutError:
            self.logger.error(f"Workflow {workflow_id} timed out after {timeout}s")
            workflow_state["state"] = WorkflowState.FAILED
            workflow_state["error"] = "Timeout"
            await self._trigger_callbacks("on_failure", workflow_state)
            
            return {
                "success": False,
                "error": "Workflow timeout",
                "workflow_id": workflow_id,
                "execution_time": time.time() - start_time
            }
            
        except Exception as e:
            self.logger.error(f"Workflow {workflow_id} error: {str(e)}")
            workflow_state["state"] = WorkflowState.FAILED
            workflow_state["error"] = str(e)
            await self._trigger_callbacks("on_failure", workflow_state)
            
            return {
                "success": False,
                "error": str(e),
                "workflow_id": workflow_id,
                "execution_time": time.time() - start_time
            }
        
        finally:
            # Cleanup
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
    
    # ========================================================================
    # V4 COMPATIBILITY
    # ========================================================================
    
    def _convert_to_v4_format(
        self,
        agent_result: Any,
        workflow_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert agent result to v4-compatible format."""
        return {
            "success": agent_result.status == AgentStatus.SUCCESS,
            "workflow_id": workflow_state["id"],
            "url": workflow_state["url"],
            "execution_time": workflow_state.get("execution_time", 0),
            "cost": workflow_state.get("budget_used", 0),
            "confidence": agent_result.confidence,
            "data": agent_result.data,
            "steps_completed": workflow_state.get("steps_completed", []),
            "error": agent_result.error if hasattr(agent_result, "error") else None
        }
    
    # ========================================================================
    # CALLBACK MANAGEMENT
    # ========================================================================
    
    def register_callback(
        self,
        event: str,
        callback: Callable
    ) -> None:
        """
        Register callback for workflow events.
        
        Args:
            event: Event name (on_start, on_progress, on_success, on_failure, on_complete)
            callback: Callback function
        """
        if event in self.callbacks:
            self.callbacks[event].append(callback)
        else:
            self.logger.warning(f"Unknown event type: {event}")
    
    async def _trigger_callbacks(
        self,
        event: str,
        workflow_state: Dict[str, Any]
    ) -> None:
        """Trigger callbacks for event."""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(workflow_state)
                    else:
                        callback(workflow_state)
                except Exception as e:
                    self.logger.error(f"Callback error for {event}: {str(e)}")
    
    # ========================================================================
    # WORKFLOW MANAGEMENT
    # ========================================================================
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of active workflow."""
        return self.active_workflows.get(workflow_id)
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel active workflow."""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id]["state"] = WorkflowState.CANCELLED
            self.logger.info(f"Cancelled workflow {workflow_id}")
            return True
        return False
    
    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get all active workflows."""
        return list(self.active_workflows.values())
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _generate_workflow_id(self) -> str:
        """Generate unique workflow ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"workflow_{timestamp}_{id(self) % 10000}"


# ============================================================================
# V4 BRIDGE FUNCTIONS
# ============================================================================

class V4Bridge:
    """
    Bridge functions for backward compatibility with v4 system.
    """
    
    def __init__(self, integration_layer: IntegrationLayer):
        """Initialize V4 Bridge."""
        self.integration = integration_layer
    
    async def register_account(
        self,
        url: str,
        email: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        V4-compatible registration function.
        
        Args:
            url: Registration URL
            email: Optional email
            password: Optional password
            **kwargs: Additional parameters
        
        Returns:
            Registration result
        """
        identity_data = {}
        
        if email:
            identity_data["email"] = email
        if password:
            identity_data["password"] = password
        
        # Add any additional fields
        for key, value in kwargs.items():
            identity_data[key] = value
        
        return await self.integration.execute_registration(
            url=url,
            identity_data=identity_data
        )
    
    def get_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow status (v4-compatible)."""
        return self.integration.get_workflow_status(workflow_id)


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_integration_layer(
    config_path: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> IntegrationLayer:
    """
    Factory function to create integration layer.
    
    Args:
        config_path: Optional path to config file
        logger: Optional logger instance
    
    Returns:
        IntegrationLayer instance
    """
    # Initialize components
    from pathlib import Path
    config_file = Path(config_path) if config_path else None
    model_router = ModelRouter(config_file=config_file)
    domain_intelligence = DomainIntelligence()
    
    return IntegrationLayer(
        model_router=model_router,
        domain_intelligence=domain_intelligence,
        logger=logger
    )


def create_v4_bridge(
    config_path: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> V4Bridge:
    """
    Factory function to create v4 bridge.
    
    Args:
        config_path: Optional path to config file
        logger: Optional logger instance
    
    Returns:
        V4Bridge instance
    """
    integration = create_integration_layer(config_path, logger)
    return V4Bridge(integration)


# ============================================================================
# CLI FOR TESTING
# ============================================================================

if __name__ == "__main__":
    from rich.console import Console
    import asyncio
    
    console = Console()
    
    console.print("\n[bold cyan]Integration Layer - Test[/bold cyan]\n")
    
    async def test():
        # Create integration layer
        integration = create_integration_layer()
        
        # Register callbacks
        def on_start(state):
            console.print(f"[cyan]Started:[/cyan] {state['id']}")
        
        def on_success(state):
            console.print(f"[green]Success:[/green] {state['id']}")
        
        def on_failure(state):
            console.print(f"[red]Failed:[/red] {state['id']}")
        
        integration.register_callback("on_start", on_start)
        integration.register_callback("on_success", on_success)
        integration.register_callback("on_failure", on_failure)
        
        # Test registration
        console.print("[cyan]Testing registration workflow...[/cyan]")
        
        result = await integration.execute_registration(
            url="https://example.com/signup",
            budget=0.01,
            timeout=60
        )
        
        console.print(f"\n[green]Result:[/green]")
        console.print(f"  Success: {result.get('success')}")
        console.print(f"  Workflow ID: {result.get('workflow_id')}")
        console.print(f"  Execution Time: {result.get('execution_time', 0):.2f}s")
        console.print(f"  Cost: ${result.get('cost', 0):.6f}")
        console.print(f"  Confidence: {result.get('confidence', 0):.2f}")
        
        # Test V4 bridge
        console.print(f"\n[cyan]Testing V4 Bridge...[/cyan]")
        bridge = V4Bridge(integration)
        
        result = await bridge.register_account(
            url="https://example.com/signup",
            email="test@example.com"
        )
        
        console.print(f"  Success: {result.get('success')}")
        console.print(f"  Workflow ID: {result.get('workflow_id')}")
    
    asyncio.run(test())


# ============================================================================
# BACKWARD COMPATIBILITY WRAPPER
# ============================================================================

class UnifiedFormFiller:
    """
    Backward compatibility wrapper for v4 script.
    Bridges old deterministic flow with new multi-agent system.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize unified form filler.
        
        Args:
            config_path: Optional path to config file
        """
        self.config_path = config_path
        self.integration = None
    
    async def fill_form(self, page, url: str, identity_data: dict) -> dict:
        """
        Fill form using multi-agent system.
        
        Args:
            page: Playwright page object
            url: Target URL
            identity_data: User identity data
        
        Returns:
            Result dictionary with success status
        """
        # Lazy initialization
        if self.integration is None:
            self.integration = create_integration_layer(
                config_path=self.config_path
            )
        
        # Execute registration using multi-agent system
        result = await self.integration.execute_registration(
            url=url,
            identity_data=identity_data
        )
        
        return result
    
    def get_stats(self) -> dict:
        """Get usage statistics."""
        if self.integration:
            return self.integration.get_stats()
        return {}
