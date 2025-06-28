#!/usr/bin/env python3
"""
Simple RTN login test - run this locally to verify credentials
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_rtn_login():
    # Get credentials from environment
    username = os.getenv('RTN_USERNAME')
    password = os.getenv('RTN_PASSWORD')
    
    if not username or not password:
        print("Please set RTN_USERNAME and RTN_PASSWORD environment variables")
        return
    
    print(f"Testing login with email: {username}")
    
    # Setup Chrome
    driver = webdriver.Chrome()
    
    try:
        # Navigate to RTN
        print("1. Navigating to RTN...")
        driver.get("https://online.rtn.tv")
        time.sleep(3)
        
        # Find and fill email field
        print("2. Finding email field...")
        email_field = driver.find_element(By.XPATH, "//td[contains(text(), 'Email:')]/following-sibling::td/input")
        email_field.clear()
        email_field.send_keys(username)
        print("   ✓ Email entered")
        
        # Find and fill password field
        print("3. Finding password field...")
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_field.clear()
        password_field.send_keys(password)
        print("   ✓ Password entered")
        
        # Wait for user to see the form is filled
        print("\n4. Form filled. Press Enter to submit login...")
        input()
        
        # Click login button
        print("5. Clicking login button...")
        login_button = driver.find_element(By.CSS_SELECTOR, "input[value='Log in']")
        login_button.click()
        
        # Wait and check result
        print("6. Waiting for login result...")
        time.sleep(5)
        
        current_url = driver.current_url
        print(f"\nCurrent URL: {current_url}")
        
        if "login" not in current_url.lower():
            print("✅ Login appears successful!")
        else:
            print("❌ Still on login page - login may have failed")
            print("\nPossible issues:")
            print("- Check your email/password are correct")
            print("- Verify your RTN subscription is active")
            print("- Look for any error messages on the page")
        
        print("\nPress Enter to close browser...")
        input()
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    test_rtn_login()