#!/usr/bin/env python3
"""
Advanced Universal Form Detection Engine v1.0
Multi-context form discovery with iframe and Shadow DOM support
Author: vinayakkumar9000
"""

import asyncio
import re
from typing import List, Dict, Optional, Any, Tuple
from playwright.async_api import Page, Locator, Frame, ElementHandle


# ============================================================================
# FIELD TYPE PATTERNS - Enhanced for scoring
# ============================================================================

FIELD_PATTERNS = {
    "email": [
        (r'\bemail\b', 100),
        (r'\be[\-_]?mail\b', 95),
        (r'\bmail\b', 70),
        (r'\bcontact\b', 40),
    ],
    "username": [
        (r'\busername\b', 100),
        (r'\buser[\-_]?name\b', 95),
        (r'\blogin\b', 80),
        (r'\bhandle\b', 75),
        (r'\baccount\b', 60),
    ],
    "display_name": [
        (r'\bdisplay[\-_]?name\b', 100),
        (r'\bnickname\b', 90),
        (r'\bscreen[\-_]?name\b', 85),
        (r'\bpublic[\-_]?name\b', 80),
    ],
    "password": [
        (r'\bpassword\b', 100),
        (r'\bpasswd\b', 95),
        (r'\bpwd\b', 90),
        (r'\bsecret\b', 70),
    ],
    "confirm_password": [
        (r'\bconfirm[\s\-_]*password\b', 100),
        (r'\bpassword[\s\-_]*confirm\b', 95),
        (r'\bre[\s\-_]*enter[\s\-_]*password\b', 90),
        (r'\bverify[\s\-_]*password\b', 85),
    ],
    "otp": [
        (r'\botp\b', 100),
        (r'\bcode\b', 90),
        (r'\bverif', 85),
        (r'\b2fa\b', 80),
        (r'\bmfa\b', 80),
        (r'\bone[\-_]?time\b', 75),
    ],
    "first_name": [
        (r'\bfirst[\s\-_]*name\b', 100),
        (r'\bgiven[\s\-_]*name\b', 95),
        (r'\bfname\b', 90),
        (r'\bforename\b', 85),
    ],
    "last_name": [
        (r'\blast[\s\-_]*name\b', 100),
        (r'\bsurname\b', 95),
        (r'\bfamily[\s\-_]*name\b', 90),
        (r'\blname\b', 85),
    ],
    "full_name": [
        (r'\bfull[\s\-_]*name\b', 100),
        (r'\bname\b', 80),
        (r'\bcomplete[\s\-_]*name\b', 90),
    ],
    "date_of_birth": [
        (r'\bdate[\s\-_]*of[\s\-_]*birth\b', 100),
        (r'\bdob\b', 95),
        (r'\bbirthday\b', 90),
        (r'\bbirth[\s\-_]*date\b', 95),
        (r'\bage\b', 70),
    ],
    "gender": [
        (r'\bgender\b', 100),
        (r'\bsex\b', 90),
    ],
    "country": [
        (r'\bcountry\b', 100),
        (r'\bnation\b', 80),
        (r'\blocation\b', 60),
    ],
    "phone": [
        (r'\bphone\b', 100),
        (r'\bmobile\b', 95),
        (r'\btel\b', 90),
        (r'\bcontact\b', 70),
    ],
}


# ============================================================================
# FIELD DISCOVERY RESULT
# ============================================================================

class FieldCandidate:
    """Represents a discovered form field with metadata."""
    
    def __init__(
        self,
        locator: Locator,
        field_type: str,
        confidence: int,
        context: str,
        frame_path: List[str],
        attributes: Dict[str, str],
        surrounding_text: str = ""
    ):
        self.locator = locator
        self.field_type = field_type
        self.confidence = confidence
        self.context = context  # "main", "iframe", "shadow"
        self.frame_path = frame_path
        self.attributes = attributes
        self.surrounding_text = surrounding_text
    
    def __repr__(self):
        return f"FieldCandidate(type={self.field_type}, confidence={self.confidence}, context={self.context})"


