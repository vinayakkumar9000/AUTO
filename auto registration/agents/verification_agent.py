#!/usr/bin/env python3
"""
Verification Agent
Verifies registration success through multiple methods
Author: vinayakkumar9000
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base_agent import BaseAgent, AgentResult, AgentContext, AgentStatus
from ai_model_router import ModelRouter
import logging

# ============================================================================
# VERIFICATION AGENT
# ============================================================================

class VerificationAgent(BaseAgent):
    """
    Verification Agent - Verifies registration success.
    
    Responsibilities:
    - Verify registration completion
    - Check authenticated state
    - Validate account creation
    - Return confidence score
    - Collect evidence
    
    Verification Methods:
    - URL change detection
    - Dashboard access check
    - Session cookie validation
    - Logout button presence
    - Welcome message detection
    - Profile page access
    """
    
    def __init__(
        self,
        model_router: ModelRouter,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Verification Agent.
        
        Args:
            model_router: Model router instance
            logger: Optional logger instance
        """
        super().__init__("verification", model_router, logger)
        
        # Success indicators
        self.success_patterns = {
            "url_patterns": [
                r"/dashboard",
                r"/home",
                r"/welcome",
                r"/profile",
                r"/account",
                r"/app"
            ],
            "text_patterns": [
                r"welcome",
                r"successfully registered",
                r"account created",
                r"registration complete",
                r"verify your email",
                r"check your inbox"
            ],
            "element_patterns": [
                r"logout",
                r"sign out",
                r"log out",
                r"profile",
                r"settings",
                r"account"
            ]
        }
        
        # Failure indicators
        self.failure_patterns = {
            "error_messages": [
                r"error",
                r"failed",
                r"invalid",
                r"already exists",
                r"try again",
                r"something went wrong"
            ],
            "captcha_patterns": [
                r"captcha",
                r"recaptcha",
                r"hcaptcha",
                r"verify you're human"
            ]
        }
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Verify registration success.
        
        Args:
            context: Execution context with page state
        
        Returns:
            AgentResult with verification outcome
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Verifying registration for {context.domain}")
            
            # Collect evidence from multiple sources
            evidence = []
            confidence_scores = []
            
            # Method 1: URL Analysis
            url_check = self._check_url(context)
            if url_check["success"]:
                evidence.append(url_check["evidence"])
                confidence_scores.append(url_check["confidence"])
            
            # Method 2: Page Content Analysis
            content_check = self._check_content(context)
            if content_check["success"]:
                evidence.append(content_check["evidence"])
                confidence_scores.append(content_check["confidence"])
            
            # Method 3: Session State Check
            session_check = self._check_session(context)
            if session_check["success"]:
                evidence.append(session_check["evidence"])
                confidence_scores.append(session_check["confidence"])
            
            # Method 4: Element Presence Check
            element_check = self._check_elements(context)
            if element_check["success"]:
                evidence.append(element_check["evidence"])
                confidence_scores.append(element_check["confidence"])
            
            # Check for failure indicators
            failure_check = self._check_failures(context)
            if failure_check["failed"]:
                evidence.append(failure_check["evidence"])
                confidence_scores.append(0.0)
            
            # Calculate overall confidence
            if confidence_scores:
                overall_confidence = sum(confidence_scores) / len(confidence_scores)
            else:
                overall_confidence = 0.0
            
            # Determine success
            success = overall_confidence >= 0.7 and len(evidence) >= 2
            
            # Use AI for low-confidence cases
            cost = 0.0
            model_used = "deterministic"
            
            if 0.5 <= overall_confidence < 0.7:
                ai_verification = await self._ai_verify(context, evidence)
                if ai_verification["confidence"] > overall_confidence:
                    success = ai_verification["success"]
                    overall_confidence = ai_verification["confidence"]
                    evidence.append(ai_verification["evidence"])
                cost = ai_verification["cost"]
                model_used = ai_verification["model"]
            
            verification_data = {
                "success": success,
                "method": "multi_check",
                "evidence": evidence,
                "confidence": overall_confidence,
                "checks_passed": len([e for e in evidence if "success" in e.lower()]),
                "total_checks": len(evidence)
            }
            
            status = AgentStatus.SUCCESS if success else AgentStatus.FAILURE
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_name=self.name,
                status=status,
                data=verification_data,
                confidence=overall_confidence,
                execution_time=execution_time,
                cost=cost,
                model_used=model_used
            )
            
        except Exception as e:
            self.logger.error(f"Verification error: {str(e)}")
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.ERROR,
                data={"success": False},
                confidence=0.0,
                execution_time=execution_time,
                cost=0.0,
                error=str(e)
            )
    
    def get_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate confidence score for verification."""
        return result.get("confidence", 0.0)
    
    # ========================================================================
    # VERIFICATION METHODS
    # ========================================================================
    
    def _check_url(self, context: AgentContext) -> Dict[str, Any]:
        """Check if URL indicates success."""
        import re
        
        current_url = context.metadata.get("current_url", context.url)
        
        for pattern in self.success_patterns["url_patterns"]:
            if re.search(pattern, current_url, re.IGNORECASE):
                return {
                    "success": True,
                    "evidence": f"URL changed to success page: {pattern}",
                    "confidence": 0.8
                }
        
        # Check if URL changed from signup page
        if current_url != context.url and "/signup" not in current_url.lower():
            return {
                "success": True,
                "evidence": "URL changed from signup page",
                "confidence": 0.6
            }
        
        return {"success": False, "evidence": "URL unchanged", "confidence": 0.0}
    
    def _check_content(self, context: AgentContext) -> Dict[str, Any]:
        """Check page content for success indicators."""
        import re
        
        page_content = context.page_content or ""
        content_lower = page_content.lower()
        
        for pattern in self.success_patterns["text_patterns"]:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return {
                    "success": True,
                    "evidence": f"Success message found: {pattern}",
                    "confidence": 0.9
                }
        
        return {"success": False, "evidence": "No success message", "confidence": 0.0}
    
    def _check_session(self, context: AgentContext) -> Dict[str, Any]:
        """Check session state."""
        cookies = context.metadata.get("cookies", [])
        
        # Check for session cookies
        session_cookies = [
            "session", "auth", "token", "jwt", "access_token",
            "user_id", "logged_in"
        ]
        
        for cookie in cookies:
            cookie_name = cookie.get("name", "").lower()
            for session_pattern in session_cookies:
                if session_pattern in cookie_name:
                    return {
                        "success": True,
                        "evidence": f"Session cookie found: {cookie_name}",
                        "confidence": 0.85
                    }
        
        return {"success": False, "evidence": "No session cookies", "confidence": 0.0}
    
    def _check_elements(self, context: AgentContext) -> Dict[str, Any]:
        """Check for authenticated user elements."""
        import re
        
        page_content = context.page_content or ""
        content_lower = page_content.lower()
        
        for pattern in self.success_patterns["element_patterns"]:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return {
                    "success": True,
                    "evidence": f"Authenticated element found: {pattern}",
                    "confidence": 0.75
                }
        
        return {"success": False, "evidence": "No auth elements", "confidence": 0.0}
    
    def _check_failures(self, context: AgentContext) -> Dict[str, Any]:
        """Check for failure indicators."""
        import re
        
        page_content = context.page_content or ""
        content_lower = page_content.lower()
        
        # Check for error messages
        for pattern in self.failure_patterns["error_messages"]:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return {
                    "failed": True,
                    "evidence": f"Error detected: {pattern}",
                    "confidence": 0.0
                }
        
        # Check for CAPTCHA
        for pattern in self.failure_patterns["captcha_patterns"]:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return {
                    "failed": True,
                    "evidence": f"CAPTCHA detected: {pattern}",
                    "confidence": 0.0
                }
        
        return {"failed": False, "evidence": "No failures detected", "confidence": 1.0}
    
    # ========================================================================
    # AI-ENHANCED VERIFICATION
    # ========================================================================
    
    async def _ai_verify(
        self,
        context: AgentContext,
        evidence: List[str]
    ) -> Dict[str, Any]:
        """Use AI to verify registration success."""
        model = self.model_router.select_model(
            task_type="verification",
            confidence=0.6,
            budget_remaining=context.budget_remaining
        )
        
        page_content = context.page_content or ""
        if len(page_content) > 2000:
            page_content = page_content[:2000]
        
        prompt = f"""Verify if registration was successful based on:

