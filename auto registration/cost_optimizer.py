#!/usr/bin/env python3
"""
Cost Optimizer
Real-time cost tracking, budget enforcement, and optimization
Author: vinayakkumar9000
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

from ai_model_router import ModelRouter

# ============================================================================
# COST TRACKING
# ============================================================================

@dataclass
class CostEntry:
    """Single cost entry."""
    timestamp: datetime
    workflow_id: str
    agent_name: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    task_type: str

class BudgetStatus(Enum):
    """Budget status."""
    OK = "ok"
    WARNING = "warning"
    EXCEEDED = "exceeded"

# ============================================================================
# COST OPTIMIZER
# ============================================================================

class CostOptimizer:
    """
    Cost Optimizer - Real-time cost tracking and optimization.
    
    Responsibilities:
    - Track all AI costs in real-time
    - Enforce budget limits
    - Optimize model selection
    - Generate cost reports
    - Identify cost-saving opportunities
    - Alert on budget thresholds
    """
    
    def __init__(
        self,
        model_router: ModelRouter,
        default_budget: float = 0.01,
        warning_threshold: float = 0.8,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Cost Optimizer.
        
        Args:
            model_router: Model router instance
            default_budget: Default budget per workflow
            warning_threshold: Warning threshold (0.0-1.0)
            logger: Optional logger instance
        """
        self.model_router = model_router
        self.default_budget = default_budget
        self.warning_threshold = warning_threshold
        self.logger = logger or logging.getLogger(__name__)
        
        # Cost tracking
        self.cost_entries: List[CostEntry] = []
        self.workflow_costs: Dict[str, float] = {}
        self.workflow_budgets: Dict[str, float] = {}
        
        # Statistics
        self.total_cost = 0.0
        self.total_tokens = 0
        self.model_usage: Dict[str, int] = {}
        
        # Optimization settings
        self.cost_targets = {
            "registration": 0.0008,  # Target: $0.0008 per registration
            "form_analysis": 0.0002,
            "otp_extraction": 0.0001,
            "recovery": 0.0003
        }
    
    # ========================================================================
    # BUDGET MANAGEMENT
    # ========================================================================
    
    def set_workflow_budget(
        self,
        workflow_id: str,
        budget: float
    ) -> None:
        """Set budget for workflow."""
        self.workflow_budgets[workflow_id] = budget
        self.workflow_costs[workflow_id] = 0.0
        self.logger.info(f"Set budget for {workflow_id}: ${budget:.6f}")
    
    def get_remaining_budget(self, workflow_id: str) -> float:
        """Get remaining budget for workflow."""
        budget = self.workflow_budgets.get(workflow_id, self.default_budget)
        used = self.workflow_costs.get(workflow_id, 0.0)
        return max(0.0, budget - used)
    
    def get_budget_status(self, workflow_id: str) -> BudgetStatus:
        """Get budget status for workflow."""
        budget = self.workflow_budgets.get(workflow_id, self.default_budget)
        used = self.workflow_costs.get(workflow_id, 0.0)
        
        if used >= budget:
            return BudgetStatus.EXCEEDED
        elif used >= budget * self.warning_threshold:
            return BudgetStatus.WARNING
        else:
            return BudgetStatus.OK
    
    def check_budget(
        self,
        workflow_id: str,
        estimated_cost: float
    ) -> Tuple[bool, str]:
        """
        Check if operation is within budget.
        
        Args:
            workflow_id: Workflow ID
            estimated_cost: Estimated cost of operation
        
        Returns:
            Tuple of (allowed, reason)
        """
        remaining = self.get_remaining_budget(workflow_id)
        
        if estimated_cost > remaining:
            return False, f"Insufficient budget: ${remaining:.6f} remaining, ${estimated_cost:.6f} needed"
        
        return True, "OK"
    
    # ========================================================================
    # COST TRACKING
    # ========================================================================
    
    def track_cost(
        self,
        workflow_id: str,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        task_type: str = "unknown"
    ) -> None:
        """Track cost entry."""
        entry = CostEntry(
            timestamp=datetime.utcnow(),
            workflow_id=workflow_id,
            agent_name=agent_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            task_type=task_type
        )
        
        self.cost_entries.append(entry)
        
        # Update workflow cost
        if workflow_id not in self.workflow_costs:
            self.workflow_costs[workflow_id] = 0.0
        self.workflow_costs[workflow_id] += cost
        
        # Update totals
        self.total_cost += cost
        self.total_tokens += input_tokens + output_tokens
        
        # Update model usage
        if model not in self.model_usage:
            self.model_usage[model] = 0
        self.model_usage[model] += 1
        
        # Check budget status
        status = self.get_budget_status(workflow_id)
        if status == BudgetStatus.WARNING:
            self.logger.warning(
                f"Budget warning for {workflow_id}: "
                f"${self.workflow_costs[workflow_id]:.6f} / "
                f"${self.workflow_budgets.get(workflow_id, self.default_budget):.6f}"
            )
        elif status == BudgetStatus.EXCEEDED:
            self.logger.error(
                f"Budget exceeded for {workflow_id}: "
                f"${self.workflow_costs[workflow_id]:.6f} / "
                f"${self.workflow_budgets.get(workflow_id, self.default_budget):.6f}"
            )
    
    # ========================================================================
    # OPTIMIZATION
    # ========================================================================
    
    def suggest_model(
        self,
        task_type: str,
        workflow_id: str,
        confidence_required: float = 0.7
    ) -> str:
        """
        Suggest optimal model for task.
        
        Args:
            task_type: Type of task
            workflow_id: Workflow ID
            confidence_required: Required confidence level
        
        Returns:
            Suggested model name
        """
        remaining_budget = self.get_remaining_budget(workflow_id)
        
        # Use model router with budget constraint
        model = self.model_router.select_model(
            task_type=task_type,
            confidence=confidence_required,
            budget_remaining=remaining_budget
        )
        
        return model
    
    def get_cost_saving_opportunities(self) -> List[Dict[str, Any]]:
        """Identify cost-saving opportunities."""
        opportunities = []
        
        # Analyze model usage
        if self.cost_entries:
            # Check for expensive models on simple tasks
            for entry in self.cost_entries[-100:]:  # Last 100 entries
                if entry.task_type in ["form_analysis", "otp_extraction"]:
                    if entry.cost > self.cost_targets.get(entry.task_type, 0.001):
                        opportunities.append({
                            "type": "expensive_model",
                            "task": entry.task_type,
                            "model": entry.model,
                            "cost": entry.cost,
                            "suggestion": "Consider using cheaper model for simple tasks"
                        })
        
        # Check for repeated failures (wasted cost)
        workflow_failures = {}
        for entry in self.cost_entries:
            wf_id = entry.workflow_id
            if wf_id not in workflow_failures:
                workflow_failures[wf_id] = []
            workflow_failures[wf_id].append(entry)
        
        for wf_id, entries in workflow_failures.items():
            if len(entries) > 5:  # Many attempts
                total_cost = sum(e.cost for e in entries)
                if total_cost > 0.01:
                    opportunities.append({
                        "type": "repeated_failures",
                        "workflow": wf_id,
                        "attempts": len(entries),
                        "cost": total_cost,
                        "suggestion": "Improve success rate to reduce wasted costs"
                    })
        
        return opportunities
    
    # ========================================================================
    # REPORTING
    # ========================================================================
    
    def get_workflow_report(self, workflow_id: str) -> Dict[str, Any]:
        """Get cost report for workflow."""
        entries = [e for e in self.cost_entries if e.workflow_id == workflow_id]
        
        if not entries:
            return {}
        
        total_cost = sum(e.cost for e in entries)
        total_tokens = sum(e.input_tokens + e.output_tokens for e in entries)
        
        # Group by agent
        agent_costs = {}
        for entry in entries:
            if entry.agent_name not in agent_costs:
                agent_costs[entry.agent_name] = 0.0
            agent_costs[entry.agent_name] += entry.cost
        
        # Group by model
        model_costs = {}
        for entry in entries:
            if entry.model not in model_costs:
                model_costs[entry.model] = 0.0
            model_costs[entry.model] += entry.cost
        
        return {
            "workflow_id": workflow_id,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "total_calls": len(entries),
            "budget": self.workflow_budgets.get(workflow_id, self.default_budget),
            "remaining": self.get_remaining_budget(workflow_id),
            "status": self.get_budget_status(workflow_id).value,
            "agent_costs": agent_costs,
            "model_costs": model_costs,
            "entries": len(entries)
        }
    
    def get_global_report(
        self,
        time_range: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Get global cost report."""
        entries = self.cost_entries
        
        # Filter by time range
        if time_range:
            cutoff = datetime.utcnow() - time_range
            entries = [e for e in entries if e.timestamp >= cutoff]
        
        if not entries:
            return {
                "total_cost": 0.0,
                "total_tokens": 0,
                "total_calls": 0,
                "workflows": 0
            }
        
        total_cost = sum(e.cost for e in entries)
        total_tokens = sum(e.input_tokens + e.output_tokens for e in entries)
        unique_workflows = len(set(e.workflow_id for e in entries))
        
        # Average cost per workflow
        avg_cost_per_workflow = total_cost / unique_workflows if unique_workflows > 0 else 0.0
        
        # Most expensive models
        model_costs = {}
        for entry in entries:
            if entry.model not in model_costs:
                model_costs[entry.model] = 0.0
            model_costs[entry.model] += entry.cost
        
        top_models = sorted(
            model_costs.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "total_calls": len(entries),
            "workflows": unique_workflows,
            "avg_cost_per_workflow": avg_cost_per_workflow,
            "top_models": [{"model": m, "cost": c} for m, c in top_models],
            "time_range": str(time_range) if time_range else "all_time"
        }
    
    def get_cost_breakdown(self) -> Dict[str, Any]:
        """Get detailed cost breakdown."""
        if not self.cost_entries:
            return {}
        
        # By task type
        task_costs = {}
        for entry in self.cost_entries:
            if entry.task_type not in task_costs:
                task_costs[entry.task_type] = 0.0
            task_costs[entry.task_type] += entry.cost
        
        # By agent
        agent_costs = {}
        for entry in self.cost_entries:
            if entry.agent_name not in agent_costs:
                agent_costs[entry.agent_name] = 0.0
            agent_costs[entry.agent_name] += entry.cost
        
        return {
            "by_task": task_costs,
            "by_agent": agent_costs,
            "by_model": dict(self.model_usage),
            "total": self.total_cost
        }
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cost statistics."""
        return {
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "total_calls": len(self.cost_entries),
            "unique_workflows": len(self.workflow_costs),
            "model_usage": self.model_usage,
            "avg_cost_per_call": self.total_cost / len(self.cost_entries) if self.cost_entries else 0.0
        }


# ============================================================================
# CLI FOR TESTING
# ============================================================================

if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table
    from ai_model_router import ModelRouter
    
    console = Console()
    
    console.print("\n[bold cyan]Cost Optimizer - Test[/bold cyan]\n")
    
    # Create optimizer
    router = ModelRouter()
    optimizer = CostOptimizer(router)
    
    # Simulate workflow
    workflow_id = "test-workflow-123"
    optimizer.set_workflow_budget(workflow_id, 0.01)
    
    # Simulate cost entries
    optimizer.track_cost(
        workflow_id=workflow_id,
        agent_name="site_analyzer",
        model="gpt-4o-mini",
        input_tokens=500,
        output_tokens=200,
        cost=0.0015,
        task_type="site_analysis"
    )
    
    optimizer.track_cost(
        workflow_id=workflow_id,
        agent_name="form_intelligence",
        model="gpt-4o-mini",
        input_tokens=800,
        output_tokens=300,
        cost=0.0025,
        task_type="form_analysis"
    )
    
    # Get report
    console.print("[cyan]Workflow Report:[/cyan]")
    report = optimizer.get_workflow_report(workflow_id)
    
    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow")
    
    table.add_row("Total Cost", f"${report['total_cost']:.6f}")
    table.add_row("Budget", f"${report['budget']:.6f}")
    table.add_row("Remaining", f"${report['remaining']:.6f}")
    table.add_row("Status", report['status'])
    table.add_row("Total Calls", str(report['total_calls']))
    table.add_row("Total Tokens", str(report['total_tokens']))
    
    console.print(table)
    
    # Agent costs
    if report.get('agent_costs'):
        console.print(f"\n[cyan]Cost by Agent:[/cyan]")
        for agent, cost in report['agent_costs'].items():
            console.print(f"  {agent}: ${cost:.6f}")
    
    # Opportunities
    console.print(f"\n[cyan]Cost Saving Opportunities:[/cyan]")
    opportunities = optimizer.get_cost_saving_opportunities()
    if opportunities:
        for opp in opportunities:
            console.print(f"  • {opp['type']}: {opp['suggestion']}")
    else:
        console.print("  No opportunities identified")
