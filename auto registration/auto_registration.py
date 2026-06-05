#!/usr/bin/env python3
"""
Auto Registration Workflow v2.1
Universal, robust, and lightweight automation for registration forms
Author: vinayakkumar9000
"""

import asyncio
import html
import json
import re
import sys
import time
import random
import string
from pathlib import Path
from typing import Optional, Tuple, Callable, Any

import requests
from playwright.async_api import async_playwright, Page, Browser
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "tempmail"))
sys.path.insert(0, str(Path(__file__).parent.parent / "identity"))

from identity_generator import generate_identity

console = Console()
CONFIG_FILE = Path(__file__).parent / "config.json"

# ============================================================================
# UNIVERSAL REGEX PATTERNS (FIXED)
# ============================================================================

# Fixed: Removed 'username' and bare 'mail' to avoid false positives
EMAIL_PATTERN = re.compile(r'(email|e[\-_]?mail)', re.IGNORECASE)

# Fixed: Removed 'confirm', 'auth', and 'pin' to avoid matching password/author/pincode fields
OTP_PATTERN = re.compile(r'(otp|code|verif|2fa|mfa|one[\-_]?time)', re.IGNORECASE)

# Fixed: More specific patterns, includes 'email' on right side
SEND_PATTERN = re.compile(r'(send|get|request|resend|generate)[\s\-_]*(code|otp|pin|verif|email)', re.IGNORECASE)

# Fixed: Restored common submit terms while avoiding SEND overlap
SUBMIT_PATTERN = re.compile(r'(submit|verify|confirm|continue|next|proceed|validate|done|finish|complete)', re.IGNORECASE)

# Fixed: Forward-only OTP regex to avoid matching order numbers before keywords
OTP_CONTEXT_REGEX = re.compile(r'(?:code|otp|verif|pin)[\s\S]{0,50}?(\d{4,8})', re.IGNORECASE)
OTP_FALLBACK_REGEX = re.compile(r'\b(\d{6})\b')  # Fallback: prefer 6-digit codes

# ============================================================================
# CONFIGURATION MANAGEMENT
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
    except Exception:
        pass

def get_api_key() -> str:
    """Get API key from config or prompt user."""
    config = load_config()
    if "freemodel_api_key" in config and config["freemodel_api_key"]:
        return config["freemodel_api_key"]
    
    console.print("\n[cyan]FreeModel API Key Required[/cyan]")
    console.print("Get your key from: https://freemodel.dev")
    api_key = Prompt.ask("Enter your FreeModel API key", password=True)
    
    config["freemodel_api_key"] = api_key
    save_config(config)
    return api_key

# ============================================================================
# RETRY HELPERS (FIXED)
# ============================================================================

async def retry_async(fn: Callable, retries: int = 3, delay: float = 1.5, label: str = "step") -> Any:
    """Retry async function with fixed delay."""
    for attempt in range(retries):
        try:
            return await fn()
        except Exception as e:
            if attempt == retries - 1:
                raise
            console.print(f"[yellow]Retry {label} ({attempt + 1}/{retries}): {e}[/yellow]")
            await asyncio.sleep(delay)

