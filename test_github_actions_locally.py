#!/usr/bin/env python3
"""
Test GitHub Actions setup locally before pushing
"""

import os
import sys
import subprocess

def check_requirement(name, check_cmd, install_hint):
    """Check if a requirement is installed"""
    try:
        subprocess.run(check_cmd, shell=True, check=True, capture_output=True)
        print(f"✅ {name} is installed")
        return True
    except:
        print(f"❌ {name} is not installed")
        print(f"   Install with: {install_hint}")
        return False

def test_environment():
    """Test environment setup"""
    print("🔍 Checking environment variables...")
    
    required_vars = {
        'DATABASE_URL': 'PostgreSQL connection string',
        'RTN_USERNAME': 'RTN login username',
        'RTN_PASSWORD': 'RTN login password'
    }
    
    missing = []
    for var, desc in required_vars.items():
        if os.getenv(var):
            print(f"✅ {var} is set")
        else:
            print(f"❌ {var} is not set ({desc})")
            missing.append(var)
    
    return len(missing) == 0

def test_database_connection():
    """Test database connection"""
    print("\n🔍 Testing database connection...")
    
    try:
        import psycopg2
        db_url = os.getenv('DATABASE_URL')
        
        if not db_url:
            print("❌ DATABASE_URL not set")
            return False
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Test query
        cursor.execute('SELECT 1')
        result = cursor.fetchone()
        
        if result[0] == 1:
            print("✅ Database connection successful")
            
            # Check tables
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = cursor.fetchone()[0]
            print(f"📊 Found {table_count} tables in database")
            
            conn.close()
            return True
        
    except ImportError:
        print("❌ psycopg2 not installed")
        print("   Install with: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_github_files():
    """Check if GitHub Actions files exist"""
    print("\n🔍 Checking GitHub Actions files...")
    
    files = [
        '.github/workflows/rtn_capture.yml',
        '.github/workflows/rtn_monitor.yml',
        '.github/workflows/test_connection.yml',
        'rtn_runner_headless.py',
        'requirements_rtn.txt'
    ]
    
    all_exist = True
    for file in files:
        path = os.path.join('/Users/alecrichmond/Library/Mobile Documents/com~apple~CloudDocs/STALL10N', file)
        if os.path.exists(path):
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} not found")
            all_exist = False
    
    return all_exist

def main():
    print("🚀 Testing GitHub Actions Setup for RTN Capture\n")
    
    # Check system requirements
    print("🔍 Checking system requirements...")
    reqs_ok = True
    reqs_ok &= check_requirement("Git", "git --version", "Install from git-scm.com")
    reqs_ok &= check_requirement("Python 3", "python3 --version", "Install from python.org")
    
    if not reqs_ok:
        print("\n❌ Please install missing requirements first")
        return
    
    # Test environment
    env_ok = test_environment()
    
    # Test database
    db_ok = test_database_connection()
    
    # Check files
    files_ok = test_github_files()
    
    # Summary
    print("\n" + "="*50)
    print("📋 SUMMARY")
    print("="*50)
    
    if env_ok and db_ok and files_ok:
        print("✅ All tests passed! Ready to push to GitHub.")
        print("\nNext steps:")
        print("1. git add .")
        print("2. git commit -m 'Add RTN automated capture'")
        print("3. git push origin main")
        print("4. Go to GitHub → Actions → Run 'Test Database Connection'")
        print("5. If test passes, run 'RTN Fair Meadows Capture'")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        
        if not env_ok:
            print("\n🔧 To set environment variables:")
            print("export DATABASE_URL='postgresql://...'")
            print("export RTN_USERNAME='your_username'")
            print("export RTN_PASSWORD='your_password'")

if __name__ == "__main__":
    main()