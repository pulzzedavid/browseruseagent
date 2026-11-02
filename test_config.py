#!/usr/bin/env python3
"""
Test configuration loading
"""

import os
from app.core.config import settings

def test_config():
    """Test if configuration is loaded correctly"""
    print("🔧 Testing configuration...")
    print(f"Browser Type: {settings.browser_type}")
    print(f"Browser Headless: {settings.browser_headless}")
    print(f"Browser Slow Mo: {settings.browser_slow_mo}")
    print(f"Browser DevTools: {settings.browser_devtools}")
    
    # Check environment variables
    print(f"\n🌍 Environment Variables:")
    print(f"BUA_FORCE_VISIBLE: {os.getenv('BUA_FORCE_VISIBLE', 'Not Set')}")
    print(f"BUA_BROWSER_TYPE: {os.getenv('BUA_BROWSER_TYPE', 'Not Set')}")

if __name__ == "__main__":
    test_config()

