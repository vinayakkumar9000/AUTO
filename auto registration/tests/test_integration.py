#!/usr/bin/env python3
"""
Integration Tests
Test integration between agents and components
Author: vinayakkumar9000
"""

import asyncio
import pytest
from typing import Dict, Any
import logging

from integration_layer import IntegrationLayer, create_integration_layer
from ai_model_router import ModelRouter
from domain_intelligence import DomainIntelligence
from agents.coordinator_agent import CoordinatorAgent
from agents.base_agent import create_agent_context

# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def integration_layer():
    """Create integration layer for testing."""
    return create_integration_layer()

@pytest.fixture
def model_router():
    """Create model router for testing."""
    return ModelRouter()

@pytest.fixture
def domain_intelligence():
    """Create domain intelligence for testing."""
    return DomainIntelligence()

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegrationLayer:
    """Test integration layer functionality."""
    
    @pytest.mark.asyncio
    async def test_workflow_execution(self, integration_layer):
        """Test basic workflow execution."""
        result = await integration_layer.execute_registration(
            url="https://example.com/signup",
            budget=0.01,
            timeout=60
        )
        
        assert result is not None
        assert "workflow_id" in result
        assert "success" in result
        assert "execution_time" in result
    
    @pytest.mark.asyncio
    async def test_callback_system(self, integration_layer):
        """Test callback system."""
        callbacks_triggered = []
        
        def on_start(state):
            callbacks_triggered.append("start")
        
        def on_complete(state):
            callbacks_triggered.append("complete")
        
        integration_layer.register_callback("on_start", on_start)
        integration_layer.register_callback("on_complete", on_complete)
        
        await integration_layer.execute_registration(
            url="https://example.com/signup",
            budget=0.01,
            timeout=60
        )
        
        assert "start" in callbacks_triggered
        assert "complete" in callbacks_triggered
    
    def test_workflow_status(self, integration_layer):
        """Test workflow status tracking."""
        workflow_id = "test-123"
        status = integration_layer.get_workflow_status(workflow_id)
        
        # Should be None for non-existent workflow
        assert status is None
    
    def test_active_workflows(self, integration_layer):
        """Test active workflow tracking."""
        workflows = integration_layer.get_active_workflows()
        assert isinstance(workflows, list)


class TestCoordinatorIntegration:
    """Test coordinator agent integration."""
    
    @pytest.mark.asyncio
    async def test_coordinator_execution(self, model_router, domain_intelligence):
        """Test coordinator execution."""
        coordinator = CoordinatorAgent(
            model_router=model_router,
            domain_intelligence=domain_intelligence
        )
        
        context = create_agent_context(
            workflow_id="test-123",
            url="https://example.com/signup"
        )
        
        result = await coordinator.execute(context)
        
        assert result is not None
        assert hasattr(result, "status")
        assert hasattr(result, "data")
        assert hasattr(result, "confidence")


class TestAgentCommunication:
    """Test communication between agents."""
    
    @pytest.mark.asyncio
    async def test_context_passing(self, model_router):
        """Test context passing between agents."""
        from agents.site_analyzer_agent import SiteAnalyzerAgent
        from agents.planner_agent import RegistrationPlannerAgent
        
        # Create agents
        analyzer = SiteAnalyzerAgent(model_router)
        planner = RegistrationPlannerAgent(model_router)
        
        # Create context
        context = create_agent_context(
            workflow_id="test-123",
            url="https://example.com/signup"
        )
        context.page_content = "<html><body><form></form></body></html>"
        
        # Execute analyzer
        analyzer_result = await analyzer.execute(context)
        
        # Pass result to planner
        context.previous_results["site_analysis"] = analyzer_result.data
        
        # Execute planner
        planner_result = await planner.execute(context)
        
        assert planner_result is not None
        assert planner_result.data.get("strategy") is not None


class TestCostOptimization:
    """Test cost optimization integration."""
    
    def test_budget_enforcement(self):
        """Test budget enforcement."""
        from cost_optimizer import CostOptimizer
        
        router = ModelRouter()
        optimizer = CostOptimizer(router)
        
        workflow_id = "test-123"
        optimizer.set_workflow_budget(workflow_id, 0.01)
        
        # Track some costs
        optimizer.track_cost(
            workflow_id=workflow_id,
            agent_name="test_agent",
            model="gpt-4o-mini",
            input_tokens=500,
            output_tokens=200,
            cost=0.005,
            task_type="test"
        )
        
        remaining = optimizer.get_remaining_budget(workflow_id)
        assert remaining == 0.005
        
        # Check budget
        allowed, reason = optimizer.check_budget(workflow_id, 0.01)
        assert not allowed
    
    def test_cost_tracking(self):
        """Test cost tracking."""
        from cost_optimizer import CostOptimizer
        
        router = ModelRouter()
        optimizer = CostOptimizer(router)
        
        workflow_id = "test-123"
        optimizer.set_workflow_budget(workflow_id, 0.01)
        
        optimizer.track_cost(
            workflow_id=workflow_id,
            agent_name="test_agent",
            model="gpt-4o-mini",
            input_tokens=500,
            output_tokens=200,
            cost=0.002,
            task_type="test"
        )
        
        report = optimizer.get_workflow_report(workflow_id)
        
        assert report["total_cost"] == 0.002
        assert report["total_calls"] == 1


class TestPerformanceMonitoring:
    """Test performance monitoring integration."""
    
    def test_operation_tracking(self):
        """Test operation tracking."""
        from performance_monitor import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        workflow_id = "test-123"
        monitor.track_operation(
            workflow_id=workflow_id,
            agent_name="test_agent",
            operation="test_op",
            execution_time=5.0,
            success=True
        )
        
        report = monitor.get_workflow_report(workflow_id)
        
        assert report["total_time"] == 5.0
        assert report["total_operations"] == 1
    
    def test_bottleneck_detection(self):
        """Test bottleneck detection."""
        from performance_monitor import PerformanceMonitor
        
        monitor = PerformanceMonitor(slow_threshold=10.0)
        
        workflow_id = "test-123"
        
        # Track slow operation
        monitor.track_operation(
            workflow_id=workflow_id,
            agent_name="slow_agent",
            operation="slow_op",
            execution_time=15.0,
            success=True
        )
        
        bottlenecks = monitor.get_bottlenecks()
        
        assert len(bottlenecks) > 0
        assert bottlenecks[0]["execution_time"] == 15.0


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