def retry_sync(fn: Callable, retries: int = 3, delay: float = 1.5, label: str = "step") -> Any:
    """Retry sync function with fixed delay."""
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if attempt == retries - 1:
                raise
            console.print(f"[yellow]Retry {label} ({attempt + 1}/{retries}): {e}[/yellow]")
            time.sleep(delay)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _rand_string(length: int) -> str:
    """Generate random string."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# ============================================================================
# EMAIL PROVIDER: MAIL.TM (FIXED)
# ============================================================================

def generate_mailtm_email() -> Tuple[str, str, str]:
    """Generate mail.tm email. Returns: (email, password, auth_token)"""
    BASE = "https://api.mail.tm"
    
    domains_res = requests.get(f"{BASE}/domains?page=1", timeout=15)
    domains_res.raise_for_status()
    domain = domains_res.json()["hydra:member"][0]["domain"]
    
    local_part = _rand_string(10)
    address = f"{local_part}@{domain}"
    password = _rand_string(12)
    
    account_res = requests.post(f"{BASE}/accounts", json={"address": address, "password": password}, timeout=15)
    account_res.raise_for_status()
    
    token_res = requests.post(f"{BASE}/token", json={"address": address, "password": password}, timeout=15)
    token_res.raise_for_status()
    auth = token_res.json()["token"]
    
    return address, password, auth

def check_mailtm_inbox(auth_token: str) -> Optional[str]:
    """Check mail.tm inbox once. Returns email content (text or html) or None."""
    BASE = "https://api.mail.tm"
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    inbox_res = requests.get(f"{BASE}/messages", headers=headers, timeout=15)
    inbox_res.raise_for_status()
    messages = inbox_res.json()["hydra:member"]
    
    if messages:
        message_id = messages[0]["id"]
        full_res = requests.get(f"{BASE}/messages/{message_id}", headers=headers, timeout=15)
        full_res.raise_for_status()
        data = full_res.json()
        # Fixed: Check both text and html fields, strip HTML if needed
        content = data.get("text") or data.get("html") or ""
        if content and "<" in content:  # Contains HTML tags
            content = html.unescape(re.sub(r'<[^>]+>', ' ', content))
        return content
    return None

# ============================================================================
# EMAIL PROVIDER: GUERRILLAMAIL (FIXED)
# ============================================================================

def generate_guerrillamail_email() -> Tuple[str, str, str]:
    """Generate guerrillamail email. Returns: (email, sid_token, email_timestamp_str)"""
    BASE = "https://api.guerrillamail.com/ajax.php"
    
    response = requests.get(BASE, params={"f": "get_email_address"}, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    # Fixed: Convert timestamp to string for consistent type
    return data["email_addr"], data["sid_token"], str(data["email_timestamp"])

def check_guerrillamail_inbox(sid_token: str, email_timestamp: str) -> Optional[str]:
    """Check guerrillamail inbox once. Returns email content or None."""
    BASE = "https://api.guerrillamail.com/ajax.php"
    
    response = requests.get(BASE, params={"f": "check_email", "sid_token": sid_token, "seq": email_timestamp}, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    if data.get("list") and len(data["list"]) > 0:
        email_id = data["list"][0]["mail_id"]
        full_response = requests.get(BASE, params={"f": "fetch_email", "sid_token": sid_token, "email_id": email_id}, timeout=15)
        full_response.raise_for_status()
        mail_body = full_response.json().get("mail_body", "")
        # Fixed: Strip HTML tags for better OTP extraction
        clean_body = html.unescape(re.sub(r'<[^>]+>', ' ', mail_body))
        return clean_body
    return None

# ============================================================================
# MULTI-PROVIDER EMAIL WITH FALLBACK
# ============================================================================

def generate_email_with_fallback() -> Tuple[str, str, str, str]:
    """
    Try mail.tm first, fallback to guerrillamail.
    Returns: (email_address, auth_data, provider_name, extra_data)
    """
    try:
        console.print("[cyan]Trying mail.tm...[/cyan]")
        email, password, auth = retry_sync(generate_mailtm_email, label="mail.tm generation")
        console.print(f"[green]✓[/green] mail.tm succeeded: {email}")
        return email, auth, "mail.tm", password
    except Exception as e:
        console.print(f"[yellow]mail.tm failed: {e}[/yellow]")
        console.print("[cyan]Falling back to guerrillamail...[/cyan]")
        try:
            email, sid, timestamp = retry_sync(generate_guerrillamail_email, label="guerrillamail generation")
            console.print(f"[green]✓[/green] guerrillamail succeeded: {email}")
            return email, f"{sid}|{timestamp}", "guerrillamail", ""
        except Exception as e2:
            raise Exception(f"All email providers failed. mail.tm: {e}, guerrillamail: {e2}")

async def smart_poll_inbox_async(provider: str, auth_data: str, timeout: int = 60) -> Optional[str]:
    """
    Fixed: Async polling that doesn't block event loop.
    Smart polling: check every 2 seconds, stop immediately when email arrives.
    Returns email content or None.
    """
    start_time = asyncio.get_running_loop().time()
    
    while True:
        elapsed = asyncio.get_running_loop().time() - start_time
        
        if elapsed >= timeout:
            console.print(f"[red]✗[/red] No email after {timeout}s" + " " * 20)
            return None
        
        try:
            console.print(f"[dim]Checking inbox... ({int(elapsed)}s elapsed)[/dim]", end="\r")
            
            # Run sync email check in executor to avoid blocking
            loop = asyncio.get_running_loop()
            if provider == "mail.tm":
                content = await loop.run_in_executor(None, check_mailtm_inbox, auth_data)
            elif provider == "guerrillamail":
                sid, timestamp = auth_data.split("|")
                content = await loop.run_in_executor(None, check_guerrillamail_inbox, sid, timestamp)
            else:
                return None
            
            if content:
                console.print(f"[green]✓[/green] Email received after {int(elapsed)}s" + " " * 20)
                return content
            
            await asyncio.sleep(2)
        except Exception:
            await asyncio.sleep(2)

# ============================================================================
# OTP EXTRACTION: REGEX FIRST, AI FALLBACK (FIXED)
# ============================================================================

def extract_otp_regex(email_content: str) -> Optional[str]:
    """Extract OTP using improved regex with context awareness."""
    # Try context-aware regex first (forward-only to avoid wrong numbers)
    context_match = OTP_CONTEXT_REGEX.search(email_content)
    if context_match:
        return context_match.group(1)
    
    # Fallback to 6-digit codes
    fallback_match = OTP_FALLBACK_REGEX.search(email_content)
    if fallback_match:
        return fallback_match.group(1)
    
    return None

def extract_otp_ai(email_content: str, api_key: str) -> Optional[str]:
    """Extract OTP using FreeModel AI API."""
    API_URL = "https://api.freemodel.dev/v1/chat/completions"
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-5.4-mini",
        "max_completion_tokens": 10,  # Fixed: Increased from 6 to handle 8-digit OTPs
        "messages": [
            {"role": "system", "content": "Extract the OTP verification code from the email. Return only the digits of the verification code, nothing else. No spaces, no punctuation, no labels, no explanations."},
            {"role": "user", "content": email_content[:1000]}  # Limit content to avoid token limits
        ]
    }
    
    response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    otp = response.json()["choices"][0]["message"]["content"].strip()
    
    # Extract only digits from response
    otp_digits = re.sub(r'\D', '', otp)
    return otp_digits if otp_digits and 4 <= len(otp_digits) <= 8 else None

def extract_otp(email_content: str, api_key: str) -> Optional[str]:
    """Extract OTP: try regex first, fallback to AI."""
    # Try regex first
    otp = extract_otp_regex(email_content)
    if otp:
        console.print(f"[green]✓[/green] OTP extracted via regex: {otp}")
        return otp
    
    console.print("[yellow]Regex failed, trying AI...[/yellow]")
    otp = extract_otp_ai(email_content, api_key)
    if otp:
        console.print(f"[green]✓[/green] OTP extracted via AI: {otp}")
        return otp
    
    return None

# ============================================================================
# UNIVERSAL FIELD DETECTION (FIXED)
# ============================================================================

async def find_input_by_pattern(page: Page, pattern: re.Pattern, field_type: str) -> Optional[Any]:
    """Universal input field finder using regex pattern matching."""
    # Get all input elements
    inputs = await page.locator('input').all()
    
    for inp in inputs:
        try:
            # Fixed: Check visibility first
            if not await inp.is_visible():
                continue
            
            # Fixed: Don't check 'class' attribute to avoid false matches
            attrs_to_check = ['name', 'id', 'placeholder', 'aria-label', 'autocomplete', 'type']
            for attr in attrs_to_check:
                value = await inp.get_attribute(attr)
                if value and pattern.search(value):
                    return inp
            
            # Check associated label
            input_id = await inp.get_attribute('id')
            if input_id:
                label = page.locator(f'label[for="{input_id}"]')
                if await label.count() > 0:
                    label_text = await label.inner_text()
                    if pattern.search(label_text):
                        return inp
        except Exception:
            continue
    
    raise Exception(f"{field_type} field not found")

async def find_button_by_pattern(page: Page, pattern: re.Pattern, button_type: str) -> Optional[Any]:
    """Universal button finder using regex pattern matching."""
    # Check buttons and elements with role="button"
    selectors = ['button', '[role="button"]', 'input[type="submit"]', 'input[type="button"]']
    
    for selector in selectors:
        elements = await page.locator(selector).all()
        for elem in elements:
            try:
                if not await elem.is_visible():
                    continue
                
                # Fixed: Check if button is enabled
                if not await elem.is_enabled():
                    continue
                
                # Check inner text
                text = await elem.inner_text()
                if pattern.search(text):
                    return elem
                
                # Check value attribute (for input elements)
                value = await elem.get_attribute('value')
                if value and pattern.search(value):
                    return elem
                
                # Check aria-label
                aria_label = await elem.get_attribute('aria-label')
                if aria_label and pattern.search(aria_label):
                    return elem
            except Exception:
                continue
    
    raise Exception(f"{button_type} button not found")

# ============================================================================
# MULTI-STEP FORM SUPPORT (FIXED)
# ============================================================================

async def wait_for_otp_field(page: Page, timeout: int = 15) -> Any:
    """
    Fixed: Removed retry_async wrapper to avoid 45s timeout.
    Poll for OTP field appearance (multi-step form support).
    """
    deadline = asyncio.get_running_loop().time() + timeout
    
    while asyncio.get_running_loop().time() < deadline:
        try:
            otp_field = await find_input_by_pattern(page, OTP_PATTERN, "OTP")
            if otp_field:
                return otp_field
        except Exception:
            pass
        await asyncio.sleep(1)
    
    raise Exception("OTP field did not appear within timeout")

# ============================================================================
# MAIN AUTOMATION WORKFLOW (FIXED)
# ============================================================================

async def run_automation(url: str, api_key: str) -> None:
    """Main automation workflow with fresh browser context."""
    try:
        # Step 1: Generate Identity
        console.print("\n[bold cyan]═══ Step 1: Generate Identity ═══[/bold cyan]")
        identity = generate_identity()
        console.print(Panel(
            f"[bold]Name:[/bold] {identity.full_name}\n"
            f"[bold]Gender:[/bold] {identity.gender.capitalize()}\n"
            f"[bold]Age:[/bold] {identity.age}\n"
            f"[bold]Location:[/bold] {identity.city}, {identity.state}",
            title="✨ Generated Identity",
            border_style="cyan"
        ))
        
        # Step 2: Generate Email with Fallback
        console.print("\n[bold cyan]═══ Step 2: Generate Email ═══[/bold cyan]")
        email, auth_data, provider, _ = generate_email_with_fallback()
        
        # Step 3: Launch Browser
        console.print("\n[bold cyan]═══ Step 3: Launch Browser ═══[/bold cyan]")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()  # Fresh context
            page = await context.new_page()
            
            # Step 4: Navigate to URL (Fixed: Added explicit timeout)
            console.print(f"[cyan]Navigating to {url}...[/cyan]")
            await retry_async(
                lambda: page.goto(url, wait_until="domcontentloaded", timeout=30000),
                label="page load"
            )
            console.print("[green]✓[/green] Page loaded")
            
            # Step 5: Find and Fill Email Field
            console.print("\n[bold cyan]═══ Step 4: Fill Email ═══[/bold cyan]")
            email_field = await retry_async(
                lambda: find_input_by_pattern(page, EMAIL_PATTERN, "Email"),
                label="email field find"
            )
            await email_field.fill(email)
            console.print(f"[green]✓[/green] Email entered: {email}")
            
            await asyncio.sleep(0.5)
            
            # Step 6: Click Send Code Button (or skip if not found)
            console.print("\n[bold cyan]═══ Step 5: Send Code ═══[/bold cyan]")
            try:
                send_button = await retry_async(
                    lambda: find_button_by_pattern(page, SEND_PATTERN, "Send Code"),
                    label="send button find"
                )
                await send_button.click()
                console.print("[green]✓[/green] Send Code clicked")
                
                # Fixed: Wait for potential page navigation
                await asyncio.sleep(2)
            except Exception:
                console.print("[yellow]⚠[/yellow] No dedicated Send Code button found, assuming form auto-sends OTP")
                await asyncio.sleep(1)
            
            # Step 7: Wait for Email (Smart Polling - Fixed: Now async)
            console.print("\n[bold cyan]═══ Step 6: Wait for Email ═══[/bold cyan]")
            email_content = await smart_poll_inbox_async(provider, auth_data, timeout=60)
            
            if not email_content:
                raise Exception("No email received within 60 seconds")
            
            # Step 8: Extract OTP (Regex First, AI Fallback)
            console.print("\n[bold cyan]═══ Step 7: Extract OTP ═══[/bold cyan]")
            otp = extract_otp(email_content, api_key)
            
            if not otp:
                console.print(f"[yellow]Email content preview:[/yellow] {email_content[:200]}")
                raise Exception("Failed to extract OTP from email")
            
            # Step 9: Wait for OTP Field (Multi-Step Support - Fixed: No double retry)
            console.print("\n[bold cyan]═══ Step 8: Enter OTP ═══[/bold cyan]")
            otp_field = await wait_for_otp_field(page, timeout=15)
            await otp_field.fill(otp)
            console.print(f"[green]✓[/green] OTP entered: {otp}")
            
            await asyncio.sleep(0.5)
            
            # Step 10: Submit OTP
            submit_button = await retry_async(
                lambda: find_button_by_pattern(page, SUBMIT_PATTERN, "Submit"),
                label="submit button find"
            )
            await submit_button.click()
            console.print("[green]✓[/green] OTP submitted")
            
            # Fixed: Wait for potential redirect/success page
            await asyncio.sleep(3)
            
            # Get final URL for summary
            current_url = page.url
            
            # Success Summary
            console.print("\n[bold green]═══════════════════════════════════[/bold green]")
            console.print("[bold green]    ✓ REGISTRATION COMPLETED    [/bold green]")
            console.print("[bold green]═══════════════════════════════════[/bold green]\n")
            
            console.print(Panel(
                f"[bold]URL:[/bold] {url}\n"
                f"[bold]Email:[/bold] {email}\n"
                f"[bold]Provider:[/bold] {provider}\n"
                f"[bold]Identity:[/bold] {identity.full_name}\n"
                f"[bold]OTP:[/bold] {otp}\n"
                f"[bold]Final URL:[/bold] {current_url}",
                title="📋 Registration Summary",
                border_style="green"
            ))
    
    except Exception as e:
        console.print(f"\n[red]✗ Error:[/red] {e}")
        raise

# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Main CLI entry point."""
    console.print("\n[bold cyan]╔═══════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║   Auto Registration Workflow v2.1    ║[/bold cyan]")
    console.print("[bold cyan]╚═══════════════════════════════════════╝[/bold cyan]\n")
    
    # Get URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = Prompt.ask("Enter registration URL")
    
    if not url.startswith("http"):
        console.print("[red]✗[/red] Invalid URL. Must start with http:// or https://")
        return
    
    # Get API key
    api_key = get_api_key()
    
    # Run automation
    try:
        asyncio.run(run_automation(url, api_key))
    except Exception:
        # Error already printed in run_automation
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Aborted by user[/yellow]")
        sys.exit(130)
