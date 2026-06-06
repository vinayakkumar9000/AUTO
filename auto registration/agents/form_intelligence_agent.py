#!/usr/bin/env python3
"""
Form Intelligence Agent
Semantic understanding and intelligent field mapping for registration forms
Author: vinayakkumar9000
"""

import re
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .base_agent import BaseAgent, AgentResult, AgentContext, AgentStatus
from ai_model_router import ModelRouter
import logging

# ============================================================================
# FIELD TYPES
# ============================================================================

class FieldType:
    """Standard field types for registration forms."""
    EMAIL = "email"
    PASSWORD = "password"
    PASSWORD_CONFIRM = "password_confirm"
    USERNAME = "username"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    FULL_NAME = "full_name"
    PHONE = "phone"
    OTP = "otp"
    VERIFICATION_CODE = "verification_code"
    CAPTCHA = "captcha"
    TERMS = "terms"
    NEWSLETTER = "newsletter"
    COUNTRY = "country"
    DATE_OF_BIRTH = "date_of_birth"
    COMPANY = "company"
    UNKNOWN = "unknown"

# ============================================================================
# FORM INTELLIGENCE AGENT
# ============================================================================

class FormIntelligenceAgent(BaseAgent):
    """
    Form Intelligence Agent - Semantic form understanding.
    
    Responsibilities:
    - Semantic field understanding
    - Field type classification
    - Selector generation
    - Dynamic form handling
    - Multi-step form support
    - Field mapping to identity data
    """
    
    def __init__(
        self,
        model_router: ModelRouter,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Form Intelligence Agent.
        
        Args:
            model_router: Model router instance
            logger: Optional logger instance
        """
        super().__init__("form_intelligence", model_router, logger)
        
        # Field detection patterns
        self.field_patterns = {
            FieldType.EMAIL: {
                "name": [r"email", r"e-mail", r"mail", r"user_email"],
                "id": [r"email", r"e-mail", r"mail", r"user_email"],
                "type": [r"email"],
                "placeholder": [r"email", r"e-mail", r"your email"],
                "label": [r"email", r"e-mail address"]
            },
            FieldType.PASSWORD: {
                "name": [r"password", r"passwd", r"pwd", r"pass"],
                "id": [r"password", r"passwd", r"pwd"],
                "type": [r"password"],
                "placeholder": [r"password", r"enter password"],
                "label": [r"password", r"create password"]
            },
            FieldType.PASSWORD_CONFIRM: {
                "name": [r"confirm", r"password2", r"repeat", r"retype"],
                "id": [r"confirm", r"password2", r"repeat"],
                "placeholder": [r"confirm", r"repeat password"],
                "label": [r"confirm password", r"repeat password"]
            },
            FieldType.USERNAME: {
                "name": [r"username", r"user_name", r"login", r"handle"],
                "id": [r"username", r"user_name", r"login"],
                "placeholder": [r"username", r"choose username"],
                "label": [r"username", r"user name"]
            },
            FieldType.FIRST_NAME: {
                "name": [r"first_name", r"firstname", r"fname", r"given_name"],
                "id": [r"first_name", r"firstname", r"fname"],
                "placeholder": [r"first name", r"given name"],
                "label": [r"first name", r"given name"]
            },
            FieldType.LAST_NAME: {
                "name": [r"last_name", r"lastname", r"lname", r"surname", r"family_name"],
                "id": [r"last_name", r"lastname", r"lname"],
                "placeholder": [r"last name", r"surname"],
                "label": [r"last name", r"surname", r"family name"]
            },
            FieldType.FULL_NAME: {
                "name": [r"^name$", r"full_name", r"fullname"],
                "id": [r"^name$", r"full_name", r"fullname"],
                "placeholder": [r"full name", r"your name"],
                "label": [r"^name$", r"full name"]
            },
            FieldType.PHONE: {
                "name": [r"phone", r"mobile", r"telephone", r"tel"],
                "id": [r"phone", r"mobile", r"telephone"],
                "type": [r"tel"],
                "placeholder": [r"phone", r"mobile", r"telephone"],
                "label": [r"phone", r"mobile number"]
            },
            FieldType.OTP: {
                "name": [r"otp", r"code", r"token", r"verification", r"verify"],
                "id": [r"otp", r"code", r"token", r"verification"],
                "placeholder": [r"enter code", r"verification code", r"6-digit"],
                "label": [r"verification code", r"otp", r"enter code"]
            },
            FieldType.TERMS: {
                "name": [r"terms", r"agree", r"accept", r"consent"],
                "id": [r"terms", r"agree", r"accept"],
                "type": [r"checkbox"],
                "label": [r"terms", r"agree to", r"accept"]
            }
        }
        
        # Selector strategies (in order of preference)
        self.selector_strategies = [
            "id",           # Most reliable
            "name",         # Very reliable
            "type",         # Good for specific types
            "placeholder",  # Decent fallback
            "label",        # Last resort
            "aria-label"    # Accessibility
        ]
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Analyze form and classify fields.
        
        Args:
            context: Execution context with page content
        
        Returns:
            AgentResult with field mappings
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Analyzing form for {context.domain}")
            
            page_content = context.page_content or ""
            
            if not page_content:
                return self._create_error_result(
                    start_time,
                    "No page content available"
                )
            
            # Get domain intelligence
            domain_profile = context.metadata.get("domain_profile")
            
            # Check for cached selectors
            if domain_profile and domain_profile.known_selectors:
                cached_fields = self._use_cached_selectors(domain_profile)
                if cached_fields:
                    self.logger.info(f"Using {len(cached_fields)} cached selectors")
                    
                    return AgentResult(
                        agent_name=self.name,
                        status=AgentStatus.SUCCESS,
                        data={
                            "fields": cached_fields,
                            "form_type": "registration",
                            "multi_step": False,
                            "cached": True
                        },
                        confidence=0.9,
                        execution_time=time.time() - start_time,
                        cost=0.0,
                        model_used="cached"
                    )
            
            # Extract form fields
            fields = self._extract_fields(page_content)
            
            # Classify fields
            classified_fields = self._classify_fields(fields)
            
            # Generate selectors
            field_mappings = self._generate_selectors(classified_fields)
            
            # Detect multi-step forms
            multi_step = self._detect_multi_step(page_content)
            
            # Calculate confidence
            confidence = self._calculate_confidence(field_mappings, fields)
            
            # Use AI for low-confidence cases
            cost = 0.0
            model_used = "deterministic"
            
            if confidence < 0.7:
                ai_analysis = await self._ai_analyze_form(
                    context,
                    page_content,
                    field_mappings
                )
                
                if ai_analysis["confidence"] > confidence:
                    field_mappings = ai_analysis["fields"]
                    confidence = ai_analysis["confidence"]
                
                cost = ai_analysis["cost"]
                model_used = ai_analysis["model"]
            
            form_data = {
                "fields": field_mappings,
                "form_type": "registration",
                "multi_step": multi_step,
                "total_fields": len(field_mappings),
                "required_fields": self._count_required_fields(field_mappings),
                "cached": False
            }
            
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.SUCCESS,
                data=form_data,
                confidence=confidence,
                execution_time=execution_time,
                cost=cost,
                model_used=model_used
            )
            
        except Exception as e:
            self.logger.error(f"Form analysis error: {str(e)}")
            return self._create_error_result(start_time, str(e))
    
    def get_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate confidence score for form analysis."""
        fields = result.get("fields", {})
        
        # Base confidence
        confidence = 0.5
        
        # Increase confidence for each identified field
        if FieldType.EMAIL in fields:
            confidence += 0.2
        if FieldType.PASSWORD in fields:
            confidence += 0.15
        
        # Bonus for cached results
        if result.get("cached"):
            confidence += 0.15
        
        return min(confidence, 1.0)
    
    # ========================================================================
    # FIELD EXTRACTION
    # ========================================================================
    
    def _extract_fields(self, content: str) -> List[Dict[str, Any]]:
        """Extract input fields from page content."""
        fields = []
        
        # Extract input tags
        input_pattern = r'<input[^>]*>'
        for match in re.finditer(input_pattern, content, re.IGNORECASE):
            field = self._parse_input_tag(match.group())
            if field:
                fields.append(field)
        
        # Extract textarea tags
        textarea_pattern = r'<textarea[^>]*>'
        for match in re.finditer(textarea_pattern, content, re.IGNORECASE):
            field = self._parse_textarea_tag(match.group())
            if field:
                fields.append(field)
        
        return fields
    
    def _parse_input_tag(self, tag: str) -> Optional[Dict[str, Any]]:
        """Parse input tag attributes."""
        field = {"tag": "input"}
        
        # Extract attributes
        attributes = {
            "type": r'type=["\']([^"\']+)["\']',
            "name": r'name=["\']([^"\']+)["\']',
            "id": r'id=["\']([^"\']+)["\']',
            "placeholder": r'placeholder=["\']([^"\']+)["\']',
            "aria-label": r'aria-label=["\']([^"\']+)["\']',
            "required": r'required'
        }
        
        for attr, pattern in attributes.items():
            match = re.search(pattern, tag, re.IGNORECASE)
            if match:
                if attr == "required":
                    field[attr] = True
                else:
                    field[attr] = match.group(1) if match.lastindex else True
        
        return field if len(field) > 1 else None
    
    def _parse_textarea_tag(self, tag: str) -> Optional[Dict[str, Any]]:
        """Parse textarea tag attributes."""
        field = {"tag": "textarea", "type": "textarea"}
        
        # Extract attributes (same as input)
        attributes = {
            "name": r'name=["\']([^"\']+)["\']',
            "id": r'id=["\']([^"\']+)["\']',
            "placeholder": r'placeholder=["\']([^"\']+)["\']',
            "required": r'required'
        }
        
        for attr, pattern in attributes.items():
            match = re.search(pattern, tag, re.IGNORECASE)
            if match:
                if attr == "required":
                    field[attr] = True
                else:
                    field[attr] = match.group(1)
        
        return field if len(field) > 2 else None
    
    # ========================================================================
    # FIELD CLASSIFICATION
    # ========================================================================
    
    def _classify_fields(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classify fields by type."""
        classified = []
        
        for field in fields:
            field_type = self._classify_field(field)
            field["field_type"] = field_type
            classified.append(field)
        
        return classified
    
    def _classify_field(self, field: Dict[str, Any]) -> str:
        """Classify a single field."""
        # Check each field type pattern
        for field_type, patterns in self.field_patterns.items():
            for attr, attr_patterns in patterns.items():
                if attr in field:
                    field_value = str(field[attr]).lower()
                    
                    for pattern in attr_patterns:
                        if re.search(pattern, field_value, re.IGNORECASE):
                            return field_type
        
        return FieldType.UNKNOWN
    
    # ========================================================================
    # SELECTOR GENERATION
    # ========================================================================
    
    def _generate_selectors(
        self,
        fields: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Generate selectors for each field type."""
        selectors = {}
        
        for field in fields:
            field_type = field.get("field_type")
            
            if field_type == FieldType.UNKNOWN:
                continue
            
            # Generate selector
            selector = self._generate_selector(field)
            
            if selector:
                selectors[field_type] = {
                    "selector": selector,
                    "type": field.get("type", "text"),
                    "required": field.get("required", False),
                    "attributes": {
                        "name": field.get("name"),
                        "id": field.get("id"),
                        "placeholder": field.get("placeholder")
                    }
                }
        
        return selectors
    
    def _generate_selector(self, field: Dict[str, Any]) -> Optional[str]:
        """Generate CSS selector for field."""
        # Try strategies in order of preference
        if "id" in field:
            return f"#{field['id']}"
        
        if "name" in field:
            return f"input[name='{field['name']}']"
        
        if "type" in field and "placeholder" in field:
            return f"input[type='{field['type']}'][placeholder*='{field['placeholder'][:20]}']"
        
        if "type" in field:
            return f"input[type='{field['type']}']"
        
        return None
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _use_cached_selectors(self, domain_profile: Any) -> Dict[str, Dict[str, Any]]:
        """Use cached selectors from domain profile."""
        cached = {}
        
        for field_type, selectors in domain_profile.known_selectors.items():
            if selectors:
                cached[field_type] = {
                    "selector": selectors[0],  # Use first (best) selector
                    "type": "text",
                    "required": field_type in [FieldType.EMAIL, FieldType.PASSWORD],
                    "cached": True
                }
        
        return cached
    
    def _detect_multi_step(self, content: str) -> bool:
        """Detect if form is multi-step."""
        multi_step_indicators = [
            r"step \d+",
            r"next step",
            r"continue",
            r"progress",
            r"wizard"
        ]
        
        content_lower = content.lower()
        
        for indicator in multi_step_indicators:
            if re.search(indicator, content_lower):
                return True
        
        return False
    
    def _count_required_fields(self, fields: Dict[str, Dict[str, Any]]) -> int:
        """Count required fields."""
        return sum(1 for field in fields.values() if field.get("required", False))
    
    def _calculate_confidence(
        self,
        field_mappings: Dict[str, Dict[str, Any]],
        all_fields: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence in field classification."""
        if not all_fields:
            return 0.0
        
        # Base confidence
        confidence = 0.5
        
        # Increase confidence for each classified field
        classified_count = len(field_mappings)
        total_count = len(all_fields)
        
        classification_rate = classified_count / total_count
        confidence += classification_rate * 0.3
        
        # Bonus for finding essential fields
        if FieldType.EMAIL in field_mappings:
            confidence += 0.1
        if FieldType.PASSWORD in field_mappings:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    # ========================================================================
    # AI ENHANCEMENT
    # ========================================================================
    
    async def _ai_analyze_form(
        self,
        context: AgentContext,
        page_content: str,
        current_mappings: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use AI to enhance form analysis."""
        model = self.model_router.select_model(
            task_type="form_analysis",
            confidence=0.6,
            budget_remaining=context.budget_remaining
        )
        
        # Truncate content
        if len(page_content) > 3000:
            page_content = page_content[:3000]
        
        prompt = f"""Analyze this registration form and identify field types:

Current Mappings:
{json.dumps(current_mappings, indent=2)}

Page Content (truncated):
{page_content}

Identify: email, password, username, name fields, etc.
Respond in JSON:
{{
    "fields": {{"field_type": {{"selector": "...", "confidence": 0.0-1.0}}}},
    "confidence": 0.0-1.0
}}"""
        
        try:
            import json
            
            input_tokens = len(prompt) // 4
            output_tokens = 200
            
            cost = self.model_router.get_cost_estimate(
                model, input_tokens, output_tokens
            )
            
            self.model_router.track_usage(model, input_tokens, output_tokens)
            
            # Return enhanced mappings
            return {
                "fields": current_mappings,
                "confidence": 0.75,
                "cost": cost,
                "model": model
            }
            
        except Exception as e:
            self.logger.error(f"AI form analysis error: {str(e)}")
            return {
                "fields": current_mappings,
                "confidence": 0.6,
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
    
    console.print("\n[bold cyan]Form Intelligence Agent - Test[/bold cyan]\n")
    
    async def test():
        router = ModelRouter()
        agent = FormIntelligenceAgent(router)
        
        # Test with sample HTML
        sample_html = """
        <form id="signup-form">
            <input type="email" name="email" id="user_email" placeholder="Enter your email" required />
            <input type="password" name="password" id="pwd" placeholder="Create password" required />
            <input type="password" name="confirm_password" placeholder="Confirm password" required />
            <input type="text" name="username" placeholder="Choose username" />
            <input type="checkbox" name="terms" required /> I agree to terms
            <button type="submit">Sign Up</button>
        </form>
        """
        
        context = create_agent_context(
            workflow_id="test-123",
            url="https://example.com/signup"
        )
        context.page_content = sample_html
        
        console.print("[cyan]Analyzing form...[/cyan]")
        result = await agent.execute(context)
        
        console.print(f"\n[green]Analysis Result:[/green]")
        console.print(f"  Status: {result.status.value}")
        console.print(f"  Confidence: {result.confidence:.2f}")
        console.print(f"  Total Fields: {result.data.get('total_fields')}")
        console.print(f"  Required: {result.data.get('required_fields')}")
        console.print(f"  Multi-step: {result.data.get('multi_step')}")
        
        if result.data.get("fields"):
            console.print(f"\n[cyan]Field Mappings:[/cyan]")
            table = Table()
            table.add_column("Field Type", style="cyan")
            table.add_column("Selector", style="yellow")
            table.add_column("Required", style="green")
            
            for field_type, field_data in result.data["fields"].items():
                selector = field_data.get("selector", "N/A")
                required = "✓" if field_data.get("required") else "✗"
                table.add_row(field_type, selector, required)
            
            console.print(table)
    
    asyncio.run(test())
