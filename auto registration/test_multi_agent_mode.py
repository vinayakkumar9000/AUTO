#!/usr/bin/env python3
"""Test multi-agent mode activation."""

import os
import sys

# Set environment variable
os.environ["USE_MULTI_AGENT"] = "true"

# Test if it's read correctly
USE_MULTI_AGENT = os.getenv("USE_MULTI_AGENT", "false").lower() == "true"
print(f"USE_MULTI_AGENT environment variable: {os.getenv('USE_MULTI_AGENT')}")
print(f"USE_MULTI_AGENT parsed value: {USE_MULTI_AGENT}")

# Test import
try:
    from integration_layer import create_integration_layer
    print("✓ Multi-agent system import successful")
    MULTI_AGENT_AVAILABLE = True
except ImportError as e:
    print(f"✗ Multi-agent system import failed: {e}")
    MULTI_AGENT_AVAILABLE = False

print(f"MULTI_AGENT_AVAILABLE: {MULTI_AGENT_AVAILABLE}")

if USE_MULTI_AGENT and MULTI_AGENT_AVAILABLE:
    print("\n✅ Multi-agent mode would be ENABLED")
else:
    print("\n⚠️ Multi-agent mode would be DISABLED")
    if not USE_MULTI_AGENT:
        print("   Reason: USE_MULTI_AGENT is False")
    if not MULTI_AGENT_AVAILABLE:
        print("   Reason: MULTI_AGENT_AVAILABLE is False")
