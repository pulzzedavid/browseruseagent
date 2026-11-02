#!/usr/bin/env python3
"""
Simple browser visibility test
"""

import asyncio
from playwright.async_api import async_playwright

async def simple_browser_test():
    """Simple test to see if browser opens"""
    print("🚀 Simple browser test...")
    
    async with async_playwright() as p:
        print("📱 Trying to launch Firefox...")
        
        try:
            # Try Firefox with minimal options
            browser = await p.firefox.launch(
                headless=False,
                slow_mo=2000
            )
            
            print("✅ Firefox launched!")
            
            # Create a simple page
            page = await browser.new_page()
            print("📄 Page created!")
            
            # Navigate to a simple page
            await page.goto('https://example.com')
            print("🌐 Navigated to example.com")
            
            # Wait and check if we can see anything
            print("⏳ Waiting 15 seconds...")
            print("🔍 Look for a Firefox window!")
            print("💡 If you don't see it, check:")
            print("   - Dock (bottom of screen)")
            print("   - Mission Control (swipe up with 3 fingers)")
            print("   - Other desktops")
            
            await asyncio.sleep(15)
            
            # Take screenshot to verify
            await page.screenshot(path="firefox_test.png")
            print("📸 Screenshot saved as 'firefox_test.png'")
            
            await browser.close()
            print("✅ Test completed!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print("🔧 Trying alternative approach...")
            
            try:
                # Try with even simpler options
                browser = await p.firefox.launch(headless=False)
                print("✅ Firefox launched with minimal options!")
                
                page = await browser.new_page()
                await page.goto('https://example.com')
                print("🌐 Navigated to example.com")
                
                print("⏳ Waiting 10 seconds...")
                await asyncio.sleep(10)
                
                await browser.close()
                print("✅ Alternative test completed!")
                
            except Exception as e2:
                print(f"❌ Alternative approach also failed: {e2}")

if __name__ == "__main__":
    asyncio.run(simple_browser_test())

