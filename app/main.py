"""
Main FastAPI application for the Browser Use Agent
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.api.routes import agent, browser
from app.core.database import init_db, close_db
from app.services.tool_service import ToolService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Browser Use Agent...")
    
    # Try to initialize database, but don't fail if it's not available
    try:
        await init_db()
        logger.info("Database connection established")
    except Exception as e:
        logger.warning(f"Database initialization failed (continuing without database): {e}")
    
    # Create single browser tools instance to share across services (but don't initialize yet)
    from app.tools.browser_tools import BrowserTools
    browser_tools = BrowserTools()
    # Note: We don't call initialize() here - it will be initialized lazily when first needed
    
    # Initialize tool service with shared browser tools
    tool_service = ToolService()
    await tool_service.initialize(browser_tools)
    
    # Initialize browser service with shared browser tools
    from app.services.browser_service import BrowserService
    browser_service = BrowserService()
    await browser_service.initialize(browser_tools)
    
    # Initialize agent service
    from app.services.agent_service import AgentService
    agent_service = AgentService()
    await agent_service.initialize(tool_service, browser_service)
    
    # Store services in app state for sharing
    app.state.tool_service = tool_service
    app.state.browser_service = browser_service
    app.state.agent_service = agent_service
    app.state.browser_tools = browser_tools
    
    logger.info("Browser Use Agent started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Browser Use Agent...")
    
    # Clean up shared browser tools
    if hasattr(app.state, 'browser_tools') and app.state.browser_tools:
        try:
            await app.state.browser_tools.cleanup()
            logger.info("Shared browser tools cleaned up")
        except Exception as e:
            logger.warning(f"Browser tools cleanup failed: {e}")
    
    try:
        await close_db()
        logger.info("Database connection closed")
    except Exception as e:
        logger.warning(f"Database cleanup failed: {e}")
    logger.info("Browser Use Agent shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A sophisticated browser automation agent that can understand natural language instructions",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


# Include routers
app.include_router(agent.router, prefix="/agent", tags=["agent"])
app.include_router(browser.router, prefix="/browser", tags=["browser"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
