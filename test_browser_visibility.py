#!/usr/bin/env python3
"""
Test script to verify browser visibility
"""

import asyncio
import os
from playwright.async_api import async_playwright

async def test_browser_visibility():
    """Test if browser opens visibly"""
    print("🚀 Testing browser visibility...")
    
    # Force visible mode
    os.environ["BUA_FORCE_VISIBLE"] = "true"
    
    async with async_playwright() as p:
        print("📱 Launching Chromium browser...")
        
        # Launch browser with explicit visible settings
        browser = await p.chromium.launch(
            headless=False,  # Explicitly set to False
            slow_mo=1000,   # Slow down for visibility
            devtools=True,   # Open DevTools
            args=[
                '--start-maximized',
                '--disable-web-security',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        
        print("✅ Browser launched!")
        
        # Create context and page
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        print("🌐 Navigating to example.com...")
        await page.goto('https://example.com')
        
        print("⏳ Waiting 10 seconds for you to see the browser...")
        print("🔍 Look for a Chromium browser window on your screen!")
        
        # Wait for user to see the browser
        await asyncio.sleep(10)
        
        print("🔄 Taking a screenshot...")
        await page.screenshot(path="test_visibility.png")
        print("📸 Screenshot saved as 'test_visibility.png'")
        
        print("🧹 Cleaning up...")
        await browser.close()
        print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_browser_visibility())

