#!/usr/bin/env python3
"""
Auto Registration Workflow v2.0
Universal, robust, and lightweight automation for registration forms
Author: vinayakkumar9000
"""

import asyncio
import json
import re
import sys
import time
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
# UNIVERSAL REGEX PATTERNS
# ============================================================================

EMAIL_PATTERN = re.compile(r'(email|e[\-_]?mail|mail|user[\-_]?name)', re.IGNORECASE)
OTP_PATTERN = re.compile(r'(otp|code|verif|token|pin|confirm|auth|2fa|mfa|one[\-_]?time)', re.IGNORECASE)
SEND_PATTERN = re.compile(r'(send|get|request|resend|generate)[\s\-_]*(code|otp|pin|verify|email)', re.IGNORECASE)
SUBMIT_PATTERN = re.compile(r'(submit|verify|confirm|continue|next|proceed|validate|done|finish)', re.IGNORECASE)
OTP_REGEX = re.compile(r'\b(\d{4,8})\b')

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
# RETRY HELPERS
# ============================================================================

async def retry_async(fn: Callable, retries: int = 3, delay: float = 1.5, label: str = "step") -> Any:
    """Retry async function with exponential backoff."""
    for attempt in range(retries):
        try:
            return await fn()
        except Exception as e:
            if attempt == retries - 1:
                raise
            console.print(f"[yellow]Retry {label} ({attempt + 1}/{retries}): {e}[/yellow]")
            await asyncio.sleep(delay)

def retry_sync(fn: Callable, retries: int = 3, delay: float = 1.5, label: str = "step") -> Any:
    """Retry sync function with exponential backoff."""
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if attempt == retries - 1:
                raise
            console.print(f"[yellow]Retry {label} ({attempt + 1}/{retries}): {e}[/yellow]")
            time.sleep(delay)

# ============================================================================
# EMAIL PROVIDER: MAIL.TM
# ============================================================================

def _rand_string(length: int) -> str:
    """Generate random string."""
    import random
    import string
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

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
    """Check mail.tm inbox once. Returns email content or None."""
    BASE = "https://api.mail.tm"
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    inbox_res = requests.get(f"{BASE}/messages", headers=headers, timeout=15)
    inbox_res.raise_for_status()
    messages = inbox_res.json()["hydra:member"]
    
    if messages:
        message_id = messages[0]["id"]
        full_res = requests.get(f"{BASE}/messages/{message_id}", headers=headers, timeout=15)
        full_res.raise_for_status()
        return full_res.json().get("text", "")
    return None

# ============================================================================
# EMAIL PROVIDER: GUERRILLAMAIL
# ============================================================================

def generate_guerrillamail_email() -> Tuple[str, str, str]:
    """Generate guerrillamail email. Returns: (email, sid_token, email_timestamp)"""
    BASE = "https://api.guerrillamail.com/ajax.php"
    
    response = requests.get(BASE, params={"f": "get_email_address"}, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    return data["email_addr"], data["sid_token"], data["email_timestamp"]

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
        return full_response.json().get("mail_body", "")
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

def smart_poll_inbox(provider: str, auth_data: str, timeout: int = 60) -> Optional[str]:
    """
    Smart polling: check every 2 seconds, stop immediately when email arrives.
    Returns email content or None.
    """
    start_time = time.time()
    elapsed = 0
    
    while elapsed < timeout:
        try:
            console.print(f"[dim]Checking inbox... ({int(elapsed)}s elapsed)[/dim]", end="\r")
            
            if provider == "mail.tm":
                content = check_mailtm_inbox(auth_data)
            elif provider == "guerrillamail":
                sid, timestamp = auth_data.split("|")
                content = check_guerrillamail_inbox(sid, timestamp)
            else:
                return None
            
            if content:
                console.print(f"[green]✓[/green] Email received after {int(elapsed)}s" + " " * 20)
                return content
            
            time.sleep(2)
            elapsed = time.time() - start_time
        except Exception:
            time.sleep(2)
            elapsed = time.time() - start_time
    
    console.print(f"[red]✗[/red] No email after {timeout}s" + " " * 20)
    return None

# ============================================================================
# OTP EXTRACTION: REGEX FIRST, AI FALLBACK
# ============================================================================

def extract_otp_regex(email_content: str) -> Optional[str]:
    """Extract OTP using regex. Prefer 6-digit, then any 4-8 digit."""
    matches = OTP_REGEX.findall(email_content)
    if not matches:
        return None
    
    # Prefer 6-digit codes
    six_digit = [m for m in matches if len(m) == 6]
    if six_digit:
        return six_digit[0]
    
    # Return first 4-8 digit match
    return matches[0]

def extract_otp_ai(email_content: str, api_key: str) -> Optional[str]:
    """Extract OTP using FreeModel AI API."""
    API_URL = "https://api.freemodel.dev/v1/chat/completions"
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-5.4-mini",
        "max_completion_tokens": 6,
        "messages": [
            {"role": "system", "content": "Extract the OTP from the user's message. Return only the verification code digits. Output must contain digits only, no spaces, no punctuation, no labels, no explanations, no markdown, no quotes, and no extra characters. If multiple numbers exist, return only the number intended for authentication."},
            {"role": "user", "content": email_content}
        ]
    }
    
    response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    otp = response.json()["choices"][0]["message"]["content"].strip()
    
    return otp if otp.isdigit() else None

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
# UNIVERSAL FIELD DETECTION
# ============================================================================

