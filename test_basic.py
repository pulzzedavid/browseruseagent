#!/usr/bin/env python3
"""
Basic test script for the Browser Use Agent
"""

import asyncio
import logging
from app.services.tool_service import ToolService
from app.services.browser_service import BrowserService
from app.services.llm_service import LLMService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_tool_service():
    """Test the tool service initialization"""
    try:
        logger.info("Testing tool service...")
        
        tool_service = ToolService()
        await tool_service.initialize()
        
        # Get available tools
        tools = tool_service.get_all_tools()
        logger.info(f"Tool service initialized with {len(tools)} tools")
        
        # List tools by type
        browser_tools = tool_service.get_tools_by_type("browser")
        system_tools = tool_service.get_tools_by_type("system")
        custom_tools = tool_service.get_tools_by_type("custom")
        
        logger.info(f"Browser tools: {len(browser_tools)}")
        logger.info(f"System tools: {len(system_tools)}")
        logger.info(f"Custom tools: {len(custom_tools)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Tool service test failed: {e}")
        return False


async def test_browser_service():
    """Test the browser service initialization"""
    try:
        logger.info("Testing browser service...")
        
        browser_service = BrowserService()
        await browser_service.initialize()
        
        logger.info("Browser service initialized successfully")
        
        # Clean up
        await browser_service.cleanup()
        
        return True
        
    except Exception as e:
        logger.error(f"Browser service test failed: {e}")
        return False


async def test_llm_service():
    """Test the LLM service initialization"""
    try:
        logger.info("Testing LLM service...")
        
        # Create a mock tool service for testing
        tool_service = ToolService()
        await tool_service.initialize()
        
        llm_service = LLMService(tool_service)
        
        # This will fail without API keys, but we can test the initialization
        try:
            await llm_service.initialize()
            logger.info("LLM service initialized successfully")
            return True
        except RuntimeError as e:
            if "No LLM API key configured" in str(e):
                logger.info("LLM service test skipped (no API keys configured)")
                return True
            else:
                raise
        
    except Exception as e:
        logger.error(f"LLM service test failed: {e}")
        return False


async def main():
    """Run all tests"""
    logger.info("Starting Browser Use Agent tests...")
    
    tests = [
        ("Tool Service", test_tool_service),
        ("Browser Service", test_browser_service),
        ("LLM Service", test_llm_service),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running {test_name} test...")
        
        try:
            result = await test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"✅ {test_name} test PASSED")
            else:
                logger.error(f"❌ {test_name} test FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name} test FAILED with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
