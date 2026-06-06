#!/usr/bin/env python3
"""Test imports for integration layer fixes."""

try:
    from integration_layer import UnifiedFormFiller, create_integration_layer
    print("✓ UnifiedFormFiller import successful")
    print("✓ create_integration_layer import successful")
    
    from ai_model_router import ModelRouter
    router = ModelRouter()
    print(f"✓ ModelRouter has models property: {hasattr(router, 'models')}")
    print(f"✓ ModelRouter models count: {len(router.models)}")
    
    print("\n✅ All imports successful!")
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
