import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration management for STALL10N"""
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # StatPal API Configuration
    STATPAL_ACCESS_KEY = os.getenv('STATPAL_ACCESS_KEY', os.getenv('HORSEAPI_ACCESS_KEY'))
    
    # Alternative: Load from multiple possible sources
    @staticmethod
    def get_statpal_key():
        """Get StatPal API key from multiple possible sources"""
        # Priority order:
        # 1. Environment variable (try both names for compatibility)
        key = os.getenv('STATPAL_ACCESS_KEY') or os.getenv('HORSEAPI_ACCESS_KEY')
        
        # 2. .env file (already loaded by python-dotenv)
        if not key:
            key = os.getenv('STATPAL_ACCESS_KEY') or os.getenv('HORSEAPI_ACCESS_KEY')
        
        # 3. Heroku/Render config vars (automatically available as env vars)
        
        # 4. Local .env.local file (for development)
        if not key and os.path.exists('.env.local'):
            load_dotenv('.env.local')
            key = os.getenv('STATPAL_ACCESS_KEY') or os.getenv('HORSEAPI_ACCESS_KEY')
        
        return key
    
    # Backwards compatibility
    @staticmethod
    def get_horseapi_key():
        """Deprecated: Use get_statpal_key() instead"""
        return Config.get_statpal_key()
    
    # App Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is not set")
        
        if not cls.get_statpal_key():
            errors.append("STATPAL_ACCESS_KEY is not set")
        
        if errors:
            return False, errors
        return True, []

# Usage example
if __name__ == "__main__":
    valid, errors = Config.validate_config()
    if not valid:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Configuration is valid")