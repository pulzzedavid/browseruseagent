"""
Browser API routes for the Browser Use Agent
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from app.services.browser_service import BrowserService
from app.services.tool_service import ToolService

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models
class NavigateRequest(BaseModel):
    url: str = Field(..., description="URL to navigate to")


class ClickRequest(BaseModel):
    selector: Optional[str] = Field(None, description="CSS selector or XPath")
    coordinates: Optional[Dict[str, int]] = Field(None, description="x, y coordinates")


class TypeTextRequest(BaseModel):
    selector: str = Field(..., description="CSS selector for input field")
    text: str = Field(..., description="Text to type")


class ScrollRequest(BaseModel):
    direction: str = Field(..., description="Scroll direction (up, down, left, right)")
    amount: int = Field(100, description="Scroll amount in pixels")
    selector: Optional[str] = Field(None, description="Element to scroll")


class WaitForElementRequest(BaseModel):
    selector: str = Field(..., description="CSS selector or XPath")
    timeout: int = Field(5000, description="Timeout in milliseconds")


class FindElementWithScrollRequest(BaseModel):
    selector: str = Field(..., description="CSS selector for the element to find")
    max_scroll_attempts: int = Field(5, description="Maximum number of scroll attempts")


class GetPageInfoRequest(BaseModel):
    include_dom: bool = Field(True, description="Include DOM snapshot")
    include_screenshot: bool = Field(False, description="Include screenshot")


class BrowserActionResponse(BaseModel):
    success: bool
    action: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


class PageInfoResponse(BaseModel):
    success: bool
    page_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


# Dependency to get browser service
async def get_browser_service(request: Request) -> BrowserService:
    """Get the browser service instance from app state"""
    from fastapi import Request
    return request.app.state.browser_service


@router.post("/navigate", response_model=BrowserActionResponse)
async def navigate_to_url(
    request: NavigateRequest,
    browser_service: BrowserService = Depends(get_browser_service)
):
    """Navigate to a specific URL"""
    try:
        logger.info(f"Navigating to URL: {request.url}")
        
        result = await browser_service.navigate(request.url)
        
        if result["success"]:
            return BrowserActionResponse(
                success=True,
                action="navigate",
                result=result,
                execution_time_ms=result.get("execution_time_ms")
            )
        else:
            return BrowserActionResponse(
                success=False,
                action="navigate",
                error=result.get("error", "Navigation failed")
            )
            
    except Exception as e:
        logger.error(f"Navigation failed: {e}")
        return BrowserActionResponse(
            success=False,
            action="navigate",
            error=str(e)
        )


@router.post("/click", response_model=BrowserActionResponse)
async def click_element(
    request: ClickRequest,
    browser_service: BrowserService = Depends(get_browser_service)
):
    """Click on an element or at coordinates"""
    try:
        if request.selector:
            logger.info(f"Clicking element with selector: {request.selector}")
            result = await browser_service.click(selector=request.selector)
        elif request.coordinates:
            logger.info(f"Clicking at coordinates: {request.coordinates}")
            result = await browser_service.click(coordinates=request.coordinates)
        else:
            return BrowserActionResponse(
                success=False,
                action="click",
                error="Either selector or coordinates must be provided"
            )
        
        if result["success"]:
            return BrowserActionResponse(
                success=True,
                action="click",
                result=result,
                execution_time_ms=result.get("execution_time_ms")
            )
        else:
            return BrowserActionResponse(
                success=False,
                action="click",
                error=result.get("error", "Click failed")
            )
            
    except Exception as e:
        logger.error(f"Click failed: {e}")
        return BrowserActionResponse(
            success=False,
            action="click",
            error=str(e)
        )


@router.post("/type", response_model=BrowserActionResponse)
async def type_text(
    request: TypeTextRequest,
    browser_service: BrowserService = Depends(get_browser_service)
):
    """Type text into an input field"""
    try:
        logger.info(f"Typing text into {request.selector}: {request.text[:50]}...")
        
        result = await browser_service.type_text(request.selector, request.text)
        
        if result["success"]:
            return BrowserActionResponse(
                success=True,
                action="type_text",
                result=result,
                execution_time_ms=result.get("execution_time_ms")
            )
        else:
            return BrowserActionResponse(
                success=False,
                action="type_text",
                error=result.get("error", "Type text failed")
            )
            
    except Exception as e:
        logger.error(f"Type text failed: {e}")
        return BrowserActionResponse(
            success=False,
            action="type_text",
            error=str(e)
        )


@router.post("/scroll", response_model=BrowserActionResponse)
async def scroll_page(
    request: ScrollRequest,
    browser_service: BrowserService = Depends(get_browser_service)
):
    """Scroll the page or element"""
    try:
        logger.info(f"Scrolling {request.direction} by {request.amount}px")
        
        result = await browser_service.scroll(
            direction=request.direction,
            amount=request.amount,
            selector=request.selector
        )
        
        if result["success"]:
            return BrowserActionResponse(
                success=True,
                action="scroll",
                result=result,
                execution_time_ms=result.get("execution_time_ms")
            )
        else:
            return BrowserActionResponse(
                success=False,
                action="scroll",
                error=result.get("error", "Scroll failed")
            )
            
    except Exception as e:
        logger.error(f"Scroll failed: {e}")
        return BrowserActionResponse(
            success=False,
            action="scroll",
            error=str(e)
        )


@router.post("/wait", response_model=BrowserActionResponse)
async def wait_for_element(
    request: WaitForElementRequest,
    browser_service: BrowserService = Depends(get_browser_service)
):
    """Wait for an element to appear"""
    try:
        logger.info(f"Waiting for element: {request.selector}")
        
        result = await browser_service.wait_for_element(
            request.selector,
            request.timeout
        )
        
        if result["success"]:
            return BrowserActionResponse(
                success=True,
                action="wait_for_element",
                result=result,
                execution_time_ms=result.get("execution_time_ms")
            )
        else:
            return BrowserActionResponse(
                success=False,
                action="wait_for_element",
                error=result.get("error", "Wait for element failed")
            )
            
    except Exception as e:
        logger.error(f"Wait for element failed: {e}")
        return BrowserActionResponse(
            success=False,
            action="wait_for_element",
            error=str(e)
        )


@router.post("/find-element-with-scroll", response_model=BrowserActionResponse)
async def find_element_with_scroll(
    request: FindElementWithScrollRequest,
    browser_service: BrowserService = Depends(get_browser_service)
):
    """Find an element by scrolling down if needed"""
    try:
        logger.info(f"Finding element with scroll: {request.selector}")
        
        result = await browser_service.find_element_with_scroll(
            request.selector,
            request.max_scroll_attempts
        )
        
        if result["success"]:
            return BrowserActionResponse(
                success=True,
                action="find_element_with_scroll",
                result=result,
                execution_time_ms=result.get("execution_time_ms")
            )
        else:
            return BrowserActionResponse(
                success=False,
                action="find_element_with_scroll",
                error=result.get("error", "Find element with scroll failed")
            )
            
    except Exception as e:
        logger.error(f"Find element with scroll failed: {e}")
        return BrowserActionResponse(
            success=False,
            action="find_element_with_scroll",
            error=str(e)
        )


@router.post("/page-info", response_model=PageInfoResponse)
async def get_page_info(
    request: GetPageInfoRequest,
    browser_service: BrowserService = Depends(get_browser_service)
):
    """Get current page information"""
    try:
        logger.info("Getting page information")
        
        result = await browser_service.get_page_info(
            include_dom=request.include_dom,
            include_screenshot=request.include_screenshot
        )
        
        if result["success"]:
            return PageInfoResponse(
                success=True,
                page_info=result["page_info"],
                execution_time_ms=result.get("execution_time_ms")
            )
        else:
            return PageInfoResponse(
                success=False,
                error=result.get("error", "Get page info failed")
            )
            
    except Exception as e:
        logger.error(f"Get page info failed: {e}")
        return PageInfoResponse(
            success=False,
            error=str(e)
        )


@router.get("/current-url")
async def get_current_url(
    browser_service: BrowserService = Depends(get_browser_service)
):
    """Get the current URL"""
    try:
        page_info = await browser_service.get_page_info(include_dom=False)
        
        if page_info["success"]:
            return {
                "success": True,
                "url": page_info["page_info"]["url"],
                "title": page_info["page_info"]["title"]
            }
        else:
            return {
                "success": False,
                "error": page_info.get("error", "Failed to get current URL")
            }
            
    except Exception as e:
        logger.error(f"Failed to get current URL: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/refresh")
async def refresh_page(
    browser_service: BrowserService = Depends(get_browser_service)
):
    """Refresh the current page"""
    try:
        # This would need to be implemented in the browser service
        # For now, return a placeholder response
        return {
            "success": True,
            "message": "Page refresh not yet implemented"
        }
        
    except Exception as e:
        logger.error(f"Failed to refresh page: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/back")
async def go_back(
    browser_service: BrowserService = Depends(get_browser_service)
):
    """Go back to the previous page"""
    try:
        # This would need to be implemented in the browser service
        # For now, return a placeholder response
        return {
            "success": True,
            "message": "Go back not yet implemented"
        }
        
    except Exception as e:
        logger.error(f"Failed to go back: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/forward")
async def go_forward(
    browser_service: BrowserService = Depends(get_browser_service)
):
    """Go forward to the next page"""
    try:
        # This would need to be implemented in the browser service
        # For now, return a placeholder response
        return {
            "success": True,
            "message": "Go forward not yet implemented"
        }
        
    except Exception as e:
        logger.error(f"Failed to go forward: {e}")
        return {
            "success": False,
            "error": str(e)
        }
