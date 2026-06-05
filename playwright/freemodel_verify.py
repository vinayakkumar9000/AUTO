#!/usr/bin/env python3
"""
Lightweight Playwright script for FreeModel verification
Robust element detection with multiple fallback strategies
"""

import asyncio
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout


async def find_email_field(page: Page):
    """
    Find email input field using multiple robust strategies
    Returns the first matching locator
    """
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
    
    raise Exception("Email field not found with any strategy")


async def find_send_code_button(page: Page):
    """
    Find Send Code button using multiple robust strategies
    Returns the first matching locator
    """
    strategies = [
        'button:has-text("Send Code"):visible',
        'button:has-text("Send code"):visible',
        'button:has-text("Get Code"):visible',
        'button:has-text("Continue"):visible',
        'button:has-text("Submit"):visible',
        'button:has-text("Verify"):visible',
        'button:has-text("Next"):visible',
        '[role="button"]:has-text("Send Code"):visible',
        '[role="button"]:has-text("Send code"):visible',
        '[role="button"]:has-text("Continue"):visible',
        'button[type="submit"]:visible',
    ]
    
    for selector in strategies:
        try:
            locator = page.locator(selector).first
            if await locator.count() > 0 and await locator.is_visible():
                return locator
        except Exception:
            continue
    
    raise Exception("Send Code button not found with any strategy")


async def main():
    """Main automation flow"""
    browser = None
    
    try:
        # Launch browser
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            print("[✓] Browser launched")
            
            # Navigate to URL
            await page.goto("https://freemodel.dev/invite/FRE-6f89aaed")
            await page.wait_for_load_state("networkidle")
            
            print("[✓] Page loaded")
            
            # Find email field
            email_field = await find_email_field(page)
            print("[✓] Email field found")
            
            # Fill email
            await email_field.fill("Vinayak@vinayakkumar.me")
            print("[✓] Email entered")
            
            # Wait a moment for any dynamic content
            await asyncio.sleep(1)
            
            # Find and click Send Code button
            send_button = await find_send_code_button(page)
            await send_button.click()
            print("[✓] Send Code clicked")
            
            # Wait 10 seconds
            print("[✓] Waiting 10 seconds...")
            await asyncio.sleep(10)
            
            # Get user input
            verification_code = input("Enter verification code: ")
            print(f"[✓] Code received from user: {verification_code}")
            
            # Wait 3 seconds before exit
            await asyncio.sleep(3)
            print("[✓] Exiting")
            
    except PlaywrightTimeout as e:
        print(f"[✗] Timeout error: {e}")
    except Exception as e:
        print(f"[✗] Error: {e}")
    finally:
        if browser:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