# ============================================================================
# MULTI-CONTEXT SCANNER
# ============================================================================

class FormDetectionEngine:
    """Advanced form detection with iframe and Shadow DOM support."""
    
    def __init__(self, page: Page, verbose: bool = True):
        self.page = page
        self.verbose = verbose
        self.discovered_fields: List[FieldCandidate] = []
    
    def log(self, message: str):
        """Log debug messages if verbose mode enabled."""
        if self.verbose:
            print(f"[SCAN] {message}")
    
    async def discover_all_fields(self) -> List[FieldCandidate]:
        """
        Main entry point: Discover all form fields across all contexts.
        Returns list of FieldCandidate objects sorted by confidence.
        """
        self.discovered_fields = []
        
        # Scan main document
        self.log("Scanning main document...")
        await self._scan_context(self.page, "main", [])
        
        # Scan all iframes recursively
        self.log("Scanning iframes...")
        await self._scan_iframes(self.page, [])
        
        # Scan Shadow DOM trees
        self.log("Scanning Shadow DOM...")
        await self._scan_shadow_dom(self.page, [])
        
        # Sort by confidence (highest first)
        self.discovered_fields.sort(key=lambda x: x.confidence, reverse=True)
        
        self.log(f"Total fields discovered: {len(self.discovered_fields)}")
        return self.discovered_fields
    
    async def _scan_context(self, context: Page | Frame, context_type: str, frame_path: List[str]):
        """Scan a specific context (page or frame) for form fields."""
        try:
            # Get all input, select, textarea elements
            inputs = await context.locator('input, select, textarea').all()
            
            for inp in inputs:
                try:
                    # Check visibility
                    if not await inp.is_visible():
                        continue
                    
                    # Get all attributes
                    attributes = await self._get_element_attributes(inp)
                    
                    # Get surrounding text
                    surrounding_text = await self._get_surrounding_text(inp)
                    
                    # Classify field
                    field_type, confidence = self._classify_field(attributes, surrounding_text)
                    
                    if field_type and confidence > 50:  # Minimum confidence threshold
                        candidate = FieldCandidate(
                            locator=inp,
                            field_type=field_type,
                            confidence=confidence,
                            context=context_type,
                            frame_path=frame_path,
                            attributes=attributes,
                            surrounding_text=surrounding_text
                        )
                        self.discovered_fields.append(candidate)
                        self.log(f"Found {field_type} field (confidence={confidence}, context={context_type})")
                
                except Exception as e:
                    if self.verbose:
                        print(f"[SCAN] Error processing input: {e}")
                    continue
        
        except Exception as e:
            if self.verbose:
                print(f"[SCAN] Error scanning context: {e}")
    
    async def _scan_iframes(self, context: Page | Frame, parent_path: List[str]):
        """Recursively scan all iframes."""
        try:
            frames = context.frames if hasattr(context, 'frames') else []
            
            for i, frame in enumerate(frames):
                if frame == context:  # Skip self
                    continue
                
                frame_path = parent_path + [f"iframe_{i}"]
                self.log(f"Scanning iframe: {' > '.join(frame_path)}")
                
                # Scan this iframe
                await self._scan_context(frame, "iframe", frame_path)
                
                # Recursively scan nested iframes
                await self._scan_iframes(frame, frame_path)
        
        except Exception as e:
            if self.verbose:
                print(f"[SCAN] Error scanning iframes: {e}")
    
    async def _scan_shadow_dom(self, context: Page | Frame, parent_path: List[str]):
        """Recursively scan Shadow DOM trees."""
        try:
            # Find all elements with shadow roots
            shadow_hosts = await context.locator('*').evaluate_all("""
                elements => elements.filter(el => el.shadowRoot).map((el, i) => ({
                    index: i,
                    tagName: el.tagName
                }))
            """)
            
            for host_info in shadow_hosts:
                shadow_path = parent_path + [f"shadow_{host_info['index']}_{host_info['tagName']}"]
                self.log(f"Found Shadow DOM: {' > '.join(shadow_path)}")
                
                # Get shadow root and scan it
                # Note: Playwright doesn't directly support shadow DOM traversal
                # We need to use evaluate to access shadow DOM content
                await self._scan_shadow_root(context, host_info['index'], shadow_path)
        
        except Exception as e:
            if self.verbose:
                print(f"[SCAN] Error scanning Shadow DOM: {e}")
    
    async def _scan_shadow_root(self, context: Page | Frame, host_index: int, shadow_path: List[str]):
        """Scan inside a specific shadow root."""
        try:
            # Use JavaScript to access shadow DOM inputs
            shadow_inputs = await context.evaluate(f"""
                () => {{
                    const hosts = Array.from(document.querySelectorAll('*')).filter(el => el.shadowRoot);
                    const host = hosts[{host_index}];
                    if (!host || !host.shadowRoot) return [];
                    
                    const inputs = host.shadowRoot.querySelectorAll('input, select, textarea');
                    return Array.from(inputs).map(inp => {{
                        const rect = inp.getBoundingClientRect();
                        return {{
                            visible: rect.width > 0 && rect.height > 0,
                            name: inp.name || '',
                            id: inp.id || '',
                            type: inp.type || '',
                            placeholder: inp.placeholder || '',
                            ariaLabel: inp.getAttribute('aria-label') || '',
                            autocomplete: inp.autocomplete || ''
                        }};
                    }});
                }}
            """)
            
            for inp_data in shadow_inputs:
                if not inp_data['visible']:
                    continue
                
                # Classify based on attributes
                field_type, confidence = self._classify_field(inp_data, "")
                
                if field_type and confidence > 50:
                    # Note: We can't return actual locators from shadow DOM easily
                    # This is a limitation - we log it but can't interact directly
                    self.log(f"Found {field_type} in Shadow DOM (confidence={confidence}) - Limited interaction")
        
        except Exception as e:
            if self.verbose:
                print(f"[SCAN] Error scanning shadow root: {e}")
    
    async def _get_element_attributes(self, element: Locator) -> Dict[str, str]:
        """Extract all relevant attributes from an element."""
        attributes = {}
        
        attr_names = ['name', 'id', 'type', 'placeholder', 'aria-label', 'autocomplete', 'class', 'role']
        
        for attr in attr_names:
            try:
                value = await element.get_attribute(attr)
                if value:
                    attributes[attr] = value
            except:
                pass
        
        # Get data-* attributes
        try:
            data_attrs = await element.evaluate("""
                el => {
                    const data = {};
                    for (let attr of el.attributes) {
                        if (attr.name.startsWith('data-')) {
                            data[attr.name] = attr.value;
                        }
                    }
                    return data;
                }
            """)
            attributes.update(data_attrs)
        except:
            pass
        
        return attributes
    
    async def _get_surrounding_text(self, element: Locator) -> str:
        """Get text from surrounding elements (labels, parent, siblings)."""
        try:
            surrounding = await element.evaluate("""
                el => {
                    let text = '';
                    
                    // Check for associated label
                    if (el.id) {
                        const label = document.querySelector(`label[for="${el.id}"]`);
                        if (label) text += label.textContent + ' ';
                    }
                    
                    // Check parent text
                    if (el.parentElement) {
                        text += el.parentElement.textContent + ' ';
                    }
                    
                    // Check previous sibling
                    if (el.previousElementSibling) {
                        text += el.previousElementSibling.textContent + ' ';
                    }
                    
                    return text.trim();
                }
            """)
            return surrounding[:500]  # Limit length
        except:
            return ""
    
    def _classify_field(self, attributes: Dict[str, str], surrounding_text: str) -> Tuple[Optional[str], int]:
        """
        Classify field type and return confidence score.
        Returns: (field_type, confidence_score)
        """
        scores = {}
        
        # Combine all text to search
        search_text = ' '.join([
            attributes.get('name', ''),
            attributes.get('id', ''),
            attributes.get('placeholder', ''),
            attributes.get('aria-label', ''),
            attributes.get('autocomplete', ''),
            surrounding_text
        ]).lower()
        
        # Score each field type
        for field_type, patterns in FIELD_PATTERNS.items():
            max_score = 0
            for pattern, score in patterns:
                if re.search(pattern, search_text, re.IGNORECASE):
                    max_score = max(max_score, score)
            
            if max_score > 0:
                scores[field_type] = max_score
        
        # Special handling for password confirmation
        if 'password' in scores and 'confirm_password' in scores:
            # If both match, prefer confirm_password if it has higher score
            if scores['confirm_password'] > scores['password']:
                return 'confirm_password', scores['confirm_password']
        
        # Return highest scoring field type
        if scores:
            best_type = max(scores, key=scores.get)
            return best_type, scores[best_type]
        
        return None, 0
    
    def get_best_field(self, field_type: str) -> Optional[FieldCandidate]:
        """Get the highest confidence field of a specific type."""
        candidates = [f for f in self.discovered_fields if f.field_type == field_type]
        return candidates[0] if candidates else None
    
    def get_all_fields_by_type(self, field_type: str) -> List[FieldCandidate]:
        """Get all fields of a specific type, sorted by confidence."""
        return [f for f in self.discovered_fields if f.field_type == field_type]


