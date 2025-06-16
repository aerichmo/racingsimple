#!/usr/bin/env python3
"""
Render initialization script
Run this after deployment to set up database tables
"""

import os
import sys
import logging
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_render_deployment():
    """Initialize Render deployment"""
    print("=== STALL10N Render Initialization ===\n")
    
    # Check configuration
    print("1. Checking configuration...")
    valid, errors = Config.validate_config()
    
    if not valid:
        print("❌ Configuration errors:")
        for error in errors:
            print(f"   - {error}")
        print("\nPlease set environment variables in Render dashboard:")
        print("  - DATABASE_URL (automatically set from database)")
        print("  - HORSEAPI_ACCESS_KEY (your API key)")
        return False
    
    print("✅ Configuration valid")
    print(f"   - Database: {Config.DATABASE_URL[:30]}...")
    print(f"   - HorseAPI: {'Configured' if Config.get_horseapi_key() else 'Not configured'}")
    
    # Initialize database tables
    print("\n2. Initializing database tables...")
    try:
        from horseapi_db_integration import HorseAPIOddsDB
        db = HorseAPIOddsDB()
        db.create_odds_tables()
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        return False
    
    # Test API connection
    print("\n3. Testing HorseAPI connection...")
    try:
        from horseapi_service import HorseAPIService
        api = HorseAPIService()
        # Just initialize, don't make a call to preserve quota
        print("✅ HorseAPI service initialized")
    except Exception as e:
        print(f"❌ HorseAPI initialization failed: {str(e)}")
        return False
    
    # Check if monitoring should be started
    print("\n4. Checking monitoring configuration...")
    if os.getenv('ENABLE_ODDS_MONITOR', 'false').lower() == 'true':
        print("✅ Odds monitoring is enabled (running as background worker)")
    else:
        print("ℹ️  Odds monitoring not enabled (set ENABLE_ODDS_MONITOR=true to enable)")
    
    print("\n=== Initialization Complete ===")
    print("\nNext steps:")
    print("1. Test the health endpoint: https://your-app.onrender.com/health")
    print("2. Enable monitoring for specific races via API")
    print("3. Check logs in Render dashboard")
    
    return True

if __name__ == "__main__":
    success = init_render_deployment()
    sys.exit(0 if success else 1)