"""
Browser service for the Browser Use Agent
"""

import logging
from typing import Dict, Any, Optional
from app.tools.browser_tools import BrowserTools

logger = logging.getLogger(__name__)


class BrowserService:
    """Service for managing browser interactions"""
    
    def __init__(self):
        self.browser_tools: Optional[BrowserTools] = None
        self.is_initialized = False
        
    async def initialize(self, browser_tools: Optional[BrowserTools] = None):
        """Initialize the browser service"""
        try:
            # Use shared browser tools if provided, otherwise create new instance
            if browser_tools:
                self.browser_tools = browser_tools
                logger.info("Browser service using shared browser tools")
            else:
                self.browser_tools = BrowserTools()
                logger.info("Browser service created new browser tools instance")
            
            self.is_initialized = True
            logger.info("Browser service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser service: {e}")
            raise
    
    def _ensure_initialized(self):
        """Ensure browser service is initialized"""
        if not self.is_initialized:
            raise RuntimeError("Browser service not initialized")
    
    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL"""
        logger.info(f"Browser service navigate called with URL: {url}")
        self._ensure_initialized()
        logger.info("Browser service _ensure_initialized passed")
        # Ensure browser tools are initialized (lazy initialization)
        logger.info("Calling browser_tools._ensure_initialized...")
        await self.browser_tools._ensure_initialized()
        logger.info("Browser tools _ensure_initialized completed")
        logger.info("Calling browser_tools.navigate...")
        return await self.browser_tools.navigate(url)
    
    async def click(self, selector: Optional[str] = None, coordinates: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """Click on an element or at coordinates"""
        self._ensure_initialized()
        # Ensure browser tools are initialized (lazy initialization)
        await self.browser_tools._ensure_initialized()
        return await self.browser_tools.click(selector, coordinates)
    
    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into an input field"""
        self._ensure_initialized()
        # Ensure browser tools are initialized (lazy initialization)
        await self.browser_tools._ensure_initialized()
        return await self.browser_tools.type_text(selector, text)
    
    async def scroll(self, direction: str, amount: int = 100, selector: Optional[str] = None) -> Dict[str, Any]:
        """Scroll the page or element"""
        self._ensure_initialized()
        # Ensure browser tools are initialized (lazy initialization)
        await self.browser_tools._ensure_initialized()
        return await self.browser_tools.scroll(direction, amount, selector)
    
    async def wait_for_element(self, selector: str, timeout: int = 5000) -> Dict[str, Any]:
        """Wait for an element to appear"""
        self._ensure_initialized()
        # Ensure browser tools are initialized (lazy initialization)
        await self.browser_tools._ensure_initialized()
        return await self.browser_tools.wait_for_element(selector, timeout)

    async def find_element_with_scroll(self, selector: str, max_scroll_attempts: int = 5) -> Dict[str, Any]:
        """Find an element by scrolling down if needed"""
        self._ensure_initialized()
        # Ensure browser tools are initialized (lazy initialization)
        await self.browser_tools._ensure_initialized()
        return await self.browser_tools.find_element_with_scroll(selector, max_scroll_attempts)
    
    async def get_page_info(self, include_dom: bool = True, include_screenshot: bool = False) -> Dict[str, Any]:
        """Get current page information"""
        self._ensure_initialized()
        # Ensure browser tools are initialized (lazy initialization)
        await self.browser_tools._ensure_initialized()
        return await self.browser_tools.get_page_info(include_dom, include_screenshot)
    
    async def get_current_page(self):
        """Get the current page object"""
        self._ensure_initialized()
        # Ensure browser tools are initialized (lazy initialization)
        await self.browser_tools._ensure_initialized()
        return await self.browser_tools.get_current_page()
    
    async def create_new_page(self):
        """Create a new page in the current context"""
        self._ensure_initialized()
        # Ensure browser tools are initialized (lazy initialization)
        await self.browser_tools._ensure_initialized()
        return await self.browser_tools.create_new_page()
    
    async def switch_to_page(self, page):
        """Switch to a different page"""
        self._ensure_initialized()
        # Ensure browser tools are initialized (lazy initialization)
        await self.browser_tools._ensure_initialized()
        return await self.browser_tools.switch_to_page(page)
    
    async def cleanup(self):
        """Clean up browser resources"""
        # Note: Browser tools cleanup is handled by main lifespan
        # since we're using shared browser tools
        self.is_initialized = False
        logger.info("Browser service cleaned up")

    async def is_authenticated(self) -> Dict[str, Any]:
        """Check if user is authenticated"""
        try:
            return await self.browser_tools.is_authenticated()
        except Exception as e:
            logger.error(f"Failed to check authentication: {e}")
            return {"success": False, "authenticated": False, "error": str(e)}
    
    async def get_cookies(self) -> Dict[str, Any]:
        """Get current cookies from browser"""
        try:
            await self.browser_tools._ensure_initialized()
            return await self.browser_tools.get_cookies()
        except Exception as e:
            logger.error(f"Failed to get cookies: {e}")
            return {"success": False, "error": str(e)}
    
    async def clear_cookies(self) -> Dict[str, Any]:
        """Clear all saved cookies and browser cookies"""
        try:
            await self.browser_tools._ensure_initialized()
            return await self.browser_tools.clear_cookies()
        except Exception as e:
            logger.error(f"Failed to clear cookies: {e}")
            return {"success": False, "error": str(e)}
