#!/usr/bin/env python3
"""
Unified Form Filler
Wrapper that provides backward compatibility for auto_registration_v4.py
Delegates to FormDetectionEngine for actual form filling
Author: vinayakkumar9000
"""

import asyncio
from typing import Dict, Optional, Any
from playwright.async_api import Page

from form_detection_engine import FormDetectionEngine
from dynamic_form_support import DynamicFormWatcher


class UnifiedFormFiller:
    """
    Unified form filler that wraps FormDetectionEngine.
    Provides the interface expected by auto_registration_v4.py and test_runner.py
    """
    
    def __init__(
        self,
        page: Page,
        identity: Any,
        verbose: bool = True,
        ai_helper: Optional[Any] = None
    ):
        """
        Initialize unified form filler.
        
        Args:
            page: Playwright page object
            identity: Identity object with user data
            verbose: Enable verbose logging
            ai_helper: Optional AI helper for field classification
        """
        self.page = page
        self.identity = identity
        self.verbose = verbose
        self.ai_helper = ai_helper
        
        # Initialize form detection engine
        self.engine = FormDetectionEngine(page, verbose=verbose)
        
        # Initialize dynamic form watcher
        self.watcher = DynamicFormWatcher(page, verbose=verbose)
        
        # Track filled fields
        self.filled_fields = {}
    
    def log(self, message: str):
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"[FILLER] {message}")
    
    async def discover_and_fill_all(self, email: str) -> Dict[str, bool]:
        """
        Discover and fill all form fields.
        
        Args:
            email: Email address to use
        
        Returns:
            Dictionary of field types and whether they were filled
        """
        self.log("Starting form discovery and filling...")
        
        # Discover all fields
        fields = await self.engine.discover_all_fields()
        self.log(f"Discovered {len(fields)} fields")
        
        # Prepare field data from identity
        field_data = self._prepare_field_data(email)
        
        # Fill each field
        for field in fields:
            # FieldCandidate objects have field_type attribute, not dict
            field_type = field.field_type if hasattr(field, 'field_type') else field.get("type", "unknown")
            
            if field_type in field_data:
                value = field_data[field_type]
                success = await self._fill_field(field, value)
                
                if success:
                    self.filled_fields[field_type] = True
                    self.log(f"✓ Filled {field_type}")
                else:
                    self.filled_fields[field_type] = False
                    self.log(f"✗ Failed to fill {field_type}")
        
        # Wait for dynamic content
        await asyncio.sleep(1)
        
        # Try to fill any newly appeared fields
        new_fields = await self.engine.discover_all_fields()
        if len(new_fields) > len(fields):
            self.log(f"Found {len(new_fields) - len(fields)} new dynamic fields")
            for field in new_fields[len(fields):]:
                field_type = field.field_type if hasattr(field, 'field_type') else field.get("type", "unknown")
                if field_type in field_data and field_type not in self.filled_fields:
                    value = field_data[field_type]
                    success = await self._fill_field(field, value)
                    if success:
                        self.filled_fields[field_type] = True
        
        return self.filled_fields
    
    def _prepare_field_data(self, email: str) -> Dict[str, str]:
        """
        Prepare field data from identity.
        
        Args:
            email: Email address
        
        Returns:
            Dictionary mapping field types to values
        """
        data = {
            "email": email,
            "username": email.split("@")[0],
            "password": "SecurePass123!@#",
            "confirm_password": "SecurePass123!@#",
        }
        
        # Add identity data if available
        if hasattr(self.identity, "first_name"):
            data["first_name"] = self.identity.first_name
        if hasattr(self.identity, "last_name"):
            data["last_name"] = self.identity.last_name
        if hasattr(self.identity, "full_name"):
            data["full_name"] = self.identity.full_name
        if hasattr(self.identity, "date_of_birth"):
            data["date_of_birth"] = self.identity.date_of_birth
        if hasattr(self.identity, "phone"):
            data["phone"] = self.identity.phone
        if hasattr(self.identity, "address"):
            data["address"] = self.identity.address
        if hasattr(self.identity, "city"):
            data["city"] = self.identity.city
        if hasattr(self.identity, "state"):
            data["state"] = self.identity.state
        if hasattr(self.identity, "zip_code"):
            data["zip_code"] = self.identity.zip_code
        if hasattr(self.identity, "country"):
            data["country"] = self.identity.country
        
        return data
    
    async def _fill_field(self, field, value: str) -> bool:
        """
        Fill a single field.
        
        Args:
            field: FieldCandidate object or field information dictionary
            value: Value to fill
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Handle FieldCandidate objects (have locator attribute)
            if hasattr(field, 'locator'):
                element = field.locator
            else:
                # Handle dict-based fields (legacy)
                element = field.get("element")
                if not element:
                    return False
            
            # Clear existing value
            await element.fill("")
            
            # Fill with new value
            await element.fill(value)
            
            # Trigger change event
            await element.dispatch_event("change")
            await element.dispatch_event("input")
            
            # Small delay for validation
            await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            self.log(f"Error filling field: {e}")
            return False
    
    async def find_and_click_submit(self) -> bool:
        """
        Find and click submit button.
        
        Returns:
            True if button found and clicked, False otherwise
        """
        try:
            # Common submit button selectors
            selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Sign Up")',
                'button:has-text("Register")',
                'button:has-text("Create Account")',
                'button:has-text("Submit")',
                'button:has-text("Continue")',
                'button:has-text("Next")',
            ]
            
            for selector in selectors:
                try:
                    button = await self.page.wait_for_selector(selector, timeout=1000)
                    if button:
                        await button.click()
                        self.log(f"✓ Clicked submit button: {selector}")
                        return True
                except:
                    continue
            
            self.log("✗ No submit button found")
            return False
            
        except Exception as e:
            self.log(f"Error clicking submit: {e}")
            return False
    
    async def wait_for_otp_field(self, timeout: int = 15) -> Optional[Any]:
        """
        Wait for OTP field to appear on the page.
        
        Args:
            timeout: Maximum time to wait in seconds
        
        Returns:
            Locator for OTP field if found, None otherwise
        """
        try:
            # Common OTP field selectors
            otp_selectors = [
                'input[name*="otp" i]',
                'input[id*="otp" i]',
                'input[name*="code" i]',
                'input[id*="code" i]',
                'input[name*="verification" i]',
                'input[id*="verification" i]',
                'input[name*="token" i]',
                'input[id*="token" i]',
                'input[placeholder*="code" i]',
                'input[placeholder*="otp" i]',
                'input[aria-label*="code" i]',
                'input[aria-label*="otp" i]',
            ]
            
            # Try each selector
            for selector in otp_selectors:
                try:
                    otp_field = await self.page.wait_for_selector(
                        selector, 
                        timeout=timeout * 1000,
                        state='visible'
                    )
                    if otp_field:
                        self.log(f"✓ Found OTP field: {selector}")
                        return self.page.locator(selector).first
                except:
                    continue
            
            # Fallback: scan for newly appeared input fields
            self.log("Scanning for new input fields...")
            await asyncio.sleep(2)
            
            new_fields = await self.engine.discover_all_fields()
            for field in new_fields:
                if field.field_type == 'otp':
                    self.log(f"✓ Found OTP field via scan")
                    return field.locator
            
            self.log("✗ OTP field not found")
            return None
            
        except Exception as e:
            self.log(f"Error waiting for OTP field: {e}")
            return None
    
    def get_filled_fields(self) -> Dict[str, bool]:
        """Get dictionary of filled fields."""
        return self.filled_fields.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get filling statistics."""
        total = len(self.filled_fields)
        successful = sum(1 for v in self.filled_fields.values() if v)
        
        return {
            "total_fields": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "fields": self.filled_fields
        }


# Backward compatibility - export as UnifiedFormFiller
__all__ = ["UnifiedFormFiller"]
