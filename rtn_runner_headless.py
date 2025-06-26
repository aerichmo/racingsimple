#!/usr/bin/env python3
"""
RTN Runner Headless - Runs RTN capture in headless mode for GitHub Actions
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import psycopg2
from datetime import datetime, timedelta

# Import only what we need to avoid pyautogui dependency
from rtn_odds_parser import RTNOddsParser
from config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RTNDatabaseManager:
    """Database management for headless RTN capture"""
    
    def __init__(self):
        self.db_conn = None
        self.setup_database()
        
    def setup_database(self):
        """Connect to PostgreSQL database"""
        try:
            db_url = Config.DATABASE_URL or os.getenv('DATABASE_URL')
            self.db_conn = psycopg2.connect(db_url)
            logger.info("Connected to database")
            self._create_tables()
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def _create_tables(self):
        """Create RTN tables if they don't exist"""
        cursor = self.db_conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rtn_capture_sessions (
                id SERIAL PRIMARY KEY,
                track_name VARCHAR(100),
                session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_end TIMESTAMP,
                status VARCHAR(50) DEFAULT 'active'
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rtn_odds_snapshots (
                id SERIAL PRIMARY KEY,
                session_id INTEGER REFERENCES rtn_capture_sessions(id),
                race_date DATE,
                race_number INTEGER,
                program_number INTEGER,
                horse_name VARCHAR(100),
                odds VARCHAR(20),
                confidence INTEGER,
                snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(race_date, race_number, program_number, snapshot_time)
            )
        """)
        
        self.db_conn.commit()
        logger.info("Database tables ready")
    
    def start_capture_session(self, track_name):
        """Start a new capture session"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO rtn_capture_sessions (track_name, session_start)
            VALUES (%s, %s)
            RETURNING id
        """, (track_name, datetime.now()))
        
        session_id = cursor.fetchone()[0]
        self.db_conn.commit()
        logger.info(f"Started capture session {session_id}")
        return session_id
    
    def save_odds_snapshot(self, session_id, race_date, race_number, odds_data):
        """Save odds snapshot to database"""
        cursor = self.db_conn.cursor()
        
        for horse in odds_data:
            try:
                cursor.execute("""
                    INSERT INTO rtn_odds_snapshots 
                    (session_id, race_date, race_number, program_number, 
                     horse_name, odds, confidence, snapshot_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (race_date, race_number, program_number, snapshot_time) 
                    DO UPDATE SET odds = EXCLUDED.odds, confidence = EXCLUDED.confidence
                """, (
                    session_id,
                    race_date,
                    race_number,
                    horse['program_number'],
                    horse['horse_name'],
                    horse['odds'],
                    horse.get('confidence', 90),
                    datetime.now()
                ))
            except Exception as e:
                logger.error(f"Error saving odds: {e}")
        
        self.db_conn.commit()
        logger.info(f"Saved {len(odds_data)} odds entries")
    
    def end_capture_session(self, session_id):
        """End capture session"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            UPDATE rtn_capture_sessions 
            SET session_end = %s, status = 'completed'
            WHERE id = %s
        """, (datetime.now(), session_id))
        self.db_conn.commit()
    
    def close(self):
        """Close database connection"""
        if self.db_conn:
            self.db_conn.close()


class RTNCaptureHeadless:
    """Headless version of RTN capture for GitHub Actions"""
    
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.driver = None
        self.parser = RTNOddsParser()
        
    def setup_headless_browser(self):
        """Setup Chrome in headless mode with virtual display"""
        options = Options()
        
        # Headless mode settings
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        # Set window size for consistent capture
        options.add_argument('--window-size=1920,1080')
        
        # Disable automation flags
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Additional options for stability
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        
        # Use system chromedriver
        service = Service('/usr/bin/chromedriver')
        
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info("Headless browser initialized")
        
    def take_screenshot(self, filename):
        """Take screenshot for debugging"""
        self.driver.save_screenshot(filename)
        logger.info(f"Screenshot saved: {filename}")
        
    def capture_element_screenshot(self, element, filename):
        """Capture screenshot of specific element"""
        element.screenshot(filename)
        logger.info(f"Element screenshot saved: {filename}")
        
    def login_to_rtn(self):
        """Login to RTN with better error handling"""
        try:
            logger.info("Navigating to RTN...")
            self.driver.get("https://online.rtn.tv")
            
            # Take initial screenshot
            self.take_screenshot("debug_rtn_homepage.png")
            
            # Wait for page to load
            time.sleep(3)
            
            # Try multiple selectors for username field
            logger.info("Looking for login form...")
            username_field = None
            password_field = None
            
            # Look for email field by visible label
            try:
                # Find the email input field next to "Email:" label
                email_label = self.driver.find_element(By.XPATH, "//td[contains(text(), 'Email:')]")
                username_field = email_label.find_element(By.XPATH, "following-sibling::td/input")
                logger.info("Found email field using label")
            except:
                # Fallback: try direct input search
                try:
                    username_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='text']")
                    logger.info("Found email field using input type")
                except:
                    username_field = None
            
            if not username_field:
                # Take screenshot to see current page
                self.take_screenshot("debug_no_login_form.png")
                raise Exception("Could not find username field")
            
            # Find password field
            password_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            
            # Enter credentials
            username_field.clear()
            username_field.send_keys(self.username)
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Find and click login button - it's an input with value "Log in"
            try:
                login_button = self.driver.find_element(By.CSS_SELECTOR, "input[value='Log in']")
            except:
                # Try alternate selector
                login_button = self.driver.find_element(By.XPATH, "//input[@type='submit' or @type='button']")
            
            # Take screenshot before clicking
            self.take_screenshot("debug_before_login_click.png")
            
            # Try different click methods
            try:
                login_button.click()
            except:
                # If regular click fails, try JavaScript click
                logger.info("Regular click failed, trying JavaScript click")
                self.driver.execute_script("arguments[0].click();", login_button)
            
            logger.info("Login button clicked, waiting for response...")
            
            # Wait a moment for any error messages
            time.sleep(2)
            
            # Check for error messages
            try:
                error_msg = self.driver.find_element(By.CSS_SELECTOR, ".error, .alert, .message")
                logger.error(f"Login error message: {error_msg.text}")
                self.take_screenshot("debug_login_error_msg.png")
            except:
                logger.info("No error message found")
            
            # Wait for login to complete
            time.sleep(3)
            
            # Take screenshot after login attempt
            self.take_screenshot("debug_after_login_attempt.png")
            
            # Check if we're still on login page
            current_url = self.driver.current_url
            logger.info(f"Current URL after login: {current_url}")
            
            # Verify login success by checking multiple indicators
            login_indicators = [
                lambda: self.driver.find_element(By.PARTIAL_LINK_TEXT, "Logout"),
                lambda: self.driver.find_element(By.PARTIAL_LINK_TEXT, "Sign Out"),
                lambda: self.driver.find_element(By.PARTIAL_LINK_TEXT, "My Account"),
                lambda: "login" not in self.driver.current_url.lower()
            ]
            
            for indicator in login_indicators:
                try:
                    result = indicator()
                    if result:
                        logger.info("Login successful!")
                        self.take_screenshot("debug_rtn_logged_in.png")
                        return True
                except:
                    continue
            
            logger.error("Login failed - still on login page")
            return False
                    
        except Exception as e:
            logger.error(f"Login failed: {e}")
            self.take_screenshot("debug_login_error.png")
            return False
    
    def find_fair_meadows_stream(self):
        """Find and navigate to Fair Meadows stream"""
        try:
            logger.info("Looking for Fair Meadows stream...")
            
            # Try multiple selectors
            selectors = [
                "Fair Meadows",
                "FAIR MEADOWS",
                "FMT",
                "Tulsa"
            ]
            
            for selector in selectors:
                try:
                    track_link = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, selector))
                    )
                    track_link.click()
                    logger.info(f"Found and clicked {selector} link")
                    return True
                except:
                    continue
            
            # If not found in links, check schedule/dropdown
            logger.info("Checking track dropdown...")
            try:
                # Look for track selector dropdown
                track_dropdown = self.driver.find_element(By.CSS_SELECTOR, "select[name='track']")
                # Select Fair Meadows option
                from selenium.webdriver.support.select import Select
                select = Select(track_dropdown)
                select.select_by_visible_text("Fair Meadows")
                logger.info("Selected Fair Meadows from dropdown")
                return True
            except:
                logger.warning("Could not find track dropdown")
            
            self.take_screenshot("debug_no_fair_meadows.png")
            return False
            
        except Exception as e:
            logger.error(f"Error finding Fair Meadows: {e}")
            return False
    
    def capture_odds_data(self):
        """Capture odds data from the page"""
        try:
            # Take full page screenshot
            self.take_screenshot("debug_race_page.png")
            
            # Look for odds table or grid
            odds_elements = self.driver.find_elements(By.CSS_SELECTOR, "table.odds, div.odds-grid, .race-odds")
            
            if odds_elements:
                logger.info(f"Found {len(odds_elements)} odds elements")
                for i, element in enumerate(odds_elements):
                    self.capture_element_screenshot(element, f"debug_odds_{i}.png")
                    
                    # Get text content
                    text_content = element.text
                    logger.info(f"Odds text: {text_content[:200]}...")
                    
                    return self._parse_odds_text(text_content)
            else:
                logger.warning("No odds elements found")
                return []
                
        except Exception as e:
            logger.error(f"Error capturing odds: {e}")
            return []
    
    def _parse_odds_text(self, text):
        """Parse odds from text content"""
        odds_data = []
        lines = text.strip().split('\n')
        
        for line in lines:
            # Simple parsing - adjust based on actual format
            parts = line.split()
            if len(parts) >= 3 and parts[0].isdigit():
                odds_data.append({
                    'program_number': int(parts[0]),
                    'horse_name': ' '.join(parts[1:-1]),
                    'odds': parts[-1]
                })
        
        return odds_data
    
    def cleanup(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")


def main():
    parser = argparse.ArgumentParser(description='Run RTN capture in headless mode')
    parser.add_argument('--duration', type=int, default=3, help='Duration in hours')
    args = parser.parse_args()
    
    # Get credentials
    username = os.getenv('RTN_USERNAME')
    password = os.getenv('RTN_PASSWORD')
    
    if not username or not password:
        logger.error("RTN credentials not found in environment variables")
        sys.exit(1)
    
    # Initialize components
    capture = RTNCaptureHeadless(username, password)
    db_manager = RTNDatabaseManager()
    
    try:
        # Setup browser
        capture.setup_headless_browser()
        
        # Login
        if not capture.login_to_rtn():
            raise Exception("Login failed")
        
        # Find Fair Meadows
        if not capture.find_fair_meadows_stream():
            logger.warning("Fair Meadows not found - may not be racing today")
            # Still continue to show we ran successfully
        
        # Start capture session
        session_id = db_manager.start_capture_session("Fair Meadows")
        
        # Capture loop
        end_time = time.time() + (args.duration * 3600)
        race_number = 1
        
        while time.time() < end_time:
            logger.info(f"Checking for Race {race_number} data...")
            
            # Capture odds
            odds_data = capture.capture_odds_data()
            if odds_data:
                db_manager.save_odds_snapshot(
                    session_id, 
                    datetime.now().date(), 
                    race_number, 
                    odds_data
                )
            
            # Wait between captures
            time.sleep(300)  # 5 minutes
            race_number += 1
            
            # Max 10 races per session
            if race_number > 10:
                break
        
        # End session
        db_manager.end_capture_session(session_id)
        logger.info("Capture session completed successfully")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        capture.take_screenshot("debug_fatal_error.png")
        sys.exit(1)
        
    finally:
        capture.cleanup()
        db_manager.close()


if __name__ == "__main__":
    main()