#!/usr/bin/env python3
"""
AI Form Analyzer Module
Integrates B.ai API for intelligent form analysis and decision making
Uses AI as fallback when deterministic methods fail
Author: vinayakkumar9000
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from rich.console import Console

console = Console()

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG_FILE = Path(__file__).parent / "config.json"

# Available models with pricing (per 1M tokens)
AVAILABLE_MODELS = {
    "gpt-5.4-mini": {
        "name": "GPT-5.4 Mini",
        "input_price": 0.15,
        "output_price": 0.60,
        "recommended": True,
        "description": "Latest GPT model - fast, accurate, and cost-effective"
    },
    "deepseek-v4-flash": {
        "name": "DeepSeek-V4-Flash",
        "input_price": 0.28,
        "output_price": 0.56,
        "description": "Fast and cost-effective for most tasks"
    },
    "deepseek-v4-pro": {
        "name": "DeepSeek-V4-Pro",
        "input_price": 0.87,
        "output_price": 1.74,
        "description": "More capable for complex reasoning"
    },
    "deepseek-v3.2": {
        "name": "DeepSeek-V3.2",
        "input_price": 0.29,
        "output_price": 0.44,
        "description": "Balanced performance and cost"
    },
    "minimax-m3": {
        "name": "MiniMax-M3",
        "input_price": 0.3,
        "output_price": 1.2,
        "description": "Alternative fast model"
    },
    "kimi-k2.5": {
        "name": "Kimi-K2.5",
        "input_price": 0.59,
        "output_price": 3.0,
        "description": "High quality for difficult tasks"
    }
}

DEFAULT_MODEL = "gpt-5.4-mini"
API_BASE_URL = "https://api.b.ai/v1/chat/completions"


# ============================================================================
# API KEY MANAGEMENT
# ============================================================================

def load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(config: dict) -> None:
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not save config: {e}[/yellow]")


def get_api_key() -> Optional[str]:
    """Get API key from config or prompt user."""
    config = load_config()
    
    if "b_ai_api_key" in config and config["b_ai_api_key"]:
        return config["b_ai_api_key"]
    
    # Prompt user for API key
    console.print("\n[bold cyan]═══ B.ai API Configuration ═══[/bold cyan]")
    console.print("AI features require a B.ai API key for intelligent form analysis.")
    console.print("Get your API key from: https://b.ai/api")
    
    api_key = input("\nEnter your B.ai API key (or press Enter to skip AI features): ").strip()
    
    if api_key:
        config["b_ai_api_key"] = api_key
        config["ai_model"] = config.get("ai_model", DEFAULT_MODEL)
        save_config(config)
        console.print("[green]✓[/green] API key saved to config.json")
        return api_key
    
    console.print("[yellow]⚠[/yellow] AI features disabled. Using deterministic methods only.")
    return None


def get_model() -> str:
    """Get configured model or default."""
    config = load_config()
    return config.get("ai_model", DEFAULT_MODEL)


def set_model(model: str) -> bool:
    """Set the AI model to use."""
    if model not in AVAILABLE_MODELS:
        console.print(f"[red]✗[/red] Invalid model: {model}")
        console.print(f"Available models: {', '.join(AVAILABLE_MODELS.keys())}")
        return False
    
    config = load_config()
    config["ai_model"] = model
    save_config(config)
    console.print(f"[green]✓[/green] Model set to: {AVAILABLE_MODELS[model]['name']}")
    return True


# ============================================================================
# AI API CLIENT
# ============================================================================

class AIClient:
    """Client for B.ai API interactions."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or get_api_key()
        self.model = model or get_model()
        self.enabled = self.api_key is not None
    
    def call_api(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Call B.ai API with given prompt.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
        
        Returns:
            Response text or None if failed
        """
        if not self.enabled:
            return None
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = requests.post(
                API_BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                console.print(f"[yellow]AI API error: {response.status_code}[/yellow]")
                return None
        
        except Exception as e:
            console.print(f"[yellow]AI API call failed: {e}[/yellow]")
            return None


# ============================================================================
# PHASE 1: AI FIELD CLASSIFIER
# ============================================================================

class AIFieldClassifier:
    """Classifies form fields using AI when confidence is low."""
    
    def __init__(self, client: AIClient):
        self.client = client
    
    def classify_field(
        self,
        attributes: Dict[str, str],
        surrounding_text: str,
        confidence_threshold: float = 0.7
    ) -> Tuple[Optional[str], float]:
        """
        Classify a form field using AI.
        
        Args:
            attributes: Field attributes (name, id, placeholder, etc.)
            surrounding_text: Text around the field
            confidence_threshold: Minimum confidence to return result
        
        Returns:
            (field_type, confidence) or (None, 0.0) if failed
        """
        if not self.client.enabled:
            return None, 0.0
        
        system_prompt = """You are a form field classifier. Analyze the field attributes and surrounding text to determine the field type.

Return ONLY a JSON object with this exact format:
{
  "field_type": "email|username|password|confirm_password|otp|phone|first_name|last_name|full_name|date_of_birth|gender|country|checkbox|unknown",
  "confidence": 0.0-1.0
}

Field type definitions:
- email: Email address input
- username: Username or login name
- password: Password input (first occurrence)
- confirm_password: Password confirmation
- otp: One-time password or verification code
- phone: Phone number
- first_name: First/given name
- last_name: Last/family/surname
- full_name: Complete name in one field
- date_of_birth: Birth date
- gender: Gender selection
- country: Country selection
- checkbox: Checkbox for terms/agreements
- unknown: Cannot determine type"""
        
        prompt = f"""Classify this form field:

Attributes:
{json.dumps(attributes, indent=2)}

Surrounding text:
{surrounding_text}

Return JSON only."""
        
        response = self.client.call_api(prompt, system_prompt, temperature=0.2, max_tokens=100)
        
        if not response:
            return None, 0.0
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                result = json.loads(json_match.group())
                field_type = result.get("field_type", "unknown")
                confidence = float(result.get("confidence", 0.0))
                
                if field_type != "unknown" and confidence >= confidence_threshold:
                    return field_type, confidence
        
        except Exception as e:
            console.print(f"[yellow]AI field classification parse error: {e}[/yellow]")
        
        return None, 0.0


# ============================================================================
# PHASE 2: AI NAVIGATION AGENT
# ============================================================================

class AINavigationAgent:
    """Determines next action in multi-step forms."""
    
    def __init__(self, client: AIClient):
        self.client = client
    
    def get_next_action(
        self,
        visible_buttons: List[str],
        page_context: str,
        fields_completed: List[str]
    ) -> Optional[str]:
        """
        Determine which button to click next.
        
        Args:
            visible_buttons: List of visible button texts
            page_context: Page title/heading text
            fields_completed: List of field types already filled
        
        Returns:
            Button text to click or None
        """
        if not self.client.enabled or not visible_buttons:
            return None
        
        system_prompt = """You are a form navigation expert. Analyze the current form state and determine which button should be clicked next.

Return ONLY a JSON object:
{
  "button": "exact button text to click",
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}

If no button should be clicked, return:
{
  "button": null,
  "confidence": 1.0,
  "reason": "explanation"
}"""
        
        prompt = f"""Current form state:

Visible buttons:
{json.dumps(visible_buttons, indent=2)}

Page context: {page_context}

Fields completed: {', '.join(fields_completed) if fields_completed else 'None'}

Which button should be clicked next? Return JSON only."""
        
        response = self.client.call_api(prompt, system_prompt, temperature=0.2, max_tokens=150)
        
        if not response:
            return None
        
        try:
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                button = result.get("button")
                confidence = float(result.get("confidence", 0.0))
                
                if button and confidence >= 0.7:
                    return button
        
        except Exception as e:
            console.print(f"[yellow]AI navigation parse error: {e}[/yellow]")
        
        return None


# ============================================================================
# PHASE 3: AI OTP EXTRACTOR (FALLBACK)
# ============================================================================

class AIOTPExtractor:
    """Extracts OTP from email using AI as fallback."""
    
    def __init__(self, client: AIClient):
        self.client = client
    
    def extract_otp(self, email_content: str) -> Optional[str]:
        """
        Extract OTP from email using AI.
        
        Args:
            email_content: Email body text
        
        Returns:
            OTP code or None
        """
        if not self.client.enabled:
            return None
        
        system_prompt = """You are an OTP extraction expert. Find the verification code in the email.

Return ONLY a JSON object:
{
  "otp": "the numeric code",
  "confidence": 0.0-1.0
}

OTP is typically:
- 4-8 digits
- Labeled as: verification code, OTP, code, PIN, token
- May be formatted with spaces or dashes

If no OTP found, return:
{
  "otp": null,
  "confidence": 0.0
}"""
        
        # Truncate email if too long
        if len(email_content) > 2000:
            email_content = email_content[:2000] + "..."
        
        prompt = f"""Extract the OTP/verification code from this email:

{email_content}

Return JSON only."""
        
        response = self.client.call_api(prompt, system_prompt, temperature=0.1, max_tokens=100)
        
        if not response:
            return None
        
        try:
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                result = json.loads(json_match.group())
                otp = result.get("otp")
                confidence = float(result.get("confidence", 0.0))
                
                if otp and confidence >= 0.8:
                    # Clean OTP (remove spaces, dashes)
                    otp = re.sub(r'[^0-9]', '', str(otp))
                    if 4 <= len(otp) <= 8:
                        return otp
        
        except Exception as e:
            console.print(f"[yellow]AI OTP extraction parse error: {e}[/yellow]")
        
        return None


# ============================================================================
# PHASE 4: AI MAGIC LINK CLASSIFIER
# ============================================================================

class AIMagicLinkClassifier:
    """Identifies verification links in emails."""
    
    def __init__(self, client: AIClient):
        self.client = client
    
    def identify_verification_link(
        self,
        email_subject: str,
        email_body: str,
        links: List[str]
    ) -> Optional[str]:
        """
        Identify the verification/magic link from email.
        
        Args:
            email_subject: Email subject line
            email_body: Email body text
            links: List of URLs found in email
        
        Returns:
            Verification link URL or None
        """
        if not self.client.enabled or not links:
            return None
        
        system_prompt = """You are an email link classifier. Identify the verification/magic link from the list.

Return ONLY a JSON object:
{
  "verification_link": "the URL",
  "confidence": 0.0-1.0
}

Verification links typically:
- Contain: verify, confirm, activate, magic, auth, token
- Are NOT: unsubscribe, privacy, support, help, login (to existing account)

If no verification link found, return:
{
  "verification_link": null,
  "confidence": 0.0
}"""
        
        # Truncate if too long
        if len(email_body) > 1500:
            email_body = email_body[:1500] + "..."
        
        prompt = f"""Identify the verification link:

Subject: {email_subject}

Body excerpt:
{email_body}

Available links:
{json.dumps(links, indent=2)}

Return JSON only."""
        
        response = self.client.call_api(prompt, system_prompt, temperature=0.2, max_tokens=150)
        
        if not response:
            return None
        
        try:
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                link = result.get("verification_link")
                confidence = float(result.get("confidence", 0.0))
                
                if link and confidence >= 0.8:
                    return link
        
        except Exception as e:
            console.print(f"[yellow]AI magic link parse error: {e}[/yellow]")
        
        return None


# ============================================================================
# UNIFIED AI HELPER
# ============================================================================

class AIFormHelper:
    """Unified AI helper for form automation."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.client = AIClient(api_key, model)
        self.field_classifier = AIFieldClassifier(self.client)
        self.navigation_agent = AINavigationAgent(self.client)
        self.otp_extractor = AIOTPExtractor(self.client)
        self.magic_link_classifier = AIMagicLinkClassifier(self.client)
    
    @property
    def enabled(self) -> bool:
        """Check if AI features are enabled."""
        return self.client.enabled
    
    def classify_field(self, attributes: Dict, surrounding_text: str) -> Tuple[Optional[str], float]:
        """Classify form field."""
        return self.field_classifier.classify_field(attributes, surrounding_text)
    
    def get_next_button(self, buttons: List[str], context: str, completed: List[str]) -> Optional[str]:
        """Get next button to click."""
        return self.navigation_agent.get_next_action(buttons, context, completed)
    
    def extract_otp(self, email_content: str) -> Optional[str]:
        """Extract OTP from email."""
        return self.otp_extractor.extract_otp(email_content)
    
    def find_magic_link(self, subject: str, body: str, links: List[str]) -> Optional[str]:
        """Find verification link."""
        return self.magic_link_classifier.identify_verification_link(subject, body, links)


# ============================================================================
# CLI FOR TESTING
# ============================================================================

if __name__ == "__main__":
    console.print("[bold cyan]AI Form Analyzer - Configuration[/bold cyan]\n")
    
    # Show available models
    console.print("[bold]Available Models:[/bold]")
    for model_id, info in AVAILABLE_MODELS.items():
        recommended = " [green](Recommended)[/green]" if info.get("recommended") else ""
        console.print(f"  • {info['name']}{recommended}")
        console.print(f"    {info['description']}")
        console.print(f"    Cost: ${info['input_price']}/M input, ${info['output_price']}/M output\n")
    
    # Get or set API key
    api_key = get_api_key()
    
    if api_key:
        console.print(f"\n[green]✓[/green] AI features enabled")
        console.print(f"Current model: {AVAILABLE_MODELS[get_model()]['name']}")
