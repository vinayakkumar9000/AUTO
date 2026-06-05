#!/usr/bin/env python3
"""
Auto Registration Workflow
Combines tempmail, identity generation, playwright automation, and AI-powered OTP extraction
Supports multiple email providers: mail.tm, guerrillamail, and custom domain
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import requests
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "tempmail"))
sys.path.insert(0, str(Path(__file__).parent.parent / "identity"))

from identity_generator import generate_identity

console = Console()

# Configuration file path
CONFIG_FILE = Path(__file__).parent / "config.json"


# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================

def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load config: {e}[/yellow]")
    return {}


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        console.print("[green]OK[/green] Configuration saved")
    except Exception as e:
        console.print(f"[red]ERROR[/red] Failed to save config: {e}")


def get_api_key() -> str:
    """Get API key from config or prompt user."""
    config = load_config()
    
    if "freemodel_api_key" in config and config["freemodel_api_key"]:
        return config["freemodel_api_key"]
    
    console.print("\n[cyan]FreeModel API Key Required[/cyan]")
    console.print("Get your API key from: https://freemodel.dev")
    
    api_key = Prompt.ask("Enter your FreeModel API key", password=True)
    
    if Confirm.ask("Save API key for future use?", default=True):
        config["freemodel_api_key"] = api_key
        save_config(config)
    
    return api_key


def select_email_provider() -> str:
    """Prompt user to select email provider."""
    console.print("\n[bold cyan]Select Email Provider[/bold cyan]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Option", style="cyan", width=10)
    table.add_column("Provider", style="green")
    table.add_column("Description", style="dim")
    
    table.add_row("1", "mail.tm", "Fast and reliable (default)")
    table.add_row("2", "guerrillamail", "Alternative provider")
    table.add_row("3", "customdomain", "Custom domain support")
    
    console.print(table)
    
    choice = Prompt.ask("Choose provider", choices=["1", "2", "3"], default="1")
    
    providers = {
        "1": "mail.tm",
        "2": "guerrillamail",
        "3": "customdomain"
    }
    
    return providers[choice]


# ============================================================================
# EMAIL PROVIDER: MAIL.TM
# ============================================================================

def _rand_string(length: int) -> str:
    """Generate random string."""
    import random
    import string
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def generate_mailtm_email() -> Tuple[str, str, str]:
    """
    Generate a temporary email using mail.tm provider.
    Returns: (email_address, password, auth_token)
    """
    BASE = "https://api.mail.tm"
    
    try:
        # Get available domains
        domains_res = requests.get(f"{BASE}/domains?page=1", timeout=15)
        domains_res.raise_for_status()
        domain = domains_res.json()["hydra:member"][0]["domain"]
        
        # Generate random credentials
        local_part = _rand_string(10)
        address = f"{local_part}@{domain}"
        password = _rand_string(12)
        
        # Create account
        account_res = requests.post(
            f"{BASE}/accounts",
            json={"address": address, "password": password},
            timeout=15
        )
        account_res.raise_for_status()
        
        # Get authentication token
        token_res = requests.post(
            f"{BASE}/token",
            json={"address": address, "password": password},
            timeout=15
        )
        token_res.raise_for_status()
        auth = token_res.json()["token"]
        
        return address, password, auth
    
    except Exception as e:
        raise Exception(f"Failed to generate mail.tm email: {e}")


def wait_for_mailtm_email(auth_token: str, timeout: int = 60) -> Optional[str]:
    """Wait for email from mail.tm and return content."""
    BASE = "https://api.mail.tm"
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            inbox_res = requests.get(f"{BASE}/messages", headers=headers, timeout=15)
            inbox_res.raise_for_status()
            messages = inbox_res.json()["hydra:member"]
            
            if messages:
                message_id = messages[0]["id"]
                full_res = requests.get(f"{BASE}/messages/{message_id}", headers=headers, timeout=15)
                full_res.raise_for_status()
                full_message = full_res.json()
                
                return full_message.get("text", "")
            
            time.sleep(2)
        
        except Exception as e:
            console.print(f"[yellow]Warning: Error checking email: {e}[/yellow]")
            time.sleep(2)
    
    return None


# ============================================================================
# EMAIL PROVIDER: GUERRILLAMAIL
# ============================================================================

def generate_guerrillamail_email() -> Tuple[str, str, str]:
    """
    Generate a temporary email using guerrillamail provider.
    Returns: (email_address, sid_token, email_timestamp)
    """
    BASE = "https://api.guerrillamail.com/ajax.php"
    
    try:
        # Get email address
        response = requests.get(
            BASE,
            params={"f": "get_email_address"},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        
        email_address = data["email_addr"]
        sid_token = data["sid_token"]
        email_timestamp = data["email_timestamp"]
        
        return email_address, sid_token, email_timestamp
    
    except Exception as e:
        raise Exception(f"Failed to generate guerrillamail email: {e}")


def wait_for_guerrillamail_email(sid_token: str, email_timestamp: str, timeout: int = 60) -> Optional[str]:
    """Wait for email from guerrillamail and return content."""
    BASE = "https://api.guerrillamail.com/ajax.php"
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                BASE,
                params={
                    "f": "check_email",
                    "sid_token": sid_token,
                    "seq": email_timestamp
                },
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("list") and len(data["list"]) > 0:
                # Get the first email
                email_id = data["list"][0]["mail_id"]
                
                # Fetch full email
                full_response = requests.get(
                    BASE,
                    params={
                        "f": "fetch_email",
                        "sid_token": sid_token,
                        "email_id": email_id
                    },
                    timeout=15
                )
                full_response.raise_for_status()
                full_data = full_response.json()
                
                return full_data.get("mail_body", "")
            
            time.sleep(2)
        
        except Exception as e:
            console.print(f"[yellow]Warning: Error checking email: {e}[/yellow]")
            time.sleep(2)
    
    return None


# ============================================================================
# EMAIL PROVIDER: CUSTOM DOMAIN
# ============================================================================

def generate_customdomain_email() -> Tuple[str, str, str]:
    """
    Generate email using custom domain (uses mail.tm backend).
    Returns: (email_address, password, auth_token)
    """
    # For now, uses mail.tm as backend
    # In future, this can be extended to support actual custom domains
    return generate_mailtm_email()


def wait_for_customdomain_email(auth_token: str, timeout: int = 60) -> Optional[str]:
    """Wait for email from custom domain (uses mail.tm backend)."""
    return wait_for_mailtm_email(auth_token, timeout)


# ============================================================================
# UNIFIED EMAIL INTERFACE
# ============================================================================

def generate_temp_email(provider: str) -> Tuple[str, str, str]:
    """Generate temporary email based on provider."""
    if provider == "mail.tm":
        return generate_mailtm_email()
    elif provider == "guerrillamail":
        return generate_guerrillamail_email()
    elif provider == "customdomain":
        return generate_customdomain_email()
    else:
        raise ValueError(f"Unknown provider: {provider}")


def wait_for_email(provider: str, auth_data: str, timeout: int = 60) -> Optional[str]:
    """Wait for email based on provider."""
    if provider == "mail.tm":
        return wait_for_mailtm_email(auth_data, timeout)
    elif provider == "guerrillamail":
        # For guerrillamail, auth_data is a tuple (sid_token, email_timestamp)
        sid_token, email_timestamp = auth_data.split("|")
        return wait_for_guerrillamail_email(sid_token, email_timestamp, timeout)
    elif provider == "customdomain":
        return wait_for_customdomain_email(auth_data, timeout)
    else:
        raise ValueError(f"Unknown provider: {provider}")


# ============================================================================
# AI OTP EXTRACTION
# ============================================================================

def extract_otp_with_ai(email_content: str, api_key: str) -> Optional[str]:
    """Extract OTP from email content using FreeModel AI API."""
    API_URL = "https://api.freemodel.dev/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-5.4-mini",
        "max_completion_tokens": 6,
        "messages": [
            {
                "role": "system",
                "content": "Extract the OTP from the user's message. Return only the verification code digits. Output must contain digits only, no spaces, no punctuation, no labels, no explanations, no markdown, no quotes, and no extra characters. If multiple numbers exist, return only the number intended for authentication."
            },
            {
                "role": "user",
                "content": email_content
            }
        ]
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        otp = result["choices"][0]["message"]["content"].strip()
        
        if otp.isdigit():
            return otp
        else:
            console.print(f"[yellow]Warning: AI returned non-numeric OTP: {otp}[/yellow]")
            return None
    
    except Exception as e:
        console.print(f"[red]ERROR[/red] AI extraction failed: {e}")
        return None


# ============================================================================
# PLAYWRIGHT AUTOMATION
# ============================================================================

async def find_email_field(page: Page) -> Any:
    """Find email input field using multiple strategies."""
    strategies = [
        'input[type="email"]',
        'input[name*="email" i]',
        'input[id*="email" i]',
        'input[placeholder*="email" i]',
        'input[aria-label*="email" i]',
        'input[autocomplete="email"]',
    ]
    
    for selector in strategies:
        try:
            locator = page.locator(selector).first
            if await locator.count() > 0:
                return locator
        except Exception:
            continue
    
    raise Exception("Email field not found")


async def find_send_code_button(page: Page) -> Any:
    """Find Send Code button using multiple strategies."""
    strategies = [
        'button:has-text("Send Code"):visible',
        'button:has-text("Send code"):visible',
        'button:has-text("Get Code"):visible',
        'button:has-text("Continue"):visible',
        'button:has-text("Submit"):visible',
        'button:has-text("Verify"):visible',
        'button:has-text("Next"):visible',
        '[role="button"]:has-text("Send"):visible',
        'button[type="submit"]:visible',
    ]
    
    for selector in strategies:
        try:
            locator = page.locator(selector).first
            if await locator.count() > 0 and await locator.is_visible():
                return locator
        except Exception:
            continue
    
    raise Exception("Send Code button not found")


async def find_otp_field(page: Page) -> Any:
    """Find OTP input field using multiple strategies."""
    strategies = [
        'input[type="text"][name*="code" i]',
        'input[type="text"][name*="otp" i]',
        'input[type="text"][name*="verification" i]',
        'input[id*="code" i]',
        'input[id*="otp" i]',
        'input[id*="verification" i]',
        'input[placeholder*="code" i]',
        'input[placeholder*="otp" i]',
        'input[placeholder*="verification" i]',
        'input[inputmode="numeric"]',
    ]
    
    for selector in strategies:
        try:
            locator = page.locator(selector).first
            if await locator.count() > 0:
                return locator
        except Exception:
            continue
    
    raise Exception("OTP field not found")


async def find_submit_button(page: Page) -> Any:
    """Find Submit/Verify button using multiple strategies."""
    strategies = [
        'button:has-text("Submit"):visible',
        'button:has-text("Verify"):visible',
        'button:has-text("Continue"):visible',
        'button:has-text("Confirm"):visible',
        'button:has-text("Next"):visible',
        'button[type="submit"]:visible',
    ]
    
    for selector in strategies:
        try:
            locator = page.locator(selector).first
            if await locator.count() > 0 and await locator.is_visible():
                return locator
        except Exception:
            continue
    
    raise Exception("Submit button not found")


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

async def run_automation(url: str, api_key: str, provider: str, auto_mode: bool = False) -> None:
    """Main automation workflow."""
    browser = None
    
    try:
        # Stage 1: Generate Identity
        console.print("\n[bold cyan]Stage 1: Generating Identity[/bold cyan]")
        identity = generate_identity()
        
        console.print(Panel(
            f"[bold]Name:[/bold] {identity.full_name}\n"
            f"[bold]Gender:[/bold] {identity.gender.capitalize()}\n"
            f"[bold]Age:[/bold] {identity.age}\n"
            f"[bold]Location:[/bold] {identity.city}, {identity.state}",
            title="Generated Identity",
            border_style="cyan"
        ))
        
        if not auto_mode:
            if not Confirm.ask("Proceed with this identity?", default=True):
                console.print("[yellow]Aborted by user[/yellow]")
                return
        else:
            console.print("[green]OK[/green] Auto-proceeding with identity")
        
        # Stage 2: Generate Temp Email
        console.print(f"\n[bold cyan]Stage 2: Generating Temporary Email ({provider})[/bold cyan]")
        email_address, auth_data1, auth_data2 = generate_temp_email(provider)
        
        # Prepare auth data based on provider
        if provider == "guerrillamail":
            auth_data = f"{auth_data1}|{auth_data2}"
        else:
            auth_data = auth_data2
        
        console.print(f"[green]OK[/green] Email generated: [bold]{email_address}[/bold]")
        
        if not auto_mode:
            if not Confirm.ask("Proceed with automation?", default=True):
                console.print("[yellow]Aborted by user[/yellow]")
                return
        else:
            console.print("[green]OK[/green] Auto-proceeding with automation")
        
        # Stage 3: Browser Automation
        console.print("\n[bold cyan]Stage 3: Opening Website[/bold cyan]")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            console.print(f"[green]OK[/green] Navigating to: {url}")
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            
            console.print("[green]OK[/green] Page loaded")
            
            # Find and fill email field
            console.print("\n[bold cyan]Stage 4: Entering Email[/bold cyan]")
            email_field = await find_email_field(page)
            await email_field.fill(email_address)
            console.print(f"[green]OK[/green] Email entered: {email_address}")
            
            await asyncio.sleep(1)
            
            # Click Send Code button
            send_button = await find_send_code_button(page)
            await send_button.click()
            console.print("[green]OK[/green] Send Code button clicked")
            
            # Stage 5: Wait for Email
            console.print("\n[bold cyan]Stage 5: Waiting for OTP Email (max 60s)[/bold cyan]")
            
            email_content = None
            for i in range(30):  # 30 attempts, 2 seconds each = 60 seconds
                console.print(f"[dim]Checking inbox... ({i+1}/30)[/dim]")
                email_content = wait_for_email(provider, auth_data, timeout=2)
                if email_content:
                    break
            
            if not email_content:
                console.print("[red]ERROR[/red] No email received within 60 seconds")
                console.print("[yellow]Aborting workflow[/yellow]")
                return
            
            console.print("[green]OK[/green] Email received")
            
            # Stage 6: Extract OTP with AI
            console.print("\n[bold cyan]Stage 6: Extracting OTP with AI[/bold cyan]")
            
            otp = extract_otp_with_ai(email_content, api_key)
            
            if not otp:
                console.print("[red]ERROR[/red] AI failed to extract OTP")
                console.print("[yellow]Email content:[/yellow]")
                console.print(email_content[:500])
                
                if not auto_mode:
                    console.print("\n[yellow]Please enter OTP manually:[/yellow]")
                    otp = Prompt.ask("Enter OTP")
                else:
                    console.print("[red]ERROR[/red] Cannot proceed in auto mode without OTP")
                    return
            else:
                console.print(f"[green]OK[/green] OTP extracted: [bold]{otp}[/bold]")
            
            # Stage 7: Enter OTP
            console.print("\n[bold cyan]Stage 7: Entering OTP[/bold cyan]")
            
            await asyncio.sleep(2)  # Wait for OTP field to appear
            
            otp_field = await find_otp_field(page)
            await otp_field.fill(otp)
            console.print(f"[green]OK[/green] OTP entered: {otp}")
            
            await asyncio.sleep(1)
            
            # Submit OTP
            submit_button = await find_submit_button(page)
            await submit_button.click()
            console.print("[green]OK[/green] OTP submitted")
            
            # Wait for result
            await asyncio.sleep(3)
            
            console.print("\n[bold green]SUCCESS: Workflow Completed Successfully![/bold green]")
            
            # Show summary
            console.print(Panel(
                f"[bold]URL:[/bold] {url}\n"
                f"[bold]Email:[/bold] {email_address}\n"
                f"[bold]Provider:[/bold] {provider}\n"
                f"[bold]Identity:[/bold] {identity.full_name}\n"
                f"[bold]OTP:[/bold] {otp}\n"
                f"[bold]Status:[/bold] Submitted",
                title="Registration Summary",
                border_style="green"
            ))
    
    except PlaywrightTimeout as e:
        console.print(f"[red]ERROR[/red] Timeout error: {e}")
    except Exception as e:
        console.print(f"[red]ERROR[/red] Error: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
    finally:
        if browser:
            await browser.close()


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Main CLI entry point."""
    console.print("\n[bold cyan]Auto Registration Workflow[/bold cyan]")
    console.print("Automated registration with temp email and AI-powered OTP extraction\n")
    
    # Check for auto mode (test mode)
    auto_mode = len(sys.argv) > 1 and sys.argv[1] == "--auto"
    
    # Get URL from user or command line
    if len(sys.argv) > 2:
        # URL provided as command line argument
        url = sys.argv[2]
    else:
        # Prompt for URL
        url = Prompt.ask("Enter the registration URL")
    
    if not url.startswith("http"):
        console.print("[red]ERROR[/red] Invalid URL. Must start with http:// or https://")
        return
    
    if auto_mode:
        console.print("[yellow]Running in AUTO mode (no prompts)[/yellow]\n")
        provider = "mail.tm"
    else:
        # Select email provider
        provider = select_email_provider()
    
    # Get API key
    api_key = get_api_key()
    
    # Run automation
    asyncio.run(run_automation(url, api_key, provider, auto_mode))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Aborted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]ERROR[/red] Fatal error: {e}")