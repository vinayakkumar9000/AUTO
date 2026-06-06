#!/usr/bin/env python3
"""
Integration Layer v1.0
Integrates advanced form detection with existing auto_registration.py workflow
Author: vinayakkumar9000
"""

# Standard library imports
import asyncio
from typing import Any, Dict, Optional

# Third-party imports
from playwright.async_api import Page

# Local module imports
from dynamic_form_support import DynamicFormHandler
from field_handlers import (
    CheckboxHandler,
    DOBHandler,
    DropdownHandler,
    PasswordManager,
    UsernameManager,
)
from form_detection_engine import FieldCandidate, FormDetectionEngine, set_field_value


# ============================================================================
# UNIFIED FORM FILLER
# ============================================================================

class UnifiedFormFiller:
    """
    Unified form filler that combines all advanced features.
    Maintains backward compatibility with existing workflow.
    """
    
    def __init__(self, page: Page, identity: Any, verbose: bool = True):
        self.page = page
        self.identity = identity
        self.verbose = verbose
        
        # Initialize components
        self.detection_engine = FormDetectionEngine(page, verbose)
        self.dynamic_handler = DynamicFormHandler(page, verbose)
        self.password_manager = PasswordManager()
        self.username_manager = UsernameManager()
        
        # Parse date_of_birth string (format: dd-mm-yyyy)
        if hasattr(identity, 'date_of_birth') and identity.date_of_birth:
            try:
                day, month, year = map(int, identity.date_of_birth.split('-'))
                self.dob_handler = DOBHandler(year, month, day)
            except:
                # Fallback to default values if parsing fails
                self.dob_handler = DOBHandler(2000, 1, 1)
        else:
            self.dob_handler = DOBHandler(2000, 1, 1)
        self.dropdown_handler = DropdownHandler(identity)
        
        # Track filled fields
        self.filled_fields: Dict[str, bool] = {}
    
    def log(self, message: str):
        """Log messages if verbose enabled."""
        if self.verbose:
            print(f"[UNIFIED] {message}")
    
    async def discover_and_fill_all(self, email: str) -> Dict[str, bool]:
        """
        Main entry point: Discover all fields and auto-fill them.
        
        Args:
            email: Email address to fill
        
        Returns:
            Dict of {field_type: success_bool}
        """
        self.log("Starting unified form discovery and filling...")
        
        # Discover all fields
        fields = await self.detection_engine.discover_all_fields()
        
        if not fields:
            self.log("No fields discovered, trying dynamic wait...")
            # Wait for fields to appear dynamically
            await asyncio.sleep(2)
            fields = await self.detection_engine.discover_all_fields()
        
        self.log(f"Discovered {len(fields)} fields")
        
        # Fill fields by priority
        await self._fill_email(fields, email)
        await self._fill_password(fields)
        await self._fill_username(fields)
        await self._fill_name_fields(fields)
        await self._fill_phone(fields)
        await self._fill_dob(fields)
        await self._fill_gender(fields)
        await self._fill_country(fields)
        await self._auto_check_boxes()
        
        return self.filled_fields
    
    async def _fill_email(self, fields: list, email: str):
        """Fill email field with validation."""
        email_field = next((f for f in fields if f.field_type == "email"), None)
        
        if email_field:
            self.log(f"Filling email field (confidence={email_field.confidence})...")
            success = await set_field_value(
                email_field.locator, 
                email, 
                self.verbose,
                frame_context=email_field.frame_context
            )
            
            # Validate the value was set correctly
            if success:
                try:
                    actual_value = await email_field.locator.input_value()
                    if actual_value != email:
                        self.log(f"Email validation failed, retrying... (expected: {email}, got: {actual_value})")
                        await email_field.locator.clear()
                        success = await set_field_value(email_field.locator, email, self.verbose, frame_context=email_field.frame_context)
                except:
                    pass
            
            self.filled_fields["email"] = success
        else:
            self.log("No email field found")
            self.filled_fields["email"] = False
    
    async def _fill_password(self, fields: list):
        """Fill password and confirm password fields with validation and retry."""
        password_fields = [f for f in fields if f.field_type == "password"]
        confirm_fields = [f for f in fields if f.field_type == "confirm_password"]
        
        if password_fields or confirm_fields:
            password = self.password_manager.get_or_generate()
            self.log(f"Generated password: {password}")
            
            # Fill password field with retry
            if password_fields:
                success = False
                for attempt in range(3):
                    success = await set_field_value(password_fields[0].locator, password, self.verbose, frame_context=password_fields[0].frame_context)
                    if success:
                        break
                    self.log(f"Password fill attempt {attempt + 1} failed, retrying...")
                    await asyncio.sleep(0.5)
                self.filled_fields["password"] = success
            
            # Fill confirm password field with retry
            if confirm_fields:
                success = False
                for attempt in range(3):
                    success = await set_field_value(confirm_fields[0].locator, password, self.verbose, frame_context=confirm_fields[0].frame_context)
                    if success:
                        break
                    self.log(f"Confirm password fill attempt {attempt + 1} failed, retrying...")
                    await asyncio.sleep(0.5)
                self.filled_fields["confirm_password"] = success
        else:
            self.log("No password fields found")
    
    async def _fill_username(self, fields: list):
        """Fill username/display name fields."""
        username_fields = [f for f in fields if f.field_type in ["username", "display_name"]]
        
        if username_fields:
            username = self.username_manager.get_or_generate(
                self.identity.first_name,
                self.identity.last_name
            )
            self.log(f"Generated username: {username}")
            
            success = await set_field_value(username_fields[0].locator, username, self.verbose, frame_context=username_fields[0].frame_context)
            self.filled_fields["username"] = success
        else:
            self.log("No username fields found")
    
    async def _fill_name_fields(self, fields: list):
        """Fill name fields (first, last, full)."""
        first_name_fields = [f for f in fields if f.field_type == "first_name"]
        last_name_fields = [f for f in fields if f.field_type == "last_name"]
        full_name_fields = [f for f in fields if f.field_type == "full_name"]
        
        if full_name_fields:
            success = await set_field_value(
                full_name_fields[0].locator,
                self.identity.full_name,
                self.verbose
            )
            self.filled_fields["full_name"] = success
        elif first_name_fields or last_name_fields:
            if first_name_fields:
                success = await set_field_value(
                    first_name_fields[0].locator,
                    self.identity.first_name,
                    self.verbose
                )
                self.filled_fields["first_name"] = success
            
            if last_name_fields:
                success = await set_field_value(
                    last_name_fields[0].locator,
                    self.identity.last_name,
                    self.verbose
                )
                self.filled_fields["last_name"] = success
        else:
            self.log("No name fields found")
    
    async def _fill_phone(self, fields: list):
        """Fill phone field."""
        phone_fields = [f for f in fields if f.field_type == "phone"]
        
        if phone_fields:
            success = await set_field_value(
                phone_fields[0].locator,
                self.identity.phone,
                self.verbose
            )
            self.filled_fields["phone"] = success
        else:
            self.log("No phone fields found")
    
    async def _fill_dob(self, fields: list):
        """Fill date of birth field."""
        dob_fields = [f for f in fields if f.field_type == "date_of_birth"]
        
        if dob_fields:
            success = await self.dob_handler.fill_date_input(
                dob_fields[0].locator,
                self.verbose
            )
            self.filled_fields["date_of_birth"] = success
        else:
            self.log("No DOB fields found")
    
    async def _fill_gender(self, fields: list):
        """Fill gender dropdown."""
        gender_fields = [f for f in fields if f.field_type == "gender"]
        
        if gender_fields:
            success = await self.dropdown_handler.fill_gender(
                gender_fields[0].locator,
                self.verbose
            )
            self.filled_fields["gender"] = success
        else:
            self.log("No gender fields found")
    
    async def _fill_country(self, fields: list):
        """Fill country dropdown."""
        country_fields = [f for f in fields if f.field_type == "country"]
        
        if country_fields:
            success = await self.dropdown_handler.fill_country(
                country_fields[0].locator,
                self.verbose
            )
            self.filled_fields["country"] = success
        else:
            self.log("No country fields found")
    
    async def _auto_check_boxes(self):
        """Auto-check safe checkboxes."""
        try:
            checkboxes = await self.page.locator('input[type="checkbox"]').all()
            
            if checkboxes:
                self.log(f"Found {len(checkboxes)} checkboxes, analyzing...")
                checked_count = await CheckboxHandler.auto_check_safe_boxes(
                    checkboxes,
                    self.verbose
                )
                self.filled_fields["checkboxes"] = checked_count > 0
                self.log(f"Auto-checked {checked_count} safe checkboxes")
            else:
                self.log("No checkboxes found")
        except Exception as e:
            self.log(f"Error checking boxes: {e}")
    
    async def wait_for_otp_field(self, timeout: int = 15) -> Optional[Any]:
        """
        Wait for OTP field to appear (for multi-step forms).
        Uses dynamic form handler with MutationObserver and aggressive rescanning.
        
        Args:
            timeout: Maximum seconds to wait
        
        Returns:
            OTP field locator or None
        """
        self.log(f"Waiting for OTP field (timeout={timeout}s)...")
        
        async def check_otp():
            # Force a fresh scan each time
            self.detection_engine.discovered_fields = []
            fields = await self.detection_engine.discover_all_fields()
            otp_fields = [f for f in fields if f.field_type == "otp"]
            
            if otp_fields:
                self.log(f"Found OTP field with confidence={otp_fields[0].confidence}")
                return otp_fields[0].locator
            
            # Also try direct selector as fallback
            try:
                otp_input = self.page.locator('input[name*="otp" i], input[id*="otp" i], input[placeholder*="code" i], input[placeholder*="verif" i]').first
                if await otp_input.count() > 0 and await otp_input.is_visible():
                    self.log("Found OTP field via direct selector fallback")
                    return otp_input
            except:
                pass
            
            return None
        
        otp_field = await self.dynamic_handler.smart_wait_for_field(
            check_otp,
            timeout=timeout,
            field_name="OTP field",
            use_observer=True
        )
        
        return otp_field
    
    def get_generated_password(self) -> Optional[str]:
        """Get the generated password for display."""
        return self.password_manager.generated_password
    
    def get_generated_username(self) -> Optional[str]:
        """Get the generated username for display."""
        return self.username_manager.generated_username


