import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration management for STALL10N"""
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # HorseAPI Configuration
    HORSEAPI_ACCESS_KEY = os.getenv('HORSEAPI_ACCESS_KEY')
    
    # Alternative: Load from multiple possible sources
    @staticmethod
    def get_horseapi_key():
        """Get HorseAPI key from multiple possible sources"""
        # Priority order:
        # 1. Environment variable
        key = os.getenv('HORSEAPI_ACCESS_KEY')
        
        # 2. .env file (already loaded by python-dotenv)
        if not key:
            key = os.getenv('HORSEAPI_ACCESS_KEY')
        
        # 3. Heroku/Render config vars (automatically available as env vars)
        
        # 4. Local .env.local file (for development)
        if not key and os.path.exists('.env.local'):
            load_dotenv('.env.local')
            key = os.getenv('HORSEAPI_ACCESS_KEY')
        
        return key
    
    # Existing API (RapidAPI) Configuration
    RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY', '1c6ef83f5bmshae8b269821b23dep1c77dbjsn9ed69f94d9fa')
    
    # App Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is not set")
        
        if not cls.get_horseapi_key():
            errors.append("HORSEAPI_ACCESS_KEY is not set")
        
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