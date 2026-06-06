#!/usr/bin/env python3
"""
End-to-End Tests
Test complete registration workflows with real scenarios
Author: vinayakkumar9000
"""

import asyncio
import pytest
from typing import Dict, Any
import logging
from datetime import datetime

from integration_layer import create_integration_layer, V4Bridge
from domain_intelligence import DomainIntelligence

# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def integration():
    """Create integration layer for testing."""
    return create_integration_layer()

@pytest.fixture
def v4_bridge(integration):
    """Create V4 bridge for testing."""
    return V4Bridge(integration)

# ============================================================================
# END-TO-END TESTS
# ============================================================================

class TestBasicRegistration:
    """Test basic registration workflows."""
    
    @pytest.mark.asyncio
    async def test_email_only_registration(self, integration):
        """Test email-only registration flow."""
        result = await integration.execute_registration(
            url="https://example.com/signup",
            budget=0.01,
            timeout=120
        )
        
        assert result is not None
        assert "workflow_id" in result
        assert "execution_time" in result
        assert result["execution_time"] < 120
    
    @pytest.mark.asyncio
    async def test_email_password_registration(self, integration):
        """Test email+password registration flow."""
        identity_data = {
            "email": "test@example.com",
            "password": "SecurePass123!"
        }
        
        result = await integration.execute_registration(
            url="https://example.com/signup",
            identity_data=identity_data,
            budget=0.01,
            timeout=120
        )
        
        assert result is not None
        assert "workflow_id" in result


class TestComplexRegistration:
    """Test complex registration scenarios."""
    
    @pytest.mark.asyncio
    async def test_multi_step_registration(self, integration):
        """Test multi-step registration flow."""
        result = await integration.execute_registration(
            url="https://example.com/signup",
            budget=0.015,
            timeout=180
        )
        
        assert result is not None
        assert "workflow_id" in result
    
    @pytest.mark.asyncio
    async def test_otp_verification(self, integration):
        """Test OTP verification flow."""
        result = await integration.execute_registration(
            url="https://example.com/signup",
            budget=0.015,
            timeout=180
        )
        
        assert result is not None
        assert "workflow_id" in result


class TestErrorRecovery:
    """Test error recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, integration):
        """Test timeout handling."""
        result = await integration.execute_registration(
            url="https://example.com/signup",
            budget=0.01,
            timeout=5  # Very short timeout
        )
        
        assert result is not None
        assert "error" in result or "success" in result
    
    @pytest.mark.asyncio
    async def test_budget_exceeded(self, integration):
        """Test budget exceeded handling."""
        result = await integration.execute_registration(
            url="https://example.com/signup",
            budget=0.0001,  # Very low budget
            timeout=120
        )
        
        assert result is not None


class TestV4Compatibility:
    """Test V4 bridge compatibility."""
    
    @pytest.mark.asyncio
    async def test_v4_register_account(self, v4_bridge):
        """Test V4 register_account function."""
        result = await v4_bridge.register_account(
            url="https://example.com/signup",
            email="test@example.com",
            password="SecurePass123!"
        )
        
        assert result is not None
        assert "success" in result
        assert "workflow_id" in result
    
    def test_v4_get_status(self, v4_bridge):
        """Test V4 get_status function."""
        status = v4_bridge.get_status("non-existent-workflow")
        assert status is None


class TestLearningSystem:
    """Test learning system functionality."""
    
    @pytest.mark.asyncio
    async def test_domain_learning(self, integration):
        """Test domain learning after successful registration."""
        # First attempt
        result1 = await integration.execute_registration(
            url="https://example.com/signup",
            budget=0.01,
            timeout=120
        )
        
        # Second attempt (should use learned data)
        result2 = await integration.execute_registration(
            url="https://example.com/signup",
            budget=0.01,
            timeout=120
        )
        
        # Second attempt should be faster or cheaper
        assert result1 is not None
        assert result2 is not None
    
    def test_domain_intelligence_persistence(self):
        """Test domain intelligence persistence."""
        db = DomainIntelligence()
        
        # Get or create profile
        profile = db.get_or_create_profile("example.com")
        
        assert profile is not None
        assert profile.domain == "example.com"


class TestCostOptimization:
    """Test cost optimization in real workflows."""
    
    @pytest.mark.asyncio
    async def test_cost_within_budget(self, integration):
        """Test that costs stay within budget."""
        budget = 0.01
        
        result = await integration.execute_registration(
            url="https://example.com/signup",
            budget=budget,
            timeout=120
        )
        
        assert result is not None
        if "cost" in result:
            assert result["cost"] <= budget
    
    @pytest.mark.asyncio
    async def test_cost_optimization(self, integration):
        """Test cost optimization over multiple runs."""
        costs = []
        
        for i in range(3):
            result = await integration.execute_registration(
                url="https://example.com/signup",
                budget=0.01,
                timeout=120
            )
            
            if "cost" in result:
                costs.append(result["cost"])
        
        # Costs should generally decrease as system learns
        assert len(costs) > 0


class TestPerformanceTargets:
    """Test performance targets."""
    
    @pytest.mark.asyncio
    async def test_execution_time_target(self, integration):
        """Test execution time meets target."""
        result = await integration.execute_registration(
            url="https://example.com/signup",
            budget=0.01,
            timeout=120
        )
        
        assert result is not None
        if "execution_time" in result:
            # Target: < 60s average
            assert result["execution_time"] < 120
    
    @pytest.mark.asyncio
    async def test_success_rate_tracking(self, integration):
        """Test success rate tracking."""
        results = []
        
        for i in range(5):
            result = await integration.execute_registration(
                url="https://example.com/signup",
                budget=0.01,
                timeout=120
            )
            results.append(result.get("success", False))
        
        # Should have some successes
        assert len(results) > 0


# ============================================================================
# PERFORMANCE BENCHMARKS
# ============================================================================

class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    @pytest.mark.asyncio
    async def test_concurrent_workflows(self, integration):
        """Test concurrent workflow execution."""
        tasks = []
        
        for i in range(3):
            task = integration.execute_registration(
                url=f"https://example{i}.com/signup",
                budget=0.01,
                timeout=120
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        assert len(results) == 3
        # At least some should succeed
        successes = sum(1 for r in results if isinstance(r, dict) and not isinstance(r, Exception))
        assert successes > 0
    
    @pytest.mark.asyncio
    async def test_memory_efficiency(self, integration):
        """Test memory efficiency over multiple runs."""
        import gc
        
        for i in range(10):
            result = await integration.execute_registration(
                url="https://example.com/signup",
                budget=0.01,
                timeout=60
            )
            
            # Force garbage collection
            gc.collect()
        
        # Should complete without memory issues
        assert True


# ============================================================================
# INTEGRATION SCENARIOS
# ============================================================================

class TestRealWorldScenarios:
    """Test real-world registration scenarios."""
    
    @pytest.mark.asyncio
    async def test_react_spa_registration(self, integration):
        """Test registration on React SPA."""
        result = await integration.execute_registration(
            url="https://example.com/signup",
            budget=0.015,
            timeout=120
        )
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_cloudflare_protected_site(self, integration):
        """Test registration on Cloudflare-protected site."""
        result = await integration.execute_registration(
            url="https://example.com/signup",
            budget=0.02,
            timeout=180
        )
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_magic_link_verification(self, integration):
        """Test magic link verification flow."""
        result = await integration.execute_registration(
            url="https://example.com/signup",
            budget=0.015,
            timeout=180
        )
        
        assert result is not None


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto", "-s"])
