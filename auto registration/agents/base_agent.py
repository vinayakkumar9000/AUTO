#!/usr/bin/env python3
"""
Base Agent
Abstract base class for all agents in the multi-agent system
Author: vinayakkumar9000
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import json
import logging
from pathlib import Path

# ============================================================================
# DATA CLASSES
# ============================================================================

class AgentStatus(Enum):
    """Agent execution status."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    ERROR = "error"

@dataclass
class AgentContext:
    """Context passed to agents during execution."""
    workflow_id: str
    url: str
    domain: str
    page_content: Optional[str] = None
    screenshot: Optional[bytes] = None
    previous_results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    budget_remaining: float = 0.10
    timeout: int = 300

@dataclass
class AgentResult:
    """Result returned by agent execution."""
    agent_name: str
    status: AgentStatus
    data: Dict[str, Any]
    confidence: float
    execution_time: float
    cost: float
    model_used: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "status": self.status.value,
            "data": self.data,
            "confidence": self.confidence,
            "execution_time": self.execution_time,
            "cost": self.cost,
            "model_used": self.model_used,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }

# ============================================================================
# BASE AGENT
# ============================================================================

class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    All agents must implement:
    - execute(): Main execution logic
    - get_confidence(): Calculate confidence score
    """
    
    def __init__(
        self,
        name: str,
        model_router: Any,
        logger: Optional[logging.Logger] = None,
        log_dir: Optional[Path] = None
    ):
        """
        Initialize base agent.
        
        Args:
            name: Agent name
            model_router: Model router instance
            logger: Optional logger instance
            log_dir: Optional directory for agent logs
        """
        self.name = name
        self.model_router = model_router
        self.logger = logger or self._setup_logger(log_dir)
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_cost = 0.0
        self.total_time = 0.0
    
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute agent logic.
        
        Args:
            context: Execution context
        
        Returns:
            AgentResult with execution outcome
        """
        pass
    
    @abstractmethod
    def get_confidence(self, result: Dict[str, Any]) -> float:
        """
        Calculate confidence score for result.
        
        Args:
            result: Execution result data
        
        Returns:
            Confidence score (0.0 - 1.0)
        """
        pass
    
    def should_escalate(self, confidence: float, threshold: float = 0.7) -> bool:
        """
        Determine if model should be escalated.
        
        Args:
            confidence: Current confidence score
            threshold: Minimum acceptable confidence
        
        Returns:
            True if escalation needed
        """
        return confidence < threshold
    
    def should_retry(self, attempt: int, max_attempts: int = 3) -> bool:
        """
        Determine if operation should be retried.
        
        Args:
            attempt: Current attempt number
            max_attempts: Maximum retry attempts
        
        Returns:
            True if retry should be attempted
        """
        return attempt < max_attempts
    
    async def execute_with_retry(
        self,
        context: AgentContext,
        max_attempts: int = 3,
        escalate_on_failure: bool = True
    ) -> AgentResult:
        """
        Execute agent with automatic retry and escalation.
        
        Args:
            context: Execution context
            max_attempts: Maximum retry attempts
            escalate_on_failure: Whether to escalate model on failure
        
        Returns:
            AgentResult
        """
        start_time = datetime.utcnow()
        last_result = None
        current_model = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                self.logger.info(f"{self.name}: Attempt {attempt}/{max_attempts}")
                
                # Execute agent
                result = await self.execute(context)
                
                # Track statistics
                self.execution_count += 1
                self.total_cost += result.cost
                self.total_time += result.execution_time
                
                if result.status == AgentStatus.SUCCESS:
                    self.success_count += 1
                    self.log_execution(result)
                    return result
                
                # Check if we should retry
                if not self.should_retry(attempt, max_attempts):
                    self.failure_count += 1
                    self.log_execution(result)
                    return result
                
                # Escalate model if enabled and confidence is low
                if escalate_on_failure and result.confidence < 0.7:
                    if result.model_used:
                        current_model = result.model_used
                        new_model = self.model_router.escalate_model(
                            current_model,
                            f"Low confidence: {result.confidence}"
                        )
                        self.logger.info(f"{self.name}: Escalating from {current_model} to {new_model}")
                        context.metadata["escalated_model"] = new_model
                
                last_result = result
                
            except Exception as e:
                self.logger.error(f"{self.name}: Error on attempt {attempt}: {str(e)}")
                last_result = AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.ERROR,
                    data={},
                    confidence=0.0,
                    execution_time=(datetime.utcnow() - start_time).total_seconds(),
                    cost=0.0,
                    error=str(e)
                )
        
        # All attempts failed
        self.failure_count += 1
        if last_result:
            self.log_execution(last_result)
            return last_result
        
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.FAILURE,
            data={},
            confidence=0.0,
            execution_time=(datetime.utcnow() - start_time).total_seconds(),
            cost=0.0,
            error="All retry attempts failed"
        )
    
    def log_execution(self, result: AgentResult):
        """
        Log agent execution result.
        
        Args:
            result: Execution result
        """
        log_level = logging.INFO if result.status == AgentStatus.SUCCESS else logging.WARNING
        
        self.logger.log(
            log_level,
            f"{self.name} execution: status={result.status.value}, "
            f"confidence={result.confidence:.2f}, "
            f"time={result.execution_time:.2f}s, "
            f"cost=${result.cost:.6f}"
        )
        
        if result.error:
            self.logger.error(f"{self.name} error: {result.error}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get agent execution statistics.
        
        Returns:
            Statistics dictionary
        """
        success_rate = (
            self.success_count / self.execution_count
            if self.execution_count > 0
            else 0.0
        )
        
        avg_time = (
            self.total_time / self.execution_count
            if self.execution_count > 0
            else 0.0
        )
        
        avg_cost = (
            self.total_cost / self.execution_count
            if self.execution_count > 0
            else 0.0
        )
        
        return {
            "agent_name": self.name,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": success_rate,
            "total_cost": self.total_cost,
            "total_time": self.total_time,
            "average_cost": avg_cost,
            "average_time": avg_time
        }
    
    def reset_statistics(self):
        """Reset agent statistics."""
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_cost = 0.0
        self.total_time = 0.0
    
    def _setup_logger(self, log_dir: Optional[Path] = None) -> logging.Logger:
        """
        Setup logger for agent.
        
        Args:
            log_dir: Optional directory for log files
        
        Returns:
            Logger instance
        """
        logger = logging.getLogger(f"agent.{self.name}")
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler if log_dir provided
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(
                log_dir / f"{self.name}.log"
            )
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(name='{self.name}')"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_agent_context(
    workflow_id: str,
    url: str,
    budget: float = 0.10,
    timeout: int = 300,
    **kwargs
) -> AgentContext:
    """
    Create agent context with defaults.
    
    Args:
        workflow_id: Unique workflow identifier
        url: Target URL
        budget: Budget in dollars
        timeout: Timeout in seconds
        **kwargs: Additional context parameters
    
    Returns:
        AgentContext instance
    """
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    
    return AgentContext(
        workflow_id=workflow_id,
        url=url,
        domain=domain,
        budget_remaining=budget,
        timeout=timeout,
        **kwargs
    )


# ============================================================================
# CLI FOR TESTING
# ============================================================================

if __name__ == "__main__":
    from rich.console import Console
    
    console = Console()
    
    console.print("\n[bold cyan]Base Agent - Test Implementation[/bold cyan]\n")
    
    # Create a test agent
    class TestAgent(BaseAgent):
        async def execute(self, context: AgentContext) -> AgentResult:
            import time
            start = time.time()
            
            # Simulate work
            await asyncio.sleep(0.1)
            
            result_data = {"test": "success"}
            confidence = self.get_confidence(result_data)
            
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.SUCCESS,
                data=result_data,
                confidence=confidence,
                execution_time=time.time() - start,
                cost=0.001,
                model_used="gpt-5.4-mini"
            )
        
        def get_confidence(self, result: Dict[str, Any]) -> float:
            return 0.95
    
    # Test the agent
    import asyncio
    from ai_model_router import ModelRouter
    
    async def test():
        router = ModelRouter()
        agent = TestAgent("test_agent", router)
        
        context = create_agent_context(
            workflow_id="test-123",
            url="https://example.com/signup"
        )
        
        console.print("[cyan]Executing test agent...[/cyan]")
        result = await agent.execute_with_retry(context)
        
        console.print(f"\n[green]Result:[/green]")
        console.print(f"  Status: {result.status.value}")
        console.print(f"  Confidence: {result.confidence:.2f}")
        console.print(f"  Time: {result.execution_time:.3f}s")
        console.print(f"  Cost: ${result.cost:.6f}")
        
        console.print(f"\n[cyan]Statistics:[/cyan]")
        stats = agent.get_statistics()
        for key, value in stats.items():
            console.print(f"  {key}: {value}")
    
    asyncio.run(test())