# ============================================================================
# BACKWARD COMPATIBLE WRAPPER
# ============================================================================

async def enhanced_find_and_fill_email(
    page: Page,
    email: str,
    identity: Any,
    verbose: bool = True
) -> bool:
    """
    Enhanced email field finder with fallback to legacy method.
    
    Args:
        page: Playwright page
        email: Email to fill
        identity: Identity object
        verbose: Enable logging
    
    Returns:
        True if successful, False otherwise
    """
    filler = UnifiedFormFiller(page, identity, verbose)
    
    # Try advanced detection first
    results = await filler.discover_and_fill_all(email)
    
    if results.get("email", False):
        return True
    
    # Fallback to legacy regex-based detection
    if verbose:
        print("[UNIFIED] Advanced detection failed, trying legacy method...")
    
    return False


async def enhanced_wait_for_otp_field(
    page: Page,
    identity: Any,
    timeout: int = 15,
    verbose: bool = True
) -> Optional[Any]:
    """
    Enhanced OTP field waiter with dynamic form support.
    
    Args:
        page: Playwright page
        identity: Identity object
        timeout: Maximum seconds to wait
        verbose: Enable logging
    
    Returns:
        OTP field locator or None
    """
    filler = UnifiedFormFiller(page, identity, verbose)
    return await filler.wait_for_otp_field(timeout)
