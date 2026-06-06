#!/usr/bin/env python3
"""
Site Analyzer Agent
Analyzes target websites to detect framework, anti-bot mechanisms, and complexity
Author: vinayakkumar9000
"""

import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

from .base_agent import BaseAgent, AgentResult, AgentContext, AgentStatus
from ai_model_router import ModelRouter
import logging

# ============================================================================
# SITE ANALYZER AGENT
# ============================================================================

class SiteAnalyzerAgent(BaseAgent):
    """
    Site Analyzer Agent - Analyzes target websites.
    
    Responsibilities:
    - Detect web framework (React, Vue, Angular, Next.js, etc.)
    - Identify anti-bot mechanisms (CAPTCHA, Cloudflare, Turnstile)
    - Detect verification requirements (OTP, magic link, email)
    - Assess signup complexity
    - Provide structured site profile
    """
    
    def __init__(
        self,
        model_router: ModelRouter,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Site Analyzer Agent.
        
        Args:
            model_router: Model router instance
            logger: Optional logger instance
        """
        super().__init__("site_analyzer", model_router, logger)
        
        # Framework detection patterns
        self.framework_patterns = {
            "react": [
                r"react",
                r"_react",
                r"data-reactroot",
                r"data-reactid",
                r"__REACT",
                r"ReactDOM"
            ],
            "vue": [
                r"vue",
                r"_vue",
                r"data-v-",
                r"__VUE__",
                r"Vue.js"
            ],
            "angular": [
                r"angular",
                r"ng-",
                r"data-ng-",
                r"__ANGULAR__",
                r"Angular"
            ],
            "nextjs": [
                r"next",
                r"_next",
                r"__NEXT_DATA__",
                r"Next.js"
            ],
            "svelte": [
                r"svelte",
                r"_svelte",
                r"__SVELTE__"
            ]
        }
        
        # Anti-bot detection patterns
        self.antibot_patterns = {
            "cloudflare": [
                r"cloudflare",
                r"cf-ray",
                r"__cf_bm",
                r"cf_clearance"
            ],
            "recaptcha": [
                r"recaptcha",
                r"g-recaptcha",
                r"grecaptcha"
            ],
            "hcaptcha": [
                r"hcaptcha",
                r"h-captcha"
            ],
            "turnstile": [
                r"turnstile",
                r"cf-turnstile"
            ],
            "datadome": [
                r"datadome",
                r"dd_cookie"
            ]
        }
        
        # Verification type patterns
        self.verification_patterns = {
            "otp": [
                r"otp",
                r"verification code",
                r"verification token",
                r"enter code",
                r"6-digit",
                r"4-digit"
            ],
            "magic_link": [
                r"magic link",
                r"email link",
                r"click the link",
                r"verification link"
            ],
            "email_verification": [
                r"verify email",
                r"confirm email",
                r"email confirmation"
            ]
        }
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Analyze target site.
        
        Args:
            context: Execution context with page content
        
        Returns:
            AgentResult with site analysis
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Analyzing site: {context.domain}")
            
            # Check if we have domain intelligence
            domain_profile = context.metadata.get("domain_profile")
            use_cached = False
            
            if domain_profile and domain_profile.total_attempts > 0:
                # Use cached analysis if available and recent
                if domain_profile.framework and domain_profile.verification_type:
                    use_cached = True
                    self.logger.info(f"Using cached analysis for {context.domain}")
            
            if use_cached:
                analysis_data = self._create_cached_analysis(domain_profile)
                confidence = 0.9  # High confidence for cached data
                cost = 0.0
                model_used = "cached"
            else:
                # Perform new analysis
                page_content = context.page_content or ""
                
                # Deterministic analysis first
                framework = self._detect_framework(page_content)
                anti_bot = self._detect_antibot(page_content)
                verification = self._detect_verification(page_content)
                complexity = self._calculate_complexity(
                    framework, anti_bot, verification
                )
                
                # Use AI for low-confidence cases
                confidence = self._calculate_confidence(
                    framework, anti_bot, verification
                )
                
                if confidence < 0.7 and page_content:
                    # Use AI to enhance analysis
                    ai_analysis = await self._ai_analyze(
                        context, page_content, framework, anti_bot, verification
                    )
                    
                    if ai_analysis["confidence"] > confidence:
                        framework = ai_analysis.get("framework", framework)
                        anti_bot = ai_analysis.get("anti_bot", anti_bot)
                        verification = ai_analysis.get("verification", verification)
                        confidence = ai_analysis["confidence"]
                        cost = ai_analysis["cost"]
                        model_used = ai_analysis["model"]
                    else:
                        cost = ai_analysis["cost"]
                        model_used = ai_analysis["model"]
                else:
                    cost = 0.0
                    model_used = "deterministic"
                
                analysis_data = {
                    "domain": context.domain,
                    "framework": framework,
                    "anti_bot": anti_bot,
                    "verification": verification,
                    "complexity": complexity,
                    "estimated_steps": self._estimate_steps(verification),
                    "known_selectors": domain_profile.known_selectors if domain_profile else {},
                    "success_rate": domain_profile.success_rate if domain_profile else 0.0,
                    "total_attempts": domain_profile.total_attempts if domain_profile else 0
                }
            
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.SUCCESS,
                data=analysis_data,
                confidence=confidence,
                execution_time=execution_time,
                cost=cost,
                model_used=model_used
            )
            
        except Exception as e:
            self.logger.error(f"Site analysis error: {str(e)}")
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.ERROR,
                data={},
                confidence=0.0,
                execution_time=execution_time,
                cost=0.0,
                error=str(e)
            )
    
    def get_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate confidence score for analysis."""
        confidence = 0.5
        
        # Increase confidence if framework detected
        if result.get("framework") and result["framework"] != "unknown":
            confidence += 0.2
        
        # Increase confidence if verification type detected
        if result.get("verification") and result["verification"] != "unknown":
            confidence += 0.2
        
        # Increase confidence if we have historical data
        if result.get("total_attempts", 0) > 0:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    # ========================================================================
    # DETERMINISTIC DETECTION
    # ========================================================================
    
    def _detect_framework(self, content: str) -> str:
        """Detect web framework from page content."""
        content_lower = content.lower()
        
        for framework, patterns in self.framework_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    self.logger.info(f"Detected framework: {framework}")
                    return framework
        
        return "unknown"
    
    def _detect_antibot(self, content: str) -> List[str]:
        """Detect anti-bot mechanisms."""
        detected = []
        content_lower = content.lower()
        
        for mechanism, patterns in self.antibot_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    if mechanism not in detected:
                        detected.append(mechanism)
                        self.logger.info(f"Detected anti-bot: {mechanism}")
                    break
        
        return detected
    
    def _detect_verification(self, content: str) -> str:
        """Detect verification type."""
        content_lower = content.lower()
        
        for verification_type, patterns in self.verification_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    self.logger.info(f"Detected verification: {verification_type}")
                    return verification_type
        
        return "unknown"
    
    def _calculate_complexity(
        self,
        framework: str,
        anti_bot: List[str],
        verification: str
    ) -> float:
        """Calculate site complexity score (0.0 - 1.0)."""
        complexity = 0.3  # Base complexity
        
        # Framework complexity
        if framework in ["react", "vue", "angular", "nextjs"]:
            complexity += 0.2
        
        # Anti-bot adds complexity
        complexity += len(anti_bot) * 0.15
        
        # Verification complexity
        if verification == "otp":
            complexity += 0.2
        elif verification == "magic_link":
            complexity += 0.15
        
        return min(complexity, 1.0)
    
    def _calculate_confidence(
        self,
        framework: str,
        anti_bot: List[str],
        verification: str
    ) -> float:
        """Calculate confidence in deterministic analysis."""
        confidence = 0.5
        
        if framework != "unknown":
            confidence += 0.2
        
        if anti_bot:
            confidence += 0.1
        
        if verification != "unknown":
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _estimate_steps(self, verification: str) -> int:
        """Estimate number of steps required."""
        base_steps = 4  # Navigate, fill, submit, verify
        
        if verification == "otp":
            return base_steps + 4  # Wait email, extract, enter, submit
        elif verification == "magic_link":
            return base_steps + 3  # Wait email, extract, navigate
        elif verification == "email_verification":
            return base_steps + 2  # Wait email, click link
        
        return base_steps
    
    def _create_cached_analysis(self, domain_profile) -> Dict[str, Any]:
        """Create analysis from cached domain profile."""
        return {
            "domain": domain_profile.domain,
            "framework": domain_profile.framework,
            "anti_bot": domain_profile.anti_bot_mechanisms,
            "verification": domain_profile.verification_type,
            "complexity": domain_profile.complexity_score,
            "estimated_steps": self._estimate_steps(domain_profile.verification_type),
            "known_selectors": domain_profile.known_selectors,
            "success_rate": domain_profile.success_rate,
            "total_attempts": domain_profile.total_attempts,
            "cached": True
        }
    
    # ========================================================================
    # AI-ENHANCED ANALYSIS
    # ========================================================================
    
    async def _ai_analyze(
        self,
        context: AgentContext,
        page_content: str,
        framework: str,
        anti_bot: List[str],
        verification: str
    ) -> Dict[str, Any]:
        """Use AI to enhance site analysis."""
        # Select appropriate model
        model = self.model_router.select_model(
            task_type="form_analysis",
            confidence=0.6,
            budget_remaining=context.budget_remaining,
            context_size=len(page_content) // 4
        )
        
        # Truncate content if too long
        max_content = 4000
        if len(page_content) > max_content:
            page_content = page_content[:max_content]
        
        prompt = f"""Analyze this registration page and provide:
1. Web framework (react/vue/angular/nextjs/svelte/static)
2. Anti-bot mechanisms (cloudflare/recaptcha/hcaptcha/turnstile/none)
3. Verification type (otp/magic_link/email_verification/none)

Current detection:
- Framework: {framework}
- Anti-bot: {anti_bot}
- Verification: {verification}

Page content (truncated):
{page_content}

Respond in JSON format:
{{
    "framework": "detected_framework",
    "anti_bot": ["mechanism1", "mechanism2"],
    "verification": "verification_type",
    "confidence": 0.0-1.0
}}"""
        
        try:
            # Simulate AI call (replace with actual B.ai API call)
            # For now, return enhanced deterministic result
            input_tokens = len(prompt) // 4
            output_tokens = 100
            
            cost = self.model_router.get_cost_estimate(
                model, input_tokens, output_tokens
            )
            
            self.model_router.track_usage(model, input_tokens, output_tokens)
            
            return {
                "framework": framework,
                "anti_bot": anti_bot,
                "verification": verification,
                "confidence": 0.75,
                "cost": cost,
                "model": model
            }
            
        except Exception as e:
            self.logger.error(f"AI analysis error: {str(e)}")
            return {
                "framework": framework,
                "anti_bot": anti_bot,
                "verification": verification,
                "confidence": 0.5,
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
    
    console.print("\n[bold cyan]Site Analyzer Agent - Test[/bold cyan]\n")
    
    async def test():
        router = ModelRouter()
        agent = SiteAnalyzerAgent(router)
        
        # Test with sample content
        sample_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="/_next/static/chunks/main.js"></script>
            <script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>
        </head>
        <body>
            <div id="__next">
                <form>
                    <input type="email" name="email" />
                    <input type="password" name="password" />
                    <p>We'll send you a verification code</p>
                    <button type="submit">Sign Up</button>
                </form>
            </div>
        </body>
        </html>
        """
        
        context = create_agent_context(
            workflow_id="test-123",
            url="https://example.com/signup"
        )
        context.page_content = sample_content
        
        console.print("[cyan]Analyzing sample page...[/cyan]")
        result = await agent.execute(context)
        
        console.print(f"\n[green]Analysis Result:[/green]")
        console.print(f"  Status: {result.status.value}")
        console.print(f"  Confidence: {result.confidence:.2f}")
        console.print(f"  Time: {result.execution_time:.3f}s")
        console.print(f"  Cost: ${result.cost:.6f}")
        console.print(f"  Model: {result.model_used}")
        
        if result.data:
            console.print(f"\n[cyan]Site Profile:[/cyan]")
            console.print(f"  Framework: {result.data.get('framework')}")
            console.print(f"  Anti-bot: {result.data.get('anti_bot')}")
            console.print(f"  Verification: {result.data.get('verification')}")
            console.print(f"  Complexity: {result.data.get('complexity'):.2f}")
            console.print(f"  Estimated Steps: {result.data.get('estimated_steps')}")
    
    asyncio.run(test())
