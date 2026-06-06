#!/usr/bin/env python3
"""
Email Intelligence Agent
Smart inbox monitoring and content extraction for verification emails
Author: vinayakkumar9000
"""

import re
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base_agent import BaseAgent, AgentResult, AgentContext, AgentStatus
from ai_model_router import ModelRouter
import logging

# ============================================================================
# EMAIL TYPES
# ============================================================================

class EmailType:
    """Email classification types."""
    VERIFICATION = "verification"
    OTP = "otp"
    MAGIC_LINK = "magic_link"
    PASSWORD_RESET = "password_reset"
    WELCOME = "welcome"
    MARKETING = "marketing"
    SPAM = "spam"
    UNKNOWN = "unknown"

# ============================================================================
# EMAIL INTELLIGENCE AGENT
# ============================================================================

class EmailIntelligenceAgent(BaseAgent):
    """
    Email Intelligence Agent - Smart email monitoring and extraction.
    
    Responsibilities:
    - Monitor inbox intelligently
    - Classify emails by type
    - Extract OTP codes
    - Extract magic links
    - Handle multiple verification types
    - Smart polling with timeout
    """
    
    def __init__(
        self,
        model_router: ModelRouter,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Email Intelligence Agent.
        
        Args:
            model_router: Model router instance
            logger: Optional logger instance
        """
        super().__init__("email_intelligence", model_router, logger)
        
        # OTP extraction patterns
        self.otp_patterns = [
            r'\b(\d{6})\b',           # 6-digit code
            r'\b(\d{4})\b',           # 4-digit code
            r'\b(\d{8})\b',           # 8-digit code
            r'\b([A-Z0-9]{6})\b',     # 6-char alphanumeric
            r'code[:\s]+(\d+)',       # "code: 123456"
            r'token[:\s]+(\d+)',      # "token: 123456"
            r'verification[:\s]+(\d+)' # "verification: 123456"
        ]
        
        # Magic link patterns
        self.link_patterns = [
            r'https?://[^\s<>"]+/verify[^\s<>"]*',
            r'https?://[^\s<>"]+/confirm[^\s<>"]*',
            r'https?://[^\s<>"]+/activate[^\s<>"]*',
            r'https?://[^\s<>"]+/magic[^\s<>"]*',
            r'https?://[^\s<>"]+/auth[^\s<>"]*'
        ]
        
        # Email classification keywords
        self.classification_keywords = {
            EmailType.VERIFICATION: [
                "verify", "verification", "confirm", "activate"
            ],
            EmailType.OTP: [
                "code", "otp", "token", "verification code"
            ],
            EmailType.MAGIC_LINK: [
                "magic link", "click here", "sign in link"
            ],
            EmailType.PASSWORD_RESET: [
                "reset password", "forgot password", "password recovery"
            ],
            EmailType.WELCOME: [
                "welcome", "getting started", "thank you for signing up"
            ]
        }
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Monitor inbox and extract verification data.
        
        Args:
            context: Execution context with email access
        
        Returns:
            AgentResult with extracted data
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Monitoring inbox for {context.domain}")
            
            # Get email content from context
            email_content = context.metadata.get("email_content")
            email_subject = context.metadata.get("email_subject", "")
            
            if not email_content:
                return self._create_error_result(
                    start_time,
                    "No email content available"
                )
            
            # Classify email
            email_type = self._classify_email(email_subject, email_content)
            
            # Extract verification data based on type
            extracted_data = {}
            confidence = 0.5
            
            if email_type == EmailType.OTP:
                otp = self._extract_otp(email_content)
                if otp:
                    extracted_data["otp"] = otp
                    extracted_data["format"] = f"{len(otp)}-digit"
                    confidence = 0.95
            
            elif email_type == EmailType.MAGIC_LINK:
                link = self._extract_magic_link(email_content)
                if link:
                    extracted_data["magic_link"] = link
                    confidence = 0.9
            
            elif email_type == EmailType.VERIFICATION:
                # Try both OTP and link
                otp = self._extract_otp(email_content)
                link = self._extract_magic_link(email_content)
                
                if otp:
                    extracted_data["otp"] = otp
                    extracted_data["format"] = f"{len(otp)}-digit"
                    confidence = 0.9
                
                if link:
                    extracted_data["magic_link"] = link
                    confidence = max(confidence, 0.85)
            
            # Use AI for low-confidence cases
            cost = 0.0
            model_used = "deterministic"
            
            if confidence < 0.7:
                ai_extraction = await self._ai_extract(
                    context,
                    email_content,
                    email_type
                )
                
                if ai_extraction["confidence"] > confidence:
                    extracted_data.update(ai_extraction["data"])
                    confidence = ai_extraction["confidence"]
                
                cost = ai_extraction["cost"]
                model_used = ai_extraction["model"]
            
            email_data = {
                "email_type": email_type,
                "verification_method": self._determine_method(extracted_data),
                "extracted_data": extracted_data,
                "received_at": datetime.utcnow().isoformat(),
                "subject": email_subject
            }
            
            status = AgentStatus.SUCCESS if extracted_data else AgentStatus.PARTIAL
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_name=self.name,
                status=status,
                data=email_data,
                confidence=confidence,
                execution_time=execution_time,
                cost=cost,
                model_used=model_used
            )
            
        except Exception as e:
            self.logger.error(f"Email intelligence error: {str(e)}")
            return self._create_error_result(start_time, str(e))
    
    def get_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate confidence score for extraction."""
        extracted = result.get("extracted_data", {})
        
        if "otp" in extracted:
            return 0.95
        elif "magic_link" in extracted:
            return 0.9
        else:
            return 0.5
    
    # ========================================================================
    # EMAIL CLASSIFICATION
    # ========================================================================
    
    def _classify_email(self, subject: str, content: str) -> str:
        """Classify email by type."""
        combined = (subject + " " + content).lower()
        
        # Check each classification
        for email_type, keywords in self.classification_keywords.items():
            for keyword in keywords:
                if keyword in combined:
                    self.logger.info(f"Classified as: {email_type}")
                    return email_type
        
        return EmailType.UNKNOWN
    
    # ========================================================================
    # DATA EXTRACTION
    # ========================================================================
    
    def _extract_otp(self, content: str) -> Optional[str]:
        """Extract OTP code from email content."""
        for pattern in self.otp_patterns:
            matches = re.findall(pattern, content)
            if matches:
                # Return first match that looks like OTP
                for match in matches:
                    if len(match) in [4, 6, 7, 8]:
                        self.logger.info(f"Extracted OTP: {match}")
                        return match
        
        return None
    
    def _extract_magic_link(self, content: str) -> Optional[str]:
        """Extract magic link from email content."""
        for pattern in self.link_patterns:
            matches = re.findall(pattern, content)
            if matches:
                link = matches[0]
                self.logger.info(f"Extracted magic link: {link[:50]}...")
                return link
        
        return None
    
    def _determine_method(self, extracted_data: Dict[str, Any]) -> str:
        """Determine verification method from extracted data."""
        if "otp" in extracted_data:
            return "otp"
        elif "magic_link" in extracted_data:
            return "magic_link"
        else:
            return "unknown"
    
    # ========================================================================
    # AI ENHANCEMENT
    # ========================================================================
    
    async def _ai_extract(
        self,
        context: AgentContext,
        email_content: str,
        email_type: str
    ) -> Dict[str, Any]:
        """Use AI to extract verification data."""
        model = self.model_router.select_model(
            task_type="otp_extraction",
            confidence=0.6,
            budget_remaining=context.budget_remaining
        )
        
        # Truncate content
        if len(email_content) > 2000:
            email_content = email_content[:2000]
        
        prompt = f"""Extract verification data from this email:

Email Type: {email_type}

Content:
{email_content}

Extract:
- OTP code (if present)
- Magic link (if present)
- Verification link (if present)

Respond in JSON:
{{
    "otp": "code or null",
    "magic_link": "url or null",
    "confidence": 0.0-1.0
}}"""
        
        try:
            input_tokens = len(prompt) // 4
            output_tokens = 100
            
            cost = self.model_router.get_cost_estimate(
                model, input_tokens, output_tokens
            )
            
            self.model_router.track_usage(model, input_tokens, output_tokens)
            
            # Simulate AI extraction
            return {
                "data": {},
                "confidence": 0.7,
                "cost": cost,
                "model": model
            }
            
        except Exception as e:
            self.logger.error(f"AI extraction error: {str(e)}")
            return {
                "data": {},
                "confidence": 0.0,
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
    import asyncio
    from ai_model_router import ModelRouter
    from .base_agent import create_agent_context
    
    console = Console()
    
    console.print("\n[bold cyan]Email Intelligence Agent - Test[/bold cyan]\n")
    
    async def test():
        router = ModelRouter()
        agent = EmailIntelligenceAgent(router)
        
        # Test with sample email
        context = create_agent_context(
            workflow_id="test-123",
            url="https://example.com/signup"
        )
        
        context.metadata["email_subject"] = "Verify your email address"
        context.metadata["email_content"] = """
        Welcome to Example!
        
        Your verification code is: 123456
        
        This code will expire in 10 minutes.
        
        If you didn't request this, please ignore this email.
        """
        
        console.print("[cyan]Analyzing email...[/cyan]")
        result = await agent.execute(context)
        
        console.print(f"\n[green]Analysis Result:[/green]")
        console.print(f"  Status: {result.status.value}")
        console.print(f"  Email Type: {result.data.get('email_type')}")
        console.print(f"  Method: {result.data.get('verification_method')}")
        console.print(f"  Confidence: {result.confidence:.2f}")
        
        extracted = result.data.get("extracted_data", {})
        if extracted:
            console.print(f"\n[cyan]Extracted Data:[/cyan]")
            for key, value in extracted.items():
                console.print(f"  {key}: {value}")
    
    asyncio.run(test())
