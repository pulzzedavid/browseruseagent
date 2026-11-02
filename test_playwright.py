#!/usr/bin/env python3
"""
Simple Playwright test to debug installation issues
"""

import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_playwright():
    """Test basic Playwright functionality"""
    try:
        logger.info("Testing Playwright import...")
        from playwright.async_api import async_playwright
        
        logger.info("Testing Playwright start...")
        async with async_playwright() as p:
            logger.info("Playwright started successfully")
            
            # Try to launch browser
            logger.info("Testing browser launch...")
            try:
                browser = await p.chromium.launch(headless=True)
                logger.info("Chromium browser launched successfully")
                
                # Create context
                context = await browser.new_context()
                logger.info("Browser context created successfully")
                
                # Create page
                page = await context.new_page()
                logger.info("Browser page created successfully")
                
                # Navigate to a simple page
                await page.goto("data:text/html,<h1>Hello World</h1>")
                logger.info("Page navigation successful")
                
                # Get page content
                content = await page.content()
                logger.info(f"Page content: {content[:100]}...")
                
                # Cleanup
                await page.close()
                await context.close()
                await browser.close()
                logger.info("Browser cleanup successful")
                
                return True
                
            except Exception as e:
                logger.error(f"Browser launch failed: {e}")
                return False
                
    except Exception as e:
        logger.error(f"Playwright test failed: {e}")
        return False

async def main():
    """Run the test"""
    logger.info("Starting Playwright test...")
    
    success = await test_playwright()
    
    if success:
        logger.info("✅ Playwright test PASSED")
    else:
        logger.error("❌ Playwright test FAILED")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())

