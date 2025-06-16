#!/usr/bin/env python3
"""
Setup script for HorseAPI integration
Helps users configure their API key securely
"""

import os
import sys
from pathlib import Path

def setup_horseapi():
    print("=== STALL10N HorseAPI Setup ===\n")
    
    # Check if .env.local exists
    env_file = Path(".env.local")
    
    if env_file.exists():
        print("Found existing .env.local file")
        overwrite = input("Do you want to update it? (y/n): ").lower().strip()
        if overwrite != 'y':
            print("Setup cancelled.")
            return
    
    # Get API key from user
    print("\nPlease enter your HorseAPI access key")
    print("(Get it from: https://statpal.io after signing up for free trial)")
    api_key = input("API Key: ").strip()
    
    if not api_key:
        print("Error: API key cannot be empty")
        return
    
    # Get database URL if not already set
    db_url = os.getenv('DATABASE_URL', '')
    if not db_url:
        print("\nDatabase URL not found in environment")
        db_url = input("Enter DATABASE_URL (or press Enter to skip): ").strip()
    
    # Create or update .env.local
    env_content = []
    
    # Read existing content if file exists
    if env_file.exists():
        with open(env_file, 'r') as f:
            lines = f.readlines()
            for line in lines:
                # Skip lines we're going to update
                if not line.startswith('HORSEAPI_ACCESS_KEY=') and \
                   not line.startswith('DATABASE_URL='):
                    env_content.append(line)
    
    # Add/update our values
    env_content.append(f"\n# HorseAPI Configuration\n")
    env_content.append(f"HORSEAPI_ACCESS_KEY={api_key}\n")
    
    if db_url:
        env_content.append(f"\n# Database Configuration\n")
        env_content.append(f"DATABASE_URL={db_url}\n")
    
    # Write the file
    with open(env_file, 'w') as f:
        f.writelines(env_content)
    
    print(f"\n✅ Configuration saved to {env_file}")
    print("   This file is gitignored and won't be committed")
    
    # Test the configuration
    print("\nTesting configuration...")
    try:
        from config import Config
        valid, errors = Config.validate_config()
        
        if valid:
            print("✅ Configuration is valid!")
            print("\nYou can now run:")
            print("  python app.py           # Start the web app")
            print("  python horseapi_odds_monitor.py  # Run standalone monitor")
        else:
            print("❌ Configuration errors:")
            for error in errors:
                print(f"   - {error}")
    except Exception as e:
        print(f"Error testing configuration: {str(e)}")
    
    # Show next steps
    print("\n=== Next Steps ===")
    print("1. Make sure PostgreSQL is running")
    print("2. Run: python horseapi_db_integration.py  # Create tables")
    print("3. Enable monitoring for races via the API")
    print("4. Check the HORSEAPI_INTEGRATION_README.md for full docs")

def show_deployment_setup():
    """Show how to set up for deployment"""
    print("\n=== Deployment Setup ===")
    print("\nFor Heroku:")
    print("  heroku config:set HORSEAPI_ACCESS_KEY=your_key_here")
    print("  heroku config:set DATABASE_URL=your_database_url")
    
    print("\nFor Render:")
    print("  Add environment variables in Render dashboard:")
    print("  - HORSEAPI_ACCESS_KEY = your_key_here")
    print("  - DATABASE_URL = your_database_url")
    
    print("\nFor other platforms:")
    print("  Set HORSEAPI_ACCESS_KEY and DATABASE_URL as environment variables")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--deployment":
        show_deployment_setup()
    else:
        setup_horseapi()