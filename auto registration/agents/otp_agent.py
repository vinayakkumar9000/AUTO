#!/usr/bin/env python3
"""
OTP Agent
Multi-format OTP extraction with validation and retry handling
Author: vinayakkumar9000
"""

import re
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from .base_agent import BaseAgent, AgentResult, AgentContext, AgentStatus
from ai_model_router import ModelRouter
import logging

# ============================================================================
# OTP FORMATS
# ============================================================================

class OTPFormat:
    """Supported OTP formats."""
    FOUR_DIGIT = "4-digit"
    SIX_DIGIT = "6-digit"
    SEVEN_DIGIT = "7-digit"
    EIGHT_DIGIT = "8-digit"
    ALPHANUMERIC = "alphanumeric"
    UNKNOWN = "unknown"

# ============================================================================
# OTP AGENT
# ============================================================================

class OTPAgent(BaseAgent):
    """
    OTP Agent - Multi-format OTP extraction and validation.
    
    Responsibilities:
    - Extract OTP from various sources (email, SMS, image)
    - Validate OTP format
    - Handle retries
    - Track expiration
    - Support multiple formats (4-8 digits, alphanumeric)
    - Image OCR support
    - AI fallback for complex cases
    """
    
    def __init__(
        self,
        model_router: ModelRouter,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize OTP Agent.
        
        Args:
            model_router: Model router instance
            logger: Optional logger instance
        """
        super().__init__("otp", model_router, logger)
        
        # OTP extraction patterns (ordered by specificity)
        self.otp_patterns = [
            # Exact format patterns
            (r'\b(\d{6})\b', OTPFormat.SIX_DIGIT, 0.95),
            (r'\b(\d{4})\b', OTPFormat.FOUR_DIGIT, 0.90),
            (r'\b(\d{7})\b', OTPFormat.SEVEN_DIGIT, 0.85),
            (r'\b(\d{8})\b', OTPFormat.EIGHT_DIGIT, 0.85),
            (r'\b([A-Z0-9]{6})\b', OTPFormat.ALPHANUMERIC, 0.80),
            
            # Context-aware patterns
            (r'code[:\s]+(\d+)', OTPFormat.SIX_DIGIT, 0.90),
            (r'token[:\s]+(\d+)', OTPFormat.SIX_DIGIT, 0.90),
            (r'verification[:\s]+(\d+)', OTPFormat.SIX_DIGIT, 0.90),
            (r'otp[:\s]+(\d+)', OTPFormat.SIX_DIGIT, 0.90),
            (r'pin[:\s]+(\d+)', OTPFormat.FOUR_DIGIT, 0.85),
            
            # Formatted patterns
            (r'(\d{3}[-\s]\d{3})', OTPFormat.SIX_DIGIT, 0.85),
            (r'(\d{4}[-\s]\d{4})', OTPFormat.EIGHT_DIGIT, 0.85),
        ]
        
        # Validation rules
        self.validation_rules = {
            OTPFormat.FOUR_DIGIT: lambda x: len(x) == 4 and x.isdigit(),
            OTPFormat.SIX_DIGIT: lambda x: len(x) == 6 and x.isdigit(),
            OTPFormat.SEVEN_DIGIT: lambda x: len(x) == 7 and x.isdigit(),
            OTPFormat.EIGHT_DIGIT: lambda x: len(x) == 8 and x.isdigit(),
            OTPFormat.ALPHANUMERIC: lambda x: len(x) == 6 and x.isalnum(),
        }
        
        # Default expiration times (seconds)
        self.expiration_times = {
            OTPFormat.FOUR_DIGIT: 300,   # 5 minutes
            OTPFormat.SIX_DIGIT: 600,    # 10 minutes
            OTPFormat.SEVEN_DIGIT: 600,  # 10 minutes
            OTPFormat.EIGHT_DIGIT: 900,  # 15 minutes
            OTPFormat.ALPHANUMERIC: 600, # 10 minutes
        }
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Extract and validate OTP.
        
        Args:
            context: Execution context with OTP source
        
        Returns:
            AgentResult with OTP data
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Extracting OTP for {context.domain}")
            
            # Get OTP source
            source_text = context.metadata.get("otp_source", "")
            source_type = context.metadata.get("source_type", "text")
            
            if not source_text:
                return self._create_error_result(
                    start_time,
                    "No OTP source provided"
                )
            
            # Extract OTP using multiple methods
            extraction_results = []
            
            # Method 1: Pattern matching
            pattern_result = self._extract_by_pattern(source_text)
            if pattern_result:
                extraction_results.append(pattern_result)
            
            # Method 2: Context-aware extraction
            context_result = self._extract_by_context(source_text)
            if context_result:
                extraction_results.append(context_result)
            
            # Method 3: Image OCR (if source is image)
            if source_type == "image":
                ocr_result = await self._extract_from_image(context)
                if ocr_result:
                    extraction_results.append(ocr_result)
            
            # Select best result
            if extraction_results:
                best_result = max(extraction_results, key=lambda x: x["confidence"])
                otp = best_result["otp"]
                otp_format = best_result["format"]
                confidence = best_result["confidence"]
                cost = 0.0
                model_used = "deterministic"
            else:
                # Method 4: AI fallback
                ai_result = await self._ai_extract_otp(context, source_text)
                otp = ai_result.get("otp")
                otp_format = ai_result.get("format", OTPFormat.UNKNOWN)
                confidence = ai_result.get("confidence", 0.0)
                cost = ai_result.get("cost", 0.0)
                model_used = ai_result.get("model", "ai")
            
            if not otp:
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.FAILURE,
                    data={"otp": None, "reason": "No OTP found"},
                    confidence=0.0,
                    execution_time=time.time() - start_time,
                    cost=cost,
                    model_used=model_used
                )
            
            # Validate OTP
            is_valid = self._validate_otp(otp, otp_format)
            
            # Calculate expiration
            expires_at = self._calculate_expiration(otp_format)
            
            otp_data = {
                "otp": otp,
                "format": otp_format,
                "valid": is_valid,
                "expires_at": expires_at.isoformat(),
                "expires_in": self.expiration_times.get(otp_format, 600),
                "extracted_at": datetime.utcnow().isoformat()
            }
            
            status = AgentStatus.SUCCESS if is_valid else AgentStatus.PARTIAL
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_name=self.name,
                status=status,
                data=otp_data,
                confidence=confidence if is_valid else confidence * 0.7,
                execution_time=execution_time,
                cost=cost,
                model_used=model_used
            )
            
        except Exception as e:
            self.logger.error(f"OTP extraction error: {str(e)}")
            return self._create_error_result(start_time, str(e))
    
    def get_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate confidence score for OTP extraction."""
        if not result.get("otp"):
            return 0.0
        
        if result.get("valid"):
            return 0.95
        else:
            return 0.5
    
    # ========================================================================
    # EXTRACTION METHODS
    # ========================================================================
    
    def _extract_by_pattern(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract OTP using regex patterns."""
        for pattern, otp_format, base_confidence in self.otp_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            for match in matches:
                # Clean match
                otp = re.sub(r'[-\s]', '', match)
                
                # Validate format
                if self._validate_otp(otp, otp_format):
                    self.logger.info(f"Extracted OTP via pattern: {otp} ({otp_format})")
                    return {
                        "otp": otp,
                        "format": otp_format,
                        "confidence": base_confidence,
                        "method": "pattern"
                    }
        
        return None
    
    def _extract_by_context(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract OTP using contextual clues."""
        # Look for OTP near keywords
        keywords = ["code", "otp", "token", "verification", "pin"]
        
        for keyword in keywords:
            # Find keyword position
            keyword_pos = text.lower().find(keyword)
            if keyword_pos == -1:
                continue
            
            # Extract surrounding text (50 chars after keyword)
            context_text = text[keyword_pos:keyword_pos + 50]
            
            # Try to find digits
            digits = re.findall(r'\d+', context_text)
            for digit_str in digits:
                if len(digit_str) in [4, 6, 7, 8]:
                    otp_format = self._determine_format(digit_str)
                    if self._validate_otp(digit_str, otp_format):
                        self.logger.info(f"Extracted OTP via context: {digit_str}")
                        return {
                            "otp": digit_str,
                            "format": otp_format,
                            "confidence": 0.85,
                            "method": "context"
                        }
        
        return None
    
    async def _extract_from_image(self, context: AgentContext) -> Optional[Dict[str, Any]]:
        """Extract OTP from image using OCR."""
        # Placeholder for OCR implementation
        # Would integrate with image_otp_extractor.py
        self.logger.info("Image OCR extraction not yet implemented")
        return None
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    def _validate_otp(self, otp: str, otp_format: str) -> bool:
        """Validate OTP format."""
        if otp_format in self.validation_rules:
            return self.validation_rules[otp_format](otp)
        return False
    
    def _determine_format(self, otp: str) -> str:
        """Determine OTP format from string."""
        length = len(otp)
        
        if length == 4 and otp.isdigit():
            return OTPFormat.FOUR_DIGIT
        elif length == 6 and otp.isdigit():
            return OTPFormat.SIX_DIGIT
        elif length == 7 and otp.isdigit():
            return OTPFormat.SEVEN_DIGIT
        elif length == 8 and otp.isdigit():
            return OTPFormat.EIGHT_DIGIT
        elif length == 6 and otp.isalnum():
            return OTPFormat.ALPHANUMERIC
        
        return OTPFormat.UNKNOWN
    
    def _calculate_expiration(self, otp_format: str) -> datetime:
        """Calculate OTP expiration time."""
        expiration_seconds = self.expiration_times.get(otp_format, 600)
        return datetime.utcnow() + timedelta(seconds=expiration_seconds)
    
    # ========================================================================
    # AI FALLBACK
    # ========================================================================
    
    async def _ai_extract_otp(
        self,
        context: AgentContext,
        source_text: str
    ) -> Dict[str, Any]:
        """Use AI to extract OTP when patterns fail."""
        model = self.model_router.select_model(
            task_type="otp_extraction",
            confidence=0.5,
            budget_remaining=context.budget_remaining
        )
        
        # Truncate text
        if len(source_text) > 1000:
            source_text = source_text[:1000]
        
        prompt = f"""Extract the OTP/verification code from this text:

{source_text}

The OTP is typically:
- 4, 6, 7, or 8 digits
- May be alphanumeric (6 characters)
- Near keywords like "code", "otp", "token", "verification"

Respond in JSON:
{{
    "otp": "extracted_code",
    "format": "4-digit|6-digit|7-digit|8-digit|alphanumeric",
    "confidence": 0.0-1.0
}}"""
        
        try:
            input_tokens = len(prompt) // 4
            output_tokens = 50
            
            cost = self.model_router.get_cost_estimate(
                model, input_tokens, output_tokens
            )
            
            self.model_router.track_usage(model, input_tokens, output_tokens)
            
            # Simulate AI extraction
            return {
                "otp": None,
                "format": OTPFormat.UNKNOWN,
                "confidence": 0.0,
                "cost": cost,
                "model": model
            }
            
        except Exception as e:
            self.logger.error(f"AI OTP extraction error: {str(e)}")
            return {
                "otp": None,
                "format": OTPFormat.UNKNOWN,
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
    
    console.print("\n[bold cyan]OTP Agent - Test[/bold cyan]\n")
    
    async def test():
        router = ModelRouter()
        agent = OTPAgent(router)
        
        # Test cases
        test_cases = [
            ("Your verification code is: 123456", "6-digit"),
            ("OTP: 1234", "4-digit"),
            ("Token: 1234567", "7-digit"),
            ("Code 123-456", "6-digit"),
            ("Your code: ABC123", "alphanumeric"),
        ]
        
        for source_text, expected_format in test_cases:
            context = create_agent_context(
                workflow_id="test-123",
                url="https://example.com/signup"
            )
            context.metadata["otp_source"] = source_text
            context.metadata["source_type"] = "text"
            
            console.print(f"\n[cyan]Testing:[/cyan] {source_text}")
            result = await agent.execute(context)
            
            if result.status == AgentStatus.SUCCESS:
                console.print(f"  [green]✓[/green] OTP: {result.data.get('otp')}")
                console.print(f"  Format: {result.data.get('format')}")
                console.print(f"  Confidence: {result.confidence:.2f}")
            else:
                console.print(f"  [red]✗[/red] Failed to extract OTP")
    
    asyncio.run(test())
