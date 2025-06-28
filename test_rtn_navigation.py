#!/usr/bin/env python3
"""
Test RTN Navigation - Simple test to verify Live Simulcasts navigation
"""

import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_navigation():
    """Test navigation to Live Simulcasts"""
    username = os.getenv('RTN_USERNAME', 'alecrichmo@gmail.com')
    password = os.getenv('RTN_PASSWORD', 'Whim$icalC0mfort')
    
    # Setup Chrome options
    options = Options()
    options.add_argument('--window-size=1920,1080')
    
    # Try to use Chrome without specifying driver path (let Selenium find it)
    try:
        driver = webdriver.Chrome(options=options)
    except:
        logger.error("Could not start Chrome. Please install chromedriver.")
        return
    
    try:
        # Navigate to RTN
        logger.info("Navigating to RTN...")
        driver.get("https://online.rtn.tv")
        time.sleep(3)
        
        # Login
        logger.info("Logging in...")
        email_field = driver.find_element(By.XPATH, "//td[contains(text(), 'Email:')]/following-sibling::td/input")
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        
        email_field.send_keys(username)
        password_field.send_keys(password)
        
        login_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
        login_button.click()
        
        time.sleep(5)
        logger.info("Login complete")
        
        # Take screenshot of home page
        driver.save_screenshot("test_home_page.png")
        
        # Find all elements containing "Live Simulcasts"
        elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Live Simulcasts')]")
        logger.info(f"Found {len(elements)} elements containing 'Live Simulcasts'")
        
        # Try to identify which one is the button
        for i, elem in enumerate(elements):
            try:
                tag = elem.tag_name
                text = elem.text
                parent_tag = elem.find_element(By.XPATH, "..").tag_name
                is_displayed = elem.is_displayed()
                
                # Get position info
                location = elem.location
                size = elem.size
                
                logger.info(f"Element {i}: tag={tag}, text='{text}', parent={parent_tag}, displayed={is_displayed}")
                logger.info(f"  Position: x={location['x']}, y={location['y']}, width={size['width']}, height={size['height']}")
                
                # Check if it's clickable (not in navigation)
                if is_displayed and location['y'] > 200:  # Below navigation bar
                    logger.info(f"  This looks like the main button, trying to click...")
                    elem.click()
                    time.sleep(5)
                    driver.save_screenshot("test_after_click.png")
                    logger.info(f"  New URL: {driver.current_url}")
                    
                    # Check if we're on the live simulcasts page
                    if "live" in driver.current_url.lower() or driver.current_url != "https://online.rtn.tv/":
                        logger.info("Successfully navigated to Live Simulcasts!")
                        
                        # Now look for Fair Meadows
                        page_text = driver.find_element(By.TAG_NAME, "body").text
                        if "Fair Meadows" in page_text:
                            logger.info("Fair Meadows found on Live Simulcasts page!")
                        else:
                            logger.info("Fair Meadows not found on Live Simulcasts page")
                            
                        # Log what tracks are visible
                        lines = page_text.split('\n')
                        track_lines = [line for line in lines if any(word in line.lower() for word in ['meadows', 'park', 'downs', 'tulsa'])]
                        logger.info(f"Visible tracks: {track_lines[:10]}")
                        
                        break
                    else:
                        logger.info("  Click didn't navigate away from home page")
                        
            except Exception as e:
                logger.error(f"Error with element {i}: {e}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        driver.save_screenshot("test_error.png")
    
    finally:
        input("Press Enter to close browser...")
        driver.quit()

if __name__ == "__main__":
    test_navigation()