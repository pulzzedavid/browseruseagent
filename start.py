#!/usr/bin/env python3
"""
Startup script for the Browser Use Agent
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.main import app
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def initialize_services():
    """Initialize all services"""
    try:
        logger.info("Initializing Browser Use Agent services...")
        
        # Note: Services are now initialized in main.py lifespan
        # This function is kept for compatibility but doesn't do anything
        logger.info("✅ Services will be initialized by main.py lifespan")
        return True
        
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        return False


def main():
    """Main startup function"""
    print("🚀 Browser Use Agent")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("app").exists():
        print("❌ Error: 'app' directory not found")
        print("Please run this script from the project root directory")
        return 1
    
    # Check if environment file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  Warning: .env file not found")
        print("Creating from template...")
        
        # Copy from example if it exists
        example_env = Path("env.example")
        if example_env.exists():
            import shutil
            shutil.copy(example_env, env_file)
            print("✅ Created .env from template")
            print("⚠️  Please edit .env with your API keys and configuration")
        else:
            print("❌ env.example not found")
            return 1
    
    # Initialize services
    try:
        success = asyncio.run(initialize_services())
        if not success:
            return 1
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        return 1
    
    # Start the FastAPI application
    try:
        import uvicorn
        
        print(f"\n🌐 Starting Browser Use Agent on {settings.host}:{settings.port}")
        print(f"📚 API Documentation: http://{settings.host}:{settings.port}/docs")
        print(f"🔍 Health Check: http://{settings.host}:{settings.port}/health")
        print("\nPress Ctrl+C to stop")
        
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level=settings.log_level.lower()
        )
        
    except KeyboardInterrupt:
        print("\n⏹️ Shutting down Browser Use Agent...")
        return 0
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
