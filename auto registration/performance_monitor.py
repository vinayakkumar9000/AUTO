#!/usr/bin/env python3
"""
Performance Monitor
Real-time performance tracking and bottleneck identification
Author: vinayakkumar9000
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

# ============================================================================
# PERFORMANCE METRICS
# ============================================================================

@dataclass
class PerformanceEntry:
    """Single performance entry."""
    timestamp: datetime
    workflow_id: str
    agent_name: str
    operation: str
    execution_time: float
    success: bool
    error: Optional[str] = None

class PerformanceStatus(Enum):
    """Performance status."""
    EXCELLENT = "excellent"  # < 30s
    GOOD = "good"           # 30-60s
    ACCEPTABLE = "acceptable"  # 60-120s
    SLOW = "slow"           # > 120s

# ============================================================================
# PERFORMANCE MONITOR
# ============================================================================

class PerformanceMonitor:
    """
    Performance Monitor - Track and optimize execution performance.
    
    Responsibilities:
    - Track execution times
    - Identify bottlenecks
    - Monitor success rates
    - Generate performance reports
    - Alert on slow operations
    - Suggest optimizations
    """
    
    def __init__(
        self,
        slow_threshold: float = 120.0,
        warning_threshold: float = 60.0,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Performance Monitor.
        
        Args:
            slow_threshold: Threshold for slow operations (seconds)
            warning_threshold: Threshold for warnings (seconds)
            logger: Optional logger instance
        """
        self.slow_threshold = slow_threshold
        self.warning_threshold = warning_threshold
        self.logger = logger or logging.getLogger(__name__)
        
        # Performance tracking
        self.entries: List[PerformanceEntry] = []
        self.workflow_times: Dict[str, float] = {}
        self.agent_times: Dict[str, List[float]] = {}
        self.operation_times: Dict[str, List[float]] = {}
        
        # Success tracking
        self.workflow_success: Dict[str, bool] = {}
        self.agent_success: Dict[str, List[bool]] = {}
        
        # Bottleneck tracking
        self.bottlenecks: List[Dict[str, Any]] = []
    
    # ========================================================================
    # TRACKING
    # ========================================================================
    
    def track_operation(
        self,
        workflow_id: str,
        agent_name: str,
        operation: str,
        execution_time: float,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Track operation performance."""
        entry = PerformanceEntry(
            timestamp=datetime.utcnow(),
            workflow_id=workflow_id,
            agent_name=agent_name,
            operation=operation,
            execution_time=execution_time,
            success=success,
            error=error
        )
        
        self.entries.append(entry)
        
        # Update workflow time
        if workflow_id not in self.workflow_times:
            self.workflow_times[workflow_id] = 0.0
        self.workflow_times[workflow_id] += execution_time
        
        # Update agent times
        if agent_name not in self.agent_times:
            self.agent_times[agent_name] = []
        self.agent_times[agent_name].append(execution_time)
        
        # Update operation times
        if operation not in self.operation_times:
            self.operation_times[operation] = []
        self.operation_times[operation].append(execution_time)
        
        # Update success tracking
        if agent_name not in self.agent_success:
            self.agent_success[agent_name] = []
        self.agent_success[agent_name].append(success)
        
        # Check for slow operations
        if execution_time > self.slow_threshold:
            self.logger.warning(
                f"Slow operation detected: {agent_name}.{operation} "
                f"took {execution_time:.2f}s"
            )
            self._record_bottleneck(agent_name, operation, execution_time)
        elif execution_time > self.warning_threshold:
            self.logger.info(
                f"Operation warning: {agent_name}.{operation} "
                f"took {execution_time:.2f}s"
            )
    
    def track_workflow_completion(
        self,
        workflow_id: str,
        success: bool
    ) -> None:
        """Track workflow completion."""
        self.workflow_success[workflow_id] = success
        
        total_time = self.workflow_times.get(workflow_id, 0.0)
        status = self._get_performance_status(total_time)
        
        self.logger.info(
            f"Workflow {workflow_id} completed: "
            f"success={success}, time={total_time:.2f}s, status={status.value}"
        )
    
    # ========================================================================
    # ANALYSIS
    # ========================================================================
    
    def get_bottlenecks(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get identified bottlenecks."""
        # Sort by execution time
        sorted_bottlenecks = sorted(
            self.bottlenecks,
            key=lambda x: x["execution_time"],
            reverse=True
        )
        
        return sorted_bottlenecks[:limit]
    
    def get_slowest_agents(
        self,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get slowest agents by average execution time."""
        agent_stats = []
        
        for agent_name, times in self.agent_times.items():
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                min_time = min(times)
                
                agent_stats.append({
                    "agent": agent_name,
                    "avg_time": avg_time,
                    "max_time": max_time,
                    "min_time": min_time,
                    "calls": len(times)
                })
        
        # Sort by average time
        sorted_stats = sorted(
            agent_stats,
            key=lambda x: x["avg_time"],
            reverse=True
        )
        
        return sorted_stats[:limit]
    
    def get_slowest_operations(
        self,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get slowest operations by average execution time."""
        operation_stats = []
        
        for operation, times in self.operation_times.items():
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                
                operation_stats.append({
                    "operation": operation,
                    "avg_time": avg_time,
                    "max_time": max_time,
                    "calls": len(times)
                })
        
        # Sort by average time
        sorted_stats = sorted(
            operation_stats,
            key=lambda x: x["avg_time"],
            reverse=True
        )
        
        return sorted_stats[:limit]
    
    def get_success_rates(self) -> Dict[str, float]:
        """Get success rates by agent."""
        success_rates = {}
        
        for agent_name, successes in self.agent_success.items():
            if successes:
                success_rate = sum(successes) / len(successes)
                success_rates[agent_name] = success_rate
        
        return success_rates
    
    # ========================================================================
    # REPORTING
    # ========================================================================
    
    def get_workflow_report(
        self,
        workflow_id: str
    ) -> Dict[str, Any]:
        """Get performance report for workflow."""
        entries = [e for e in self.entries if e.workflow_id == workflow_id]
        
        if not entries:
            return {}
        
        total_time = self.workflow_times.get(workflow_id, 0.0)
        success = self.workflow_success.get(workflow_id, False)
        status = self._get_performance_status(total_time)
        
        # Agent breakdown
        agent_breakdown = {}
        for entry in entries:
            if entry.agent_name not in agent_breakdown:
                agent_breakdown[entry.agent_name] = {
                    "time": 0.0,
                    "calls": 0,
                    "successes": 0
                }
            
            agent_breakdown[entry.agent_name]["time"] += entry.execution_time
            agent_breakdown[entry.agent_name]["calls"] += 1
            if entry.success:
                agent_breakdown[entry.agent_name]["successes"] += 1
        
        return {
            "workflow_id": workflow_id,
            "total_time": total_time,
            "success": success,
            "status": status.value,
            "total_operations": len(entries),
            "agent_breakdown": agent_breakdown
        }
    
    def get_global_report(
        self,
        time_range: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Get global performance report."""
        entries = self.entries
        
        # Filter by time range
        if time_range:
            cutoff = datetime.utcnow() - time_range
            entries = [e for e in entries if e.timestamp >= cutoff]
        
        if not entries:
            return {
                "total_workflows": 0,
                "total_operations": 0,
                "avg_workflow_time": 0.0,
                "success_rate": 0.0
            }
        
        # Calculate metrics
        unique_workflows = len(set(e.workflow_id for e in entries))
        total_operations = len(entries)
        
        # Average workflow time
        workflow_times = list(self.workflow_times.values())
        avg_workflow_time = sum(workflow_times) / len(workflow_times) if workflow_times else 0.0
        
        # Overall success rate
        successes = sum(1 for e in entries if e.success)
        success_rate = successes / total_operations if total_operations > 0 else 0.0
        
        return {
            "total_workflows": unique_workflows,
            "total_operations": total_operations,
            "avg_workflow_time": avg_workflow_time,
            "success_rate": success_rate,
            "time_range": str(time_range) if time_range else "all_time"
        }
    
    def get_optimization_suggestions(self) -> List[str]:
        """Get optimization suggestions."""
        suggestions = []
        
        # Check for slow agents
        slowest = self.get_slowest_agents(limit=3)
        for agent_stat in slowest:
            if agent_stat["avg_time"] > self.warning_threshold:
                suggestions.append(
                    f"Optimize {agent_stat['agent']} agent "
                    f"(avg: {agent_stat['avg_time']:.2f}s)"
                )
        
        # Check for low success rates
        success_rates = self.get_success_rates()
        for agent, rate in success_rates.items():
            if rate < 0.7:
                suggestions.append(
                    f"Improve {agent} success rate "
                    f"(current: {rate:.1%})"
                )
        
        # Check for bottlenecks
        bottlenecks = self.get_bottlenecks(limit=3)
        for bottleneck in bottlenecks:
            suggestions.append(
                f"Address bottleneck in {bottleneck['agent']}.{bottleneck['operation']} "
                f"({bottleneck['execution_time']:.2f}s)"
            )
        
        return suggestions
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.entries:
            return {}
        
        total_time = sum(e.execution_time for e in self.entries)
        avg_time = total_time / len(self.entries)
        
        return {
            "total_operations": len(self.entries),
            "total_time": total_time,
            "avg_operation_time": avg_time,
            "unique_workflows": len(self.workflow_times),
            "unique_agents": len(self.agent_times),
            "bottlenecks_identified": len(self.bottlenecks)
        }
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _get_performance_status(self, execution_time: float) -> PerformanceStatus:
        """Get performance status based on execution time."""
        if execution_time < 30:
            return PerformanceStatus.EXCELLENT
        elif execution_time < 60:
            return PerformanceStatus.GOOD
        elif execution_time < 120:
            return PerformanceStatus.ACCEPTABLE
        else:
            return PerformanceStatus.SLOW
    
    def _record_bottleneck(
        self,
        agent_name: str,
        operation: str,
        execution_time: float
    ) -> None:
        """Record a bottleneck."""
        self.bottlenecks.append({
            "timestamp": datetime.utcnow(),
            "agent": agent_name,
            "operation": operation,
            "execution_time": execution_time
        })


# ============================================================================
# CLI FOR TESTING
# ============================================================================

if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    console.print("\n[bold cyan]Performance Monitor - Test[/bold cyan]\n")
    
    # Create monitor
    monitor = PerformanceMonitor()
    
    # Simulate workflow
    workflow_id = "test-workflow-123"
    
    # Simulate operations
    monitor.track_operation(
        workflow_id=workflow_id,
        agent_name="site_analyzer",
        operation="analyze_site",
        execution_time=5.2,
        success=True
    )
    
    monitor.track_operation(
        workflow_id=workflow_id,
        agent_name="form_intelligence",
        operation="analyze_form",
        execution_time=8.5,
        success=True
    )
    
    monitor.track_operation(
        workflow_id=workflow_id,
        agent_name="email_intelligence",
        operation="wait_for_email",
        execution_time=25.0,
        success=True
    )
    
    monitor.track_workflow_completion(workflow_id, success=True)
    
    # Get report
    console.print("[cyan]Workflow Report:[/cyan]")
    report = monitor.get_workflow_report(workflow_id)
    
    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow")
    
    table.add_row("Total Time", f"{report['total_time']:.2f}s")
    table.add_row("Status", report['status'])
    table.add_row("Success", str(report['success']))
    table.add_row("Operations", str(report['total_operations']))
    
    console.print(table)
    
    # Agent breakdown
    if report.get('agent_breakdown'):
        console.print(f"\n[cyan]Agent Breakdown:[/cyan]")
        for agent, stats in report['agent_breakdown'].items():
            console.print(
                f"  {agent}: {stats['time']:.2f}s "
                f"({stats['calls']} calls, "
                f"{stats['successes']}/{stats['calls']} success)"
            )
    
    # Suggestions
    console.print(f"\n[cyan]Optimization Suggestions:[/cyan]")
    suggestions = monitor.get_optimization_suggestions()
    if suggestions:
        for suggestion in suggestions:
            console.print(f"  • {suggestion}")
    else:
        console.print("  No suggestions - performance is good!")
