#!/usr/bin/env python3
"""
Manual deploy trigger for Render
"""
import os
import requests
import sys

def deploy_to_render():
    """Trigger a manual deploy on Render"""
    
    # Check for deploy hook URL
    deploy_hook = os.getenv('RENDER_DEPLOY_HOOK')
    
    if not deploy_hook:
        print("❌ RENDER_DEPLOY_HOOK environment variable not set")
        print("\nTo get your deploy hook:")
        print("1. Go to https://dashboard.render.com")
        print("2. Click on your 'stall10n' service")
        print("3. Go to Settings > Deploy Hook")
        print("4. Copy the URL and run:")
        print("   export RENDER_DEPLOY_HOOK='<your-hook-url>'")
        print("5. Then run this script again")
        return False
    
    print("🚀 Triggering Render deployment...")
    
    try:
        response = requests.get(deploy_hook)
        
        if response.status_code == 200:
            print("✅ Deploy triggered successfully!")
            print("Check https://dashboard.render.com for deployment status")
            return True
        else:
            print(f"❌ Deploy failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error triggering deploy: {e}")
        return False

if __name__ == "__main__":
    success = deploy_to_render()
    sys.exit(0 if success else 1)