async def find_input_by_pattern(page: Page, pattern: re.Pattern, field_type: str) -> Optional[Any]:
    """Universal input field finder using regex pattern matching."""
    # Get all input elements
    inputs = await page.locator('input').all()
    
    for inp in inputs:
        try:
            # Check all attributes
            attrs_to_check = ['name', 'id', 'placeholder', 'aria-label', 'autocomplete', 'class', 'type']
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
# MULTI-STEP FORM SUPPORT
# ============================================================================

async def wait_for_otp_field(page: Page, timeout: int = 15) -> Any:
    """Poll for OTP field appearance (multi-step form support)."""
    deadline = asyncio.get_event_loop().time() + timeout
    
    while asyncio.get_event_loop().time() < deadline:
        try:
            otp_field = await find_input_by_pattern(page, OTP_PATTERN, "OTP")
            if otp_field:
                return otp_field
        except Exception:
            pass
        await asyncio.sleep(1)
    
    raise Exception("OTP field did not appear within timeout")

# ============================================================================
# MAIN AUTOMATION WORKFLOW
# ============================================================================

async def run_automation(url: str, api_key: str) -> None:
    """Main automation workflow with fresh browser context."""
    browser: Optional[Browser] = None
    
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
        email, auth_data, provider, extra = generate_email_with_fallback()
        
        # Step 3: Launch Browser
        console.print("\n[bold cyan]═══ Step 3: Launch Browser ═══[/bold cyan]")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()  # Fresh context
            page = await context.new_page()
            
            # Step 4: Navigate to URL
            console.print(f"[cyan]Navigating to {url}...[/cyan]")
            await retry_async(lambda: page.goto(url, wait_until="networkidle"), label="page load")
            console.print("[green]✓[/green] Page loaded")
            
            # Step 5: Find and Fill Email Field
            console.print("\n[bold cyan]═══ Step 4: Fill Email ═══[/bold cyan]")
            email_field = await retry_async(
                lambda: find_input_by_pattern(page, EMAIL_PATTERN, "Email"),
                label="email field find"
            )
            await email_field.fill(email)
            console.print(f"[green]✓[/green] Email entered: {email}")
            
            await asyncio.sleep(1)
            
            # Step 6: Click Send Code Button
            console.print("\n[bold cyan]═══ Step 5: Send Code ═══[/bold cyan]")
            send_button = await retry_async(
                lambda: find_button_by_pattern(page, SEND_PATTERN, "Send Code"),
                label="send button find"
            )
            await send_button.click()
            console.print("[green]✓[/green] Send Code clicked")
            
            # Step 7: Wait for Email (Smart Polling)
            console.print("\n[bold cyan]═══ Step 6: Wait for Email ═══[/bold cyan]")
            email_content = smart_poll_inbox(provider, auth_data, timeout=60)
            
            if not email_content:
                raise Exception("No email received within 60 seconds")
            
            # Step 8: Extract OTP (Regex First, AI Fallback)
            console.print("\n[bold cyan]═══ Step 7: Extract OTP ═══[/bold cyan]")
            otp = extract_otp(email_content, api_key)
            
            if not otp:
                raise Exception("Failed to extract OTP from email")
            
            # Step 9: Wait for OTP Field (Multi-Step Support)
            console.print("\n[bold cyan]═══ Step 8: Enter OTP ═══[/bold cyan]")
            otp_field = await retry_async(
                lambda: wait_for_otp_field(page, timeout=15),
                label="OTP field find"
            )
            await otp_field.fill(otp)
            console.print(f"[green]✓[/green] OTP entered: {otp}")
            
            await asyncio.sleep(1)
            
            # Step 10: Submit OTP
            submit_button = await retry_async(
                lambda: find_button_by_pattern(page, SUBMIT_PATTERN, "Submit"),
                label="submit button find"
            )
            await submit_button.click()
            console.print("[green]✓[/green] OTP submitted")
            
            await asyncio.sleep(3)
            
            # Success Summary
            console.print("\n[bold green]═══════════════════════════════════[/bold green]")
            console.print("[bold green]    ✓ REGISTRATION COMPLETED    [/bold green]")
            console.print("[bold green]═══════════════════════════════════[/bold green]\n")
            
            console.print(Panel(
                f"[bold]URL:[/bold] {url}\n"
                f"[bold]Email:[/bold] {email}\n"
                f"[bold]Provider:[/bold] {provider}\n"
                f"[bold]Identity:[/bold] {identity.full_name}\n"
                f"[bold]OTP:[/bold] {otp}",
                title="📋 Registration Summary",
                border_style="green"
            ))
    
    except Exception as e:
        console.print(f"\n[red]✗ Error:[/red] {e}")
        raise
    finally:
        if browser:
            await browser.close()

# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Main CLI entry point."""
    console.print("\n[bold cyan]╔═══════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║   Auto Registration Workflow v2.0    ║[/bold cyan]")
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
    asyncio.run(run_automation(url, api_key))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Aborted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]✗ Fatal error:[/red] {e}")
        sys.exit(1)