# ============================================================================
# FRAMEWORK-AWARE VALUE SETTER
# ============================================================================

async def set_field_value(locator: Locator, value: str, verbose: bool = True) -> bool:
    """
    Set field value with framework-aware fallback chain.
    Tries multiple methods to ensure React/Vue/Angular state updates.
    Returns True if successful, False otherwise.
    """
    
    def log(msg: str):
        if verbose:
            print(f"[FILL] {msg}")
    
    # Method 1: Playwright fill (works for most cases)
    try:
        log(f"Trying fill() method...")
        await locator.fill(value)
        await asyncio.sleep(0.1)
        
        # Verify it worked
        current_value = await locator.input_value()
        if current_value == value:
            log(f"✓ fill() succeeded")
            return True
    except Exception as e:
        log(f"fill() failed: {e}")
    
    # Method 2: Type character by character
    try:
        log(f"Trying type() method...")
        await locator.clear()
        await locator.type(value, delay=50)
        await asyncio.sleep(0.1)
        
        current_value = await locator.input_value()
        if current_value == value:
            log(f"✓ type() succeeded")
            return True
    except Exception as e:
        log(f"type() failed: {e}")
    
    # Method 3: JavaScript value injection + events
    try:
        log(f"Trying JavaScript injection...")
        await locator.evaluate(f"""
            el => {{
                el.value = '{value}';
                
                // Trigger events for React/Vue/Angular
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                el.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                
                // React-specific
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                nativeInputValueSetter.call(el, '{value}');
                
                const event = new Event('input', {{ bubbles: true }});
                el.dispatchEvent(event);
            }}
        """)
        await asyncio.sleep(0.2)
        
        current_value = await locator.input_value()
        if current_value == value:
            log(f"✓ JavaScript injection succeeded")
            return True
    except Exception as e:
        log(f"JavaScript injection failed: {e}")
    
    # Method 4: Focus + type + blur
    try:
        log(f"Trying focus + type + blur...")
        await locator.focus()
        await asyncio.sleep(0.1)
        await locator.clear()
        await locator.type(value, delay=100)
        await asyncio.sleep(0.1)
        await locator.blur()
        await asyncio.sleep(0.2)
        
        current_value = await locator.input_value()
        if current_value == value:
            log(f"✓ focus + type + blur succeeded")
            return True
    except Exception as e:
        log(f"focus + type + blur failed: {e}")
    
    log(f"✗ All methods failed to set value")
    return False