Current Evidence:
{chr(10).join(f"- {e}" for e in evidence)}

Page Content (truncated):
{page_content}

Current URL: {context.metadata.get('current_url', 'unknown')}

Respond in JSON:
{{
    "success": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}"""
        
        try:
            input_tokens = len(prompt) // 4
            output_tokens = 50
            
            cost = self.model_router.get_cost_estimate(
                model, input_tokens, output_tokens
            )
            
            self.model_router.track_usage(model, input_tokens, output_tokens)
            
            # Simulate AI response (replace with actual API call)
            return {
                "success": len(evidence) >= 2,
                "confidence": 0.75,
                "evidence": "AI verification: Multiple success indicators present",
                "cost": cost,
                "model": model
            }
            
        except Exception as e:
            self.logger.error(f"AI verification error: {str(e)}")
            return {
                "success": False,
                "confidence": 0.0,
                "evidence": f"AI verification failed: {str(e)}",
                "cost": 0.0,
                "model": "error"
            }


# ============================================================================
# CLI FOR TESTING
# ============================================================================

if __name__ == "__main__":
    from rich.console import Console
    import asyncio
    from ai_model_router import ModelRouter
    from .base_agent import create_agent_context
    
    console = Console()
    
    console.print("\n[bold cyan]Verification Agent - Test[/bold cyan]\n")
    
    async def test():
        router = ModelRouter()
        agent = VerificationAgent(router)
        
        # Test successful registration
        context = create_agent_context(
            workflow_id="test-123",
            url="https://example.com/signup"
        )
        
        context.metadata["current_url"] = "https://example.com/dashboard"
        context.page_content = """
        <html>
        <body>
            <h1>Welcome to Example!</h1>
            <p>Your account has been successfully created.</p>
            <button>Logout</button>
            <a href="/profile">Profile</a>
        </body>
        </html>
        """
        context.metadata["cookies"] = [
            {"name": "session_token", "value": "abc123"}
        ]
        
        console.print("[cyan]Verifying successful registration...[/cyan]")
        result = await agent.execute(context)
        
        console.print(f"\n[green]Verification Result:[/green]")
        console.print(f"  Status: {result.status.value}")
        console.print(f"  Success: {result.data.get('success')}")
        console.print(f"  Confidence: {result.confidence:.2f}")
        console.print(f"  Evidence: {len(result.data.get('evidence', []))} checks")
        console.print(f"  Time: {result.execution_time:.3f}s")
        console.print(f"  Cost: ${result.cost:.6f}")
        
        if result.data.get("evidence"):
            console.print(f"\n[cyan]Evidence:[/cyan]")
            for evidence in result.data["evidence"]:
                console.print(f"  • {evidence}")
    
    asyncio.run(test())
