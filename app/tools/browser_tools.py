"""
Browser automation tools using Playwright
"""

import logging
import asyncio
import time
import os
import json
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from datetime import datetime
import base64

from app.core.config import settings

logger = logging.getLogger(__name__)


class BrowserTools:
    """Browser automation tools using Playwright"""
    
    def __init__(self):
        self.playwright_context = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_initialized = False
        self.browser_type = "firefox"
        self.cookies_file = Path("browser_cookies.json")
        self.user_data_dir = Path("browser_user_data")
        
    async def _ensure_initialized(self):
        """Ensure browser is initialized, initialize if needed"""
        logger.info(f"Browser tools _ensure_initialized called, is_initialized: {self.is_initialized}")
        if not self.is_initialized:
            logger.info("Browser tools not initialized, calling _initialize_browser...")
            await self._initialize_browser()
            logger.info(f"Browser tools initialization complete, is_initialized: {self.is_initialized}")
        else:
            logger.info("Browser tools already initialized")
    
    async def initialize(self):
        """Initialize Playwright and browser (public method)"""
        await self._ensure_initialized()
    
    async def _initialize_browser(self):
        """Initialize browser with configuration"""
        try:
            # Check if already initialized
            if self.is_initialized:
                logger.info("Browser already initialized, skipping initialization")
                return
                
            logger.info("🚀 Launching browser with configuration:")
            logger.info(f"   - Type: {self.browser_type}")
            logger.info(f"   - Headless: {os.getenv('BUA_FORCE_VISIBLE', 'false').lower() == 'true'}")
            logger.info(f"   - Slow Mo: {os.getenv('BUA_SLOW_MO', '100')}ms")
            logger.info(f"   - DevTools: {os.getenv('BUA_DEVTOOLS', 'true').lower() == 'true'}")
            
            self.playwright = await async_playwright().start()
            
            # Create user data directory for persistent storage
            self.user_data_dir.mkdir(exist_ok=True)
            
            if self.browser_type == "firefox":
                self.browser = await self.playwright.firefox.launch(
                    headless=False,
                    slow_mo=100,
                    devtools=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor"
                    ]
                )
                
                # Firefox doesn't support user_data_dir in new_context, use launch_persistent_context instead
                # But since we already launched, we'll use regular context and handle cookies separately
                self.context = await self.browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    accept_downloads=True
                )
                
            elif self.browser_type == "chromium":
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
                    slow_mo=100,
                    devtools=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor"
                    ]
                )
                
                # Chromium supports user_data_dir
                self.context = await self.browser.new_context(
                    user_data_dir=str(self.user_data_dir / "chromium"),
                    viewport={"width": 1920, "height": 1080},
                    accept_downloads=True
                )
            
            # Restore cookies if they exist
            await self._restore_cookies()
            
            # Create only one page
            if not self.page:
                self.page = await self.context.new_page()
                self.page.set_default_timeout(30000)
            
            # macOS-specific: Bring browser to front
            if os.name == 'posix' and os.uname().sysname == 'Darwin':
                try:
                    import subprocess
                    if self.browser_type == "firefox":
                        subprocess.run(['osascript', '-e', 'tell application "Firefox" to activate'], check=False)
                    elif self.browser_type == "chromium":
                        subprocess.run(['osascript', '-e', 'tell application "Chromium" to activate'], check=False)
                    logger.info("🔝 Attempted to bring Firefox to front on macOS")
                except Exception as e:
                    logger.warning(f"Failed to bring browser to front: {e}")
            
            self.is_initialized = True
            logger.info(f"✅ Browser launched successfully")
            logger.info(f"Browser tools initialized with {self.browser_type}")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            await self.cleanup()
            raise
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            logger.info("Cleaning up browser tools...")
            
            if hasattr(self, 'page') and self.page:
                try:
                    await self.page.close()
                    logger.info("Page closed successfully")
                except Exception as e:
                    logger.warning(f"Error closing page: {e}")
                finally:
                    self.page = None
            
            if hasattr(self, 'context') and self.context:
                try:
                    await self.context.close()
                    logger.info("Browser context closed successfully")
                except Exception as e:
                    logger.warning(f"Error closing browser context: {e}")
                finally:
                    self.context = None
            
            if hasattr(self, 'browser') and self.browser:
                try:
                    await self.browser.close()
                    logger.info("Browser closed successfully")
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
                finally:
                    self.browser = None
            
            if hasattr(self, 'playwright_context') and self.playwright_context:
                try:
                    await self.playwright_context.stop()
                    logger.info("Playwright stopped successfully")
                except Exception as e:
                    logger.warning(f"Error stopping Playwright: {e}")
                finally:
                    self.playwright_context = None
            
            self.is_initialized = False
            logger.info("Browser tools cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during browser cleanup: {e}")
            # Don't re-raise, just log the error
            self.is_initialized = False
    
    async def _check_browser_health(self):
        """Check if browser is still accessible and recover if needed"""
        try:
            if not self.context or not self.page:
                logger.warning("Browser context or page is missing, attempting recovery...")
                await self._recover_browser_context()
                return True
            
            # Try to get page info to test if context is alive
            try:
                await self.page.title()
                return True
            except Exception as e:
                logger.warning(f"Page context check failed: {e}, attempting recovery...")
                await self._recover_browser_context()
                return True
                
        except Exception as e:
            logger.error(f"Browser health check failed: {e}")
            return False
    
    async def _recover_browser_context(self):
        """Recover browser context when it gets destroyed"""
        try:
            logger.info("🔄 Attempting to recover browser context...")
            
            # Close existing context if it exists
            if self.context:
                try:
                    await self.context.close()
                except:
                    pass
            
            # Create new context
            if self.browser_type == "firefox":
                self.context = await self.browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    accept_downloads=True
                )
            elif self.browser_type == "chromium":
                self.context = await self.browser.new_context(
                    user_data_dir=str(self.user_data_dir / "chromium"),
                    viewport={"width": 1920, "height": 1080},
                    accept_downloads=True
                )
            
            # Create new page
            self.page = await self.context.new_page()
            self.page.set_default_timeout(30000)
            
            # Restore cookies
            await self._restore_cookies()
            
            logger.info("✅ Browser context recovered successfully")
            
        except Exception as e:
            logger.error(f"Failed to recover browser context: {e}")
            # If recovery fails, we need to reinitialize the entire browser
            await self.cleanup()
            await self._initialize_browser()
    
    # Note: This method was removed to avoid conflicts with the async _ensure_initialized method
    # The async method handles both initialization and checking
    
    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL"""
        start_time = time.time()
        try:
            # Ensure browser is initialized
            await self._ensure_initialized()
            
            # Check browser health before navigation
            await self._check_browser_health()
            
            logger.info(f"🌐 Navigating to: {url}")
            
            # Navigate to the URL
            await self.page.goto(url, wait_until="networkidle")
            
            # Wait a bit for page to fully load
            await asyncio.sleep(2)
            
            # Save cookies after successful navigation
            await self._save_cookies()
            
            execution_time = int((time.time() - start_time) * 1000)
            logger.info(f"✅ Navigation successful to: {url}")
            
            return {
                "success": True,
                "url": url,
                "execution_time_ms": execution_time,
                "message": f"Successfully navigated to {url}"
            }
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = f"Navigation to {url} failed: {e}"
            logger.error(error_msg)
            
            # Try to recover browser context if navigation failed
            try:
                await self._check_browser_health()
            except Exception as recovery_error:
                logger.error(f"Failed to recover browser after navigation error: {recovery_error}")
            
            return {
                "success": False,
                "url": url,
                "execution_time_ms": execution_time,
                "error": error_msg
            }
    
    async def click(self, selector: str, coordinates: Optional[Tuple[int, int]] = None) -> Dict[str, Any]:
        """Click on an element"""
        try:
            if not self._check_browser_health():
                return {
                    "success": False,
                    "error": "Browser is not accessible or has been closed"
                }
            
            if not self.page:
                return {
                    "success": False,
                    "error": "No active page"
                }
            
            if coordinates:
                logger.info(f"🖱️ Clicking at coordinates: {coordinates}")
                await self.page.click("body", position=coordinates)
            else:
                logger.info(f"🖱️ Clicking element: {selector}")
                await self.page.click(selector)
            
            # Save cookies after click (in case of authentication)
            await self._save_cookies()
            
            logger.info("✅ Click successful")
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Click action failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into an input field"""
        try:
            if not self._check_browser_health():
                return {
                    "success": False,
                    "error": "Browser is not accessible or has been closed"
                }
            
            if not self.page:
                return {
                    "success": False,
                    "error": "No active page"
                }
            
            logger.info(f"⌨️ Typing text in element: {selector}")
            
            # Clear the field first
            await self.page.fill(selector, "")
            # Type the text
            await self.page.type(selector, text)
            
            # Save cookies after text input (in case of form submission)
            await self._save_cookies()
            
            logger.info(f"✅ Successfully typed text into {selector}")
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Type text action failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def clear_cookies(self) -> Dict[str, Any]:
        """Clear all saved cookies and browser cookies"""
        try:
            await self._clear_cookies()
            return {"success": True, "message": "Cookies cleared successfully"}
        except Exception as e:
            logger.error(f"Failed to clear cookies: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_cookies(self) -> Dict[str, Any]:
        """Get current cookies from browser"""
        try:
            if not self.context:
                return {"success": False, "error": "No browser context"}
            
            cookies = await self.context.cookies()
            return {
                "success": True,
                "cookies": cookies,
                "count": len(cookies)
            }
        except Exception as e:
            logger.error(f"Failed to get cookies: {e}")
            return {"success": False, "error": str(e)}
    
    async def is_authenticated(self) -> Dict[str, Any]:
        """Check if user is authenticated by examining cookies and page content"""
        try:
            if not self.context:
                return {"success": False, "authenticated": False, "error": "No browser context"}
            
            # Get all cookies
            cookies = await self.context.cookies()
            
            # Look for authentication-related cookies
            auth_cookies = []
            for cookie in cookies:
                cookie_name = cookie.get("name", "").lower()
                cookie_value = cookie.get("value", "")
                
                # Check for common authentication cookie patterns
                if any(indicator in cookie_name for indicator in ["session", "token", "auth", "jwt", "id_token", "access_token"]):
                    if cookie_value and cookie_value != "null" and cookie_value != "undefined":
                        auth_cookies.append({
                            "name": cookie.get("name"),
                            "value": cookie.get("value")[:20] + "..." if len(cookie.get("value", "")) > 20 else cookie.get("value"),
                            "domain": cookie.get("domain"),
                            "path": cookie.get("path")
                        })
                
                # Check for Google OAuth specific cookies
                if any(indicator in cookie_name for indicator in ["google", "oauth", "gid", "ga"]):
                    if cookie_value and cookie_value != "null" and cookie_value != "undefined":
                        auth_cookies.append({
                            "name": cookie.get("name"),
                            "value": cookie.get("value")[:20] + "..." if len(cookie.get("value", "")) > 20 else cookie.get("value"),
                            "domain": cookie.get("domain"),
                            "path": cookie.get("path")
                        })
            
            # Check page content for authentication indicators
            page_auth_indicators = []
            try:
                if self.page:
                    # Check page title for authentication indicators
                    title = await self.page.title()
                    if title:
                        title_lower = title.lower()
                        if any(indicator in title_lower for indicator in ["dashboard", "home", "buttons", "welcome", "logged in"]):
                            page_auth_indicators.append(f"Page title: {title}")
                    
                    # Check for logout buttons (indicates user is logged in)
                    logout_elements = await self.page.query_selector_all('button, a, [role="button"]')
                    for element in logout_elements[:10]:  # Check first 10 elements
                        try:
                            text = await element.text_content()
                            if text and any(indicator in text.lower() for indicator in ["logout", "sign out", "log out"]):
                                page_auth_indicators.append(f"Logout button found: {text}")
                        except:
                            continue
                            
            except Exception as e:
                logger.warning(f"Error checking page content for auth: {e}")
            
            # Determine authentication status
            is_authenticated = False
            auth_reason = []
            
            # If we have auth cookies, user is likely authenticated
            if auth_cookies:
                is_authenticated = True
                auth_reason.append(f"Found {len(auth_cookies)} authentication cookies")
            
            # If we have page indicators, user is likely authenticated
            if page_auth_indicators:
                is_authenticated = True
                auth_reason.append(f"Found {len(page_auth_indicators)} page authentication indicators")
            
            # If we have many cookies (>10), user is likely authenticated (common in web apps)
            if len(cookies) > 10:
                is_authenticated = True
                auth_reason.append(f"Found {len(cookies)} total cookies (likely authenticated)")
            
            logger.info(f"Authentication check: {len(auth_cookies)} auth cookies, {len(page_auth_indicators)} page indicators, {len(cookies)} total cookies")
            logger.info(f"Authentication result: {is_authenticated} - {', '.join(auth_reason)}")
            
            return {
                "success": True,
                "authenticated": is_authenticated,
                "auth_cookies": auth_cookies,
                "page_indicators": page_auth_indicators,
                "total_cookies": len(cookies),
                "auth_reason": auth_reason
            }
            
        except Exception as e:
            logger.error(f"Authentication check failed: {e}")
            return {"success": False, "authenticated": False, "error": str(e)}
    
    async def scroll(self, direction: str, amount: int = 100, selector: Optional[str] = None) -> Dict[str, Any]:
        """Scroll the page or element"""
        await self._ensure_initialized()
        
        try:
            start_time = time.time()
            
            if selector:
                # Scroll specific element
                element = await self.page.wait_for_selector(selector, timeout=5000)
                if direction == "down":
                    await element.evaluate(f"this.scrollTop += {amount}")
                elif direction == "up":
                    await element.evaluate(f"this.scrollTop -= {amount}")
                elif direction == "left":
                    await element.evaluate(f"this.scrollLeft -= {amount}")
                elif direction == "right":
                    await element.evaluate(f"this.scrollLeft += {amount}")
            else:
                # Scroll page
                if direction == "down":
                    await self.page.evaluate(f"window.scrollBy(0, {amount})")
                elif direction == "up":
                    await self.page.evaluate(f"window.scrollBy(0, -{amount})")
                elif direction == "left":
                    await self.page.evaluate(f"window.scrollBy(-{amount}, 0)")
                elif direction == "right":
                    await self.page.evaluate(f"window.scrollBy({amount}, 0)")
            
            execution_time = int((time.time() - start_time) * 1000)
            
            result = {
                "success": True,
                "direction": direction,
                "amount": amount,
                "selector": selector,
                "execution_time_ms": execution_time
            }
            
            logger.info(f"Successfully scrolled {direction} by {amount}px")
            return result
            
        except Exception as e:
            logger.error(f"Scroll action failed: {e}")
            return {
                "success": False,
                "direction": direction,
                "amount": amount,
                "selector": selector,
                "error": str(e),
                "execution_time_ms": 0
            }
    
    async def wait_for_element(self, selector: str, timeout: int = 5000) -> Dict[str, Any]:
        """Wait for an element to appear"""
        await self._ensure_initialized()
        
        try:
            start_time = time.time()
            
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            result = {
                "success": True,
                "selector": selector,
                "timeout": timeout,
                "execution_time_ms": execution_time,
                "element_found": element is not None
            }
            
            logger.info(f"Successfully waited for element: {selector}")
            return result
            
        except Exception as e:
            logger.error(f"Wait for element failed: {e}")
            return {
                "success": False,
                "selector": selector,
                "timeout": timeout,
                "error": str(e),
                "execution_time_ms": 0
            }
    
    async def get_page_info(self, include_dom: bool = True, include_screenshot: bool = False) -> Dict[str, Any]:
        """Get comprehensive information about the current page"""
        try:
            # Ensure browser is initialized
            await self._ensure_initialized()
            
            # Check browser health before getting page info
            await self._check_browser_health()
            
            if not self.page:
                return {"success": False, "error": "No active page"}
            
            # Get basic page information
            page_info = {
                "url": self.page.url,
                "title": await self.page.title(),
                "timestamp": datetime.now().isoformat()
            }
            
            if include_dom:
                # Get DOM snapshot
                dom_info = await self._get_simplified_dom()
                page_info["dom"] = dom_info
                
                # Get viewport information
                viewport_info = await self.page.evaluate("""
                    () => {
                        return {
                            width: window.innerWidth,
                            height: window.innerHeight,
                            scrollX: window.scrollX,
                            scrollY: window.scrollY,
                            scrollHeight: document.documentElement.scrollHeight,
                            scrollWidth: document.documentElement.scrollWidth
                        }
                    }
                """)
                page_info["viewport_info"] = viewport_info
            
            if include_screenshot:
                try:
                    screenshot_bytes = await self.page.screenshot()
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    page_info["screenshot"] = screenshot_b64
                except Exception as e:
                    logger.warning(f"Failed to capture screenshot: {e}")
                    page_info["screenshot_error"] = str(e)
            
            return {
                "success": True,
                "page_info": page_info
            }
            
        except Exception as e:
            error_msg = f"Get page info failed: {e}"
            logger.error(error_msg)
            
            # Try to recover browser context if getting page info failed
            try:
                await self._check_browser_health()
            except Exception as recovery_error:
                logger.error(f"Failed to recover browser after get_page_info error: {recovery_error}")
            
            return {"success": False, "error": error_msg}

    async def find_element_with_scroll(self, selector: str, max_scroll_attempts: int = 5) -> Dict[str, Any]:
        """Find an element by scrolling down if needed"""
        await self._ensure_initialized()
        
        try:
            start_time = time.time()
            
            # First try to find the element without scrolling
            element = await self.page.query_selector(selector)
            if element:
                execution_time = int((time.time() - start_time) * 1000)
                return {
                    "success": True,
                    "selector": selector,
                    "found_without_scroll": True,
                    "execution_time_ms": execution_time
                }
            
            # If not found, try scrolling down progressively
            logger.info(f"Element {selector} not visible, attempting to scroll down to find it...")
            
            for attempt in range(max_scroll_attempts):
                # Scroll down by viewport height
                await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
                await self.page.wait_for_timeout(500)  # Wait for scroll to settle
                
                # Try to find the element again
                element = await self.page.query_selector(selector)
                if element:
                    execution_time = int((time.time() - start_time) * 1000)
                    logger.info(f"Found element {selector} after scrolling down {attempt + 1} times")
                    return {
                        "success": True,
                        "selector": selector,
                        "found_without_scroll": False,
                        "scroll_attempts": attempt + 1,
                        "execution_time_ms": execution_time
                    }
                
                logger.info(f"Scroll attempt {attempt + 1}: Element {selector} still not found")
            
            # Element not found even after scrolling
            execution_time = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "selector": selector,
                "error": f"Element not found after {max_scroll_attempts} scroll attempts",
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            logger.error(f"Find element with scroll failed: {e}")
            return {
                "success": False,
                "selector": selector,
                "error": str(e),
                "execution_time_ms": 0
            }

    async def _get_basic_page_info(self) -> Dict[str, Any]:
        """Get basic page information"""
        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "viewport": {
                "width": settings.browser_viewport_width,
                "height": settings.browser_viewport_height
            }
        }
    
    async def _get_simplified_dom(self) -> Dict[str, Any]:
        """Get simplified DOM representation"""
        try:
            # Execute JavaScript to get simplified DOM
            dom_data = await self.page.evaluate("""
                () => {
                    function simplifyElement(element) {
                        const simplified = {
                            tagName: element.tagName.toLowerCase(),
                            id: element.id || null,
                            className: element.className || null,
                            textContent: element.textContent?.trim().substring(0, 100) || null,
                            attributes: {},
                            isVisible: element.offsetParent !== null,
                            boundingRect: element.getBoundingClientRect()
                        };
                        
                        // Get important attributes
                        const importantAttrs = ['href', 'src', 'alt', 'title', 'placeholder', 'value', 'type'];
                        for (const attr of importantAttrs) {
                            if (element.hasAttribute(attr)) {
                                simplified.attributes[attr] = element.getAttribute(attr);
                            }
                        }
                        
                        return simplified;
                    }
                    
                    function getInteractiveElements() {
                        const selectors = 'button, input, select, textarea, a, [role="button"], [tabindex]';
                        const elements = document.querySelectorAll(selectors);
                        const simplified = [];
                        
                        for (const element of elements) {
                            // Include all elements, not just visible ones
                            const elementInfo = simplifyElement(element);
                            elementInfo.aboveFold = elementInfo.boundingRect.top < window.innerHeight;
                            simplified.push(elementInfo);
                        }
                        
                        return simplified;
                    }
                    
                    return {
                        interactive_elements: getInteractiveElements(),
                        page_structure: {
                            headings: Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'))
                                .map(h => ({ level: h.tagName[1], text: h.textContent?.trim().substring(0, 100) || '' })),
                            forms: Array.from(document.querySelectorAll('form'))
                                .map(f => ({ action: f.action, method: f.method || 'get' })),
                            images: Array.from(document.querySelectorAll('img'))
                                .map(img => ({ src: img.src, alt: img.alt || '' }))
                        },
                        viewport_info: {
                            height: window.innerHeight,
                            scrollY: window.scrollY,
                            documentHeight: document.documentElement.scrollHeight
                        }
                    };
                }
            """)
            
            return dom_data
            
        except Exception as e:
            logger.error(f"Failed to get simplified DOM: {e}")
            return {"error": str(e)}
    
    async def _take_screenshot(self) -> str:
        """Take a screenshot and save it"""
        try:
            # Create screenshots directory
            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            
            # Generate filename
            timestamp = int(time.time())
            filename = f"screenshot_{timestamp}.png"
            filepath = screenshots_dir / filename
            
            # Take screenshot
            await self.page.screenshot(path=str(filepath))
            
            logger.info(f"Screenshot saved to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return ""
    
    async def get_current_page(self) -> Optional[Page]:
        """Get the current page object"""
        return self.page if self.is_initialized else None
    
    async def create_new_page(self) -> Page:
        """Create a new page in the current context"""
        await self._ensure_initialized()
        return await self.context.new_page()
    
    async def switch_to_page(self, page: Page):
        """Switch to a different page"""
        if page and page in self.context.pages:
            self.page = page
            logger.info("Switched to different page")
        else:
            raise ValueError("Invalid page object")

    async def _restore_cookies(self):
        """Restore cookies from file if they exist"""
        try:
            if not self.cookies_file.exists():
                logger.info("No saved cookies found")
                return
                
            with open(self.cookies_file, 'r') as f:
                cookies_data = json.load(f)
            
            # Check if cookies are for the same browser type
            if cookies_data.get("browser_type") != self.browser_type:
                logger.info(f"Saved cookies are for {cookies_data.get('browser_type')}, current browser is {self.browser_type}")
                return
            
            # Check if cookies are not too old (24 hours)
            cookie_age = time.time() - cookies_data.get("timestamp", 0)
            if cookie_age > 86400:  # 24 hours
                logger.info("Saved cookies are too old, not restoring")
                return
            
            cookies = cookies_data.get("cookies", [])
            if cookies and self.context:
                await self.context.add_cookies(cookies)
                logger.info(f"🔄 Restored {len(cookies)} cookies from {self.cookies_file}")
                
                # For Firefox, we need to be more aggressive about cookie restoration
                if self.browser_type == "firefox":
                    logger.info("Firefox detected - cookies restored, but may need page refresh for full effect")
            else:
                logger.info("No valid cookies to restore")
                
        except Exception as e:
            logger.warning(f"Failed to restore cookies: {e}")
    
    async def _save_cookies(self):
        """Save cookies to file for persistence"""
        try:
            if not self.context:
                return
                
            cookies = await self.context.cookies()
            if cookies:
                cookies_data = {
                    "timestamp": time.time(),
                    "browser_type": self.browser_type,
                    "cookies": cookies
                }
                
                with open(self.cookies_file, 'w') as f:
                    json.dump(cookies_data, f, indent=2)
                
                logger.info(f"💾 Saved {len(cookies)} cookies to {self.cookies_file}")
                
                # For Firefox, log more details about authentication cookies
                if self.browser_type == "firefox":
                    auth_cookies = [c for c in cookies if any(indicator in c.get("name", "").lower() 
                                                          for indicator in ["session", "token", "auth", "jwt"])]
                    if auth_cookies:
                        logger.info(f"Firefox auth cookies saved: {[c.get('name') for c in auth_cookies]}")
            else:
                logger.info("No cookies to save")
                
        except Exception as e:
            logger.warning(f"Failed to save cookies: {e}")
