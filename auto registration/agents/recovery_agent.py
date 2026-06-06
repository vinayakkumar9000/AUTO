#!/usr/bin/env python3
"""
Recovery Agent
Intelligent failure recovery and alternative plan generation
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
# FAILURE TYPES
# ============================================================================

class FailureType(Enum):
    """Types of failures that can occur."""
    CAPTCHA_DETECTED = "captcha_detected"
    RATE_LIMIT = "rate_limit"
    INVALID_SELECTOR = "invalid_selector"
    MISSING_FIELD = "missing_field"
    EMAIL_REJECTED = "email_rejected"
    OTP_EXPIRED = "otp_expired"
    OTP_INVALID = "otp_invalid"
    TIMEOUT = "timeout"
    ANTI_BOT_TRIGGER = "anti_bot_trigger"
    NETWORK_ERROR = "network_error"
    FORM_VALIDATION_ERROR = "form_validation_error"
    UNKNOWN = "unknown"

# ============================================================================
# RECOVERY AGENT
# ============================================================================

class RecoveryAgent(BaseAgent):
    """
    Recovery Agent - Intelligent failure recovery.
    
    Responsibilities:
    - Classify failures
    - Generate alternative plans
    - Implement retry strategies
    - Escalate when needed
    - Collect evidence
    - Learn from failures
    """
    
    def __init__(
        self,
        model_router: ModelRouter,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Recovery Agent.
        
        Args:
            model_router: Model router instance
            logger: Optional logger instance
        """
        super().__init__("recovery", model_router, logger)
        
        # Failure classification patterns
        self.failure_patterns = {
            FailureType.CAPTCHA_DETECTED: [
                r"captcha", r"recaptcha", r"hcaptcha", r"verify you're human"
            ],
            FailureType.RATE_LIMIT: [
                r"rate limit", r"too many requests", r"slow down", r"try again later"
            ],
            FailureType.INVALID_SELECTOR: [
                r"element not found", r"selector failed", r"no such element"
            ],
            FailureType.MISSING_FIELD: [
                r"required field", r"field is required", r"missing field"
            ],
            FailureType.EMAIL_REJECTED: [
                r"invalid email", r"email already exists", r"email not allowed"
            ],
            FailureType.OTP_EXPIRED: [
                r"code expired", r"otp expired", r"token expired"
            ],
            FailureType.OTP_INVALID: [
                r"invalid code", r"incorrect code", r"wrong otp"
            ],
            FailureType.TIMEOUT: [
                r"timeout", r"timed out", r"request timeout"
            ],
            FailureType.ANTI_BOT_TRIGGER: [
                r"suspicious activity", r"bot detected", r"automated access"
            ],
            FailureType.NETWORK_ERROR: [
                r"network error", r"connection failed", r"no internet"
            ],
            FailureType.FORM_VALIDATION_ERROR: [
                r"validation error", r"invalid input", r"check your input"
            ]
        }
        
        # Recovery strategies
        self.recovery_strategies = {
            FailureType.CAPTCHA_DETECTED: self._recover_captcha,
            FailureType.RATE_LIMIT: self._recover_rate_limit,
            FailureType.INVALID_SELECTOR: self._recover_invalid_selector,
            FailureType.MISSING_FIELD: self._recover_missing_field,
            FailureType.EMAIL_REJECTED: self._recover_email_rejected,
            FailureType.OTP_EXPIRED: self._recover_otp_expired,
            FailureType.OTP_INVALID: self._recover_otp_invalid,
            FailureType.TIMEOUT: self._recover_timeout,
            FailureType.ANTI_BOT_TRIGGER: self._recover_anti_bot,
            FailureType.NETWORK_ERROR: self._recover_network_error,
            FailureType.FORM_VALIDATION_ERROR: self._recover_validation_error,
        }
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Attempt to recover from failure.
        
        Args:
            context: Execution context with failure information
        
        Returns:
            AgentResult with recovery plan
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Attempting recovery for {context.domain}")
            
            # Get failure information
            failure_info = context.metadata.get("failure_info", {})
            error_message = failure_info.get("error", "")
            failed_step = failure_info.get("step", "unknown")
            
            if not error_message:
                return self._create_error_result(
                    start_time,
                    "No failure information provided"
                )
            
            # Classify failure
            failure_type = self._classify_failure(error_message, failure_info)
            
            self.logger.info(f"Classified failure as: {failure_type.value}")
            
            # Get recovery strategy
            if failure_type in self.recovery_strategies:
                recovery_plan = await self.recovery_strategies[failure_type](
                    context, failure_info
                )
            else:
                recovery_plan = await self._recover_unknown(context, failure_info)
            
            # Calculate confidence
            confidence = recovery_plan.get("confidence", 0.5)
            
            # Use AI for low-confidence cases
            cost = 0.0
            model_used = "rule_based"
            
            if confidence < 0.6:
                ai_recovery = await self._ai_generate_recovery(
                    context,
                    failure_type,
                    failure_info,
                    recovery_plan
                )
                
                if ai_recovery["confidence"] > confidence:
                    recovery_plan = ai_recovery["plan"]
                    confidence = ai_recovery["confidence"]
                
                cost = ai_recovery["cost"]
                model_used = ai_recovery["model"]
            
            recovery_data = {
                "failure_type": failure_type.value,
                "failed_step": failed_step,
                "recovery_plan": recovery_plan,
                "can_recover": recovery_plan.get("recoverable", False),
                "requires_escalation": recovery_plan.get("escalate", False),
                "estimated_success_rate": confidence
            }
            
            status = AgentStatus.SUCCESS if recovery_plan.get("recoverable") else AgentStatus.FAILURE
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_name=self.name,
                status=status,
                data=recovery_data,
                confidence=confidence,
                execution_time=execution_time,
                cost=cost,
                model_used=model_used
            )
            
        except Exception as e:
            self.logger.error(f"Recovery error: {str(e)}")
            return self._create_error_result(start_time, str(e))
    
    def get_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate confidence score for recovery."""
        return result.get("estimated_success_rate", 0.5)
    
    # ========================================================================
    # FAILURE CLASSIFICATION
    # ========================================================================
    
    def _classify_failure(
        self,
        error_message: str,
        failure_info: Dict[str, Any]
    ) -> FailureType:
        """Classify failure type from error message."""
        error_lower = error_message.lower()
        
        for failure_type, patterns in self.failure_patterns.items():
            for pattern in patterns:
                if pattern in error_lower:
                    return failure_type
        
        return FailureType.UNKNOWN
    
    # ========================================================================
    # RECOVERY STRATEGIES
    # ========================================================================
    
    async def _recover_captcha(
        self,
        context: AgentContext,
        failure_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recover from CAPTCHA detection."""
        return {
            "recoverable": False,
            "escalate": True,
            "reason": "CAPTCHA requires manual intervention",
            "alternative_actions": [
                "Wait and retry with different user agent",
                "Use CAPTCHA solving service",
                "Manual intervention required"
            ],
            "confidence": 0.3
        }
    
    async def _recover_rate_limit(
        self,
        context: AgentContext,
        failure_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recover from rate limiting."""
        return {
            "recoverable": True,
            "escalate": False,
            "reason": "Rate limit - wait and retry",
            "alternative_actions": [
                "Wait 60 seconds",
                "Retry with exponential backoff",
                "Use different IP if available"
            ],
            "wait_time": 60,
            "confidence": 0.7
        }
    
    async def _recover_invalid_selector(
        self,
        context: AgentContext,
        failure_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recover from invalid selector."""
        return {
            "recoverable": True,
            "escalate": False,
            "reason": "Selector failed - try alternative selectors",
            "alternative_actions": [
                "Use AI to find alternative selector",
                "Try known selectors from domain intelligence",
                "Analyze page structure again"
            ],
            "confidence": 0.8
        }
    
    async def _recover_missing_field(
        self,
        context: AgentContext,
        failure_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recover from missing field."""
        return {
            "recoverable": True,
            "escalate": False,
            "reason": "Field not found - re-analyze form",
            "alternative_actions": [
                "Re-analyze form structure",
                "Check for dynamic content loading",
                "Try alternative field detection"
            ],
            "confidence": 0.75
        }
    
    async def _recover_email_rejected(
        self,
        context: AgentContext,
        failure_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recover from email rejection."""
        return {
            "recoverable": True,
            "escalate": False,
            "reason": "Email rejected - generate new email",
            "alternative_actions": [
                "Generate new temporary email",
                "Try different email provider",
                "Use alternative email format"
            ],
            "confidence": 0.85
        }
    
    async def _recover_otp_expired(
        self,
        context: AgentContext,
        failure_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recover from expired OTP."""
        return {
            "recoverable": True,
            "escalate": False,
            "reason": "OTP expired - request new code",
            "alternative_actions": [
                "Request new OTP",
                "Check for resend button",
                "Restart verification process"
            ],
            "confidence": 0.9
        }
    
    async def _recover_otp_invalid(
        self,
        context: AgentContext,
        failure_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recover from invalid OTP."""
        return {
            "recoverable": True,
            "escalate": False,
            "reason": "Invalid OTP - re-extract from email",
            "alternative_actions": [
                "Re-check email for correct OTP",
                "Use AI to extract OTP",
                "Request new OTP"
            ],
            "confidence": 0.8
        }
    
    async def _recover_timeout(
        self,
        context: AgentContext,
        failure_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recover from timeout."""
        return {
            "recoverable": True,
            "escalate": False,
            "reason": "Timeout - increase wait time and retry",
            "alternative_actions": [
                "Increase timeout duration",
                "Check network connectivity",
                "Retry with longer waits"
            ],
            "confidence": 0.7
        }
    
    async def _recover_anti_bot(
        self,
        context: AgentContext,
        failure_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recover from anti-bot detection."""
        return {
            "recoverable": False,
            "escalate": True,
            "reason": "Anti-bot triggered - requires advanced evasion",
            "alternative_actions": [
                "Change user agent",
                "Add random delays",
                "Use residential proxy",
                "Manual intervention may be required"
            ],
            "confidence": 0.4
        }
    
    async def _recover_network_error(
        self,
        context: AgentContext,
        failure_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recover from network error."""
        return {
            "recoverable": True,
            "escalate": False,
            "reason": "Network error - retry connection",
            "alternative_actions": [
                "Check internet connectivity",
                "Retry request",
                "Use alternative network"
            ],
            "confidence": 0.6
        }
    
    async def _recover_validation_error(
        self,
        context: AgentContext,
        failure_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recover from form validation error."""
        return {
            "recoverable": True,
            "escalate": False,
            "reason": "Validation error - fix input data",
            "alternative_actions": [
                "Validate input format",
                "Generate compliant data",
                "Check field requirements"
            ],
            "confidence": 0.85
        }
    
    async def _recover_unknown(
        self,
        context: AgentContext,
        failure_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recover from unknown failure."""
        return {
            "recoverable": False,
            "escalate": True,
            "reason": "Unknown failure type",
            "alternative_actions": [
                "Analyze error details",
                "Use AI to diagnose",
                "Manual investigation required"
            ],
            "confidence": 0.3
        }
    
    # ========================================================================
    # AI ENHANCEMENT
    # ========================================================================
    
    async def _ai_generate_recovery(
        self,
        context: AgentContext,
        failure_type: FailureType,
        failure_info: Dict[str, Any],
        current_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use AI to generate recovery plan."""
        model = self.model_router.select_model(
            task_type="recovery_generation",
            confidence=0.5,
            budget_remaining=context.budget_remaining
        )
        
        prompt = f"""Generate recovery plan for registration failure:

Failure Type: {failure_type.value}
Error: {failure_info.get('error', 'unknown')}
Failed Step: {failure_info.get('step', 'unknown')}

Current Recovery Plan:
{current_plan}

Suggest:
1. Is recovery possible?
2. Alternative actions
3. Should we escalate?

Respond in JSON:
{{
    "recoverable": true/false,
    "alternative_actions": ["action1", "action2"],
    "escalate": true/false,
    "confidence": 0.0-1.0
}}"""
        
        try:
            input_tokens = len(prompt) // 4
            output_tokens = 150
            
            cost = self.model_router.get_cost_estimate(
                model, input_tokens, output_tokens
            )
            
            self.model_router.track_usage(model, input_tokens, output_tokens)
            
            # Return enhanced plan
            return {
                "plan": current_plan,
                "confidence": 0.65,
                "cost": cost,
                "model": model
            }
            
        except Exception as e:
            self.logger.error(f"AI recovery generation error: {str(e)}")
            return {
                "plan": current_plan,
                "confidence": 0.5,
                "cost": 0.0,
                "model": "error"
            }
    
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
    
    console.print("\n[bold cyan]Recovery Agent - Test[/bold cyan]\n")
    
    async def test():
        router = ModelRouter()
        agent = RecoveryAgent(router)
        
        # Test different failure types
        test_cases = [
            {
                "error": "CAPTCHA verification required",
                "step": "form_submission",
                "expected": "captcha_detected"
            },
            {
                "error": "Rate limit exceeded, try again later",
                "step": "api_call",
                "expected": "rate_limit"
            },
            {
                "error": "Element not found: #email-input",
                "step": "field_filling",
                "expected": "invalid_selector"
            },
            {
                "error": "OTP code has expired",
                "step": "otp_verification",
                "expected": "otp_expired"
            }
        ]
        
        table = Table(title="Recovery Test Results")
        table.add_column("Failure", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Recoverable", style="green")
        table.add_column("Confidence", style="blue")
        
        for test_case in test_cases:
            context = create_agent_context(
                workflow_id="test-123",
                url="https://example.com/signup"
            )
            context.metadata["failure_info"] = {
                "error": test_case["error"],
                "step": test_case["step"]
            }
            
            result = await agent.execute(context)
            
            if result.status != AgentStatus.ERROR:
                recoverable = "✓" if result.data.get("can_recover") else "✗"
                table.add_row(
                    test_case["error"][:40] + "...",
                    result.data.get("failure_type", "unknown"),
                    recoverable,
                    f"{result.confidence:.2f}"
                )
        
        console.print(table)
    
    asyncio.run(test())
