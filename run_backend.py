#!/usr/bin/env python3
"""
Optimus Backend startup script.
Simple script to run the FastAPI application with proper configuration.
"""

import uvicorn
from src.config import get_settings


def main():
    """Start the Optimus backend server."""
    settings = get_settings()
    
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Base path for projects: {settings.projects_base_path}")
    print(f"Database: {settings.database_host}:{settings.database_port}/{settings.database_name}")
    print(f"Redis: {settings.redis_host}:{settings.redis_port}/{settings.redis_db}")
    print("=" * 60)
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()