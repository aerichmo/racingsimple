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
from selenium.webdriver.support.select import Select
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
            
            # Find login button - multiple strategies
            login_button = None
            button_selectors = [
                ("CSS", "input[value='Log in']"),
                ("CSS", "input[type='submit']"),
                ("CSS", "button[type='submit']"),
                ("CSS", ".login-button"),
                ("CSS", "#login-button"),
                ("XPATH", "//input[@value='Log in']"),
                ("XPATH", "//button[contains(text(), 'Log')]"),
                ("XPATH", "//input[@type='image']"),  # Some sites use image buttons
                ("XPATH", "//td[@bgcolor='#62B54F']//input"),  # Green button cell
                ("XPATH", "//input[@style[contains(.,'#62B54F')]]"),  # Green styled input
                ("XPATH", "//input[@onclick]"),  # Any input with onclick
            ]
            
            for selector_type, selector in button_selectors:
                try:
                    if selector_type == "CSS":
                        login_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    else:
                        login_button = self.driver.find_element(By.XPATH, selector)
                    logger.info(f"Found login button using {selector_type}: {selector}")
                    break
                except:
                    continue
            
            if not login_button:
                # Last resort - find any input/button near password field
                try:
                    login_button = password_field.find_element(By.XPATH, "../..//input[@type='submit' or @type='button' or @type='image']")
                    logger.info("Found login button near password field")
                except:
                    self.take_screenshot("debug_no_login_button.png")
                    raise Exception("Could not find login button")
            
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
            
            # First, let's see what's on the page after login
            self.take_screenshot("debug_after_login_page.png")
            
            # Wait for page to fully load after login
            time.sleep(3)
            
            # Look for Live Simulcasts button on the home page (NOT Available Simulcasts from menu)
            live_simulcast_found = False
            
            # First, let's log all visible text to understand the page
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                logger.info("Page contains 'Live Simulcasts': " + str("Live Simulcasts" in page_text))
                logger.info("Page contains 'Today': " + str("Today" in page_text))
                logger.info("Page contains 'Historical': " + str("Historical" in page_text))
            except:
                pass
            
            # Method 1: Try to find Live Simulcasts that's NOT in the navigation menu
            try:
                # Find all elements containing "Live Simulcasts"
                all_live_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Live Simulcasts')]")
                logger.info(f"Found {len(all_live_elements)} elements with 'Live Simulcasts' text")
                
                for elem in all_live_elements:
                    try:
                        # Get element position to skip navigation menu (usually at top)
                        location = elem.location
                        if location['y'] > 150:  # Below typical navigation height
                            logger.info(f"Found Live Simulcasts at position y={location['y']}, clicking...")
                            elem.click()
                            time.sleep(5)
                            self.take_screenshot("debug_live_simulcasts_page.png")
                            live_simulcast_found = True
                            logger.info(f"Current URL after clicking: {self.driver.current_url}")
                            break
                    except:
                        continue
                        
            except Exception as e:
                logger.error(f"Method 1 failed: {e}")
            
            # If we couldn't find the button, try CSS selectors for green buttons
            if not live_simulcast_found:
                try:
                    # Look for buttons with green styling that contain "Live"
                    green_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.btn-success, a.btn-success, button.green, a.green")
                    for button in green_buttons:
                        if "Live Simulcasts" in button.text:
                            logger.info("Found Live Simulcasts green button, clicking...")
                            button.click()
                            time.sleep(5)  # Give more time for page to load
                            self.take_screenshot("debug_live_simulcasts_page.png")
                            live_simulcast_found = True
                            
                            # Log the new page URL
                            logger.info(f"Current URL after clicking Live Simulcasts: {self.driver.current_url}")
                            break
                except:
                    pass
                    
            # Try additional selectors for the green buttons
            if not live_simulcast_found:
                try:
                    # Look for any element with green background containing "Live Simulcasts"
                    all_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Live Simulcasts')]")
                    logger.info(f"Found {len(all_elements)} elements containing 'Live Simulcasts'")
                    
                    for elem in all_elements:
                        try:
                            # Check if it's visible and not in navigation
                            if elem.is_displayed():
                                elem_text = elem.text.strip()
                                parent = elem.find_element(By.XPATH, "..")
                                parent_text = parent.text.strip()
                                logger.info(f"Checking element: '{elem_text}', parent: '{parent_text[:50]}...'")
                                
                                # Skip navigation elements
                                if "Available Simulcasts" in parent_text or "Home" in parent_text:
                                    continue
                                    
                                # Try to click it
                                logger.info("Clicking Live Simulcasts element...")
                                elem.click()
                                time.sleep(5)
                                self.take_screenshot("debug_live_simulcasts_page.png")
                                live_simulcast_found = True
                                logger.info(f"Current URL after clicking: {self.driver.current_url}")
                                break
                        except Exception as e:
                            logger.debug(f"Could not click element: {e}")
                            continue
                except Exception as e:
                    logger.error(f"Error finding Live Simulcasts elements: {e}")
            
            # Log final status
            if not live_simulcast_found:
                logger.error("Could not find Live Simulcasts button on home page")
                self.take_screenshot("debug_could_not_find_live_button.png")
                
                # As absolute last resort, try Available Simulcasts from menu
                logger.warning("LAST RESORT: Trying Available Simulcasts from navigation menu...")
                try:
                    link = self.driver.find_element(By.PARTIAL_LINK_TEXT, "Available Simulcasts")
                    logger.info("Found Available Simulcasts link in navigation, clicking...")
                    link.click()
                    time.sleep(3)
                    self.take_screenshot("debug_available_simulcasts_page.png")
                except:
                    logger.error("Could not find any simulcast links at all")
            
            # Check if we're already on Fair Meadows page
            current_page_text = self.driver.find_element(By.TAG_NAME, "body").text
            if "Today's races at Fair Meadows" in current_page_text or "Fair Meadows at Tulsa" in current_page_text:
                logger.info("Already on Fair Meadows stream page!")
                return True
                
            # Now look for Fair Meadows link if not already there
            track_names = [
                "Fair Meadows At Tulsa",  # Exact text as shown
                "Fair Meadows at Tulsa",  # Case variation
                "FAIR MEADOWS AT TULSA",  # All caps
                "Fair Meadows",
                "FAIR MEADOWS", 
                "FMT",
                "Tulsa"
            ]
            
            for track_name in track_names:
                try:
                    # Try as link
                    track_link = self.driver.find_element(By.PARTIAL_LINK_TEXT, track_name)
                    logger.info(f"Found {track_name} link")
                    track_link.click()
                    return True
                except:
                    pass
                    
                try:
                    # Try as text in a table/list
                    track_element = self.driver.find_element(By.XPATH, f"//*[contains(text(), '{track_name}')]")
                    logger.info(f"Found {track_name} text element")
                    
                    # Check if it's clickable
                    try:
                        # Try clicking the element directly
                        track_element.click()
                        time.sleep(1)
                        # Check if page changed
                        if track_name.lower() in self.driver.current_url.lower():
                            return True
                    except:
                        # Try clicking parent elements
                        for i in range(3):  # Try up to 3 parent levels
                            try:
                                parent = track_element.find_element(By.XPATH, "..")
                                parent.click()
                                time.sleep(1)
                                if track_name.lower() in self.driver.current_url.lower():
                                    return True
                                track_element = parent
                            except:
                                break
                    
                    # Try JavaScript click
                    try:
                        self.driver.execute_script("arguments[0].click();", track_element)
                        time.sleep(1)
                        if track_name.lower() in self.driver.current_url.lower():
                            return True
                    except:
                        pass
                        
                except:
                    pass
            
            # Try to find any dropdown
            try:
                dropdowns = self.driver.find_elements(By.TAG_NAME, "select")
                logger.info(f"Found {len(dropdowns)} dropdown(s)")
                for dropdown in dropdowns:
                    try:
                        select = Select(dropdown)
                        # Get all options
                        for option in select.options:
                            if "fair" in option.text.lower() or "meadows" in option.text.lower():
                                logger.info(f"Found option: {option.text}")
                                select.select_by_visible_text(option.text)
                                return True
                    except:
                        continue
            except:
                pass
            
            # Take screenshot to see available tracks
            self.take_screenshot("debug_available_tracks.png")
            
            # Log what tracks we can see
            try:
                visible_text = self.driver.find_element(By.TAG_NAME, "body").text
                if "fair meadows" in visible_text.lower():
                    logger.info("Fair Meadows text found on page but couldn't click it")
                    
                    # Find all elements containing Fair Meadows
                    fair_meadows_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Fair Meadows') or contains(text(), 'FAIR MEADOWS')]")
                    logger.info(f"Found {len(fair_meadows_elements)} Fair Meadows elements")
                    
                    # Try to understand why it's not clickable
                    for idx, elem in enumerate(fair_meadows_elements):
                        try:
                            tag_name = elem.tag_name
                            is_displayed = elem.is_displayed()
                            is_enabled = elem.is_enabled()
                            parent_tag = elem.find_element(By.XPATH, "..").tag_name
                            logger.info(f"Element {idx}: tag={tag_name}, displayed={is_displayed}, enabled={is_enabled}, parent={parent_tag}")
                            
                            # Check if it's in a disabled/inactive state
                            classes = elem.get_attribute("class") or ""
                            if any(word in classes.lower() for word in ["disabled", "inactive", "unavailable"]):
                                logger.info(f"Fair Meadows appears to be disabled/inactive: {classes}")
                        except:
                            pass
                else:
                    logger.info("Fair Meadows not found in page text")
                    
                # Log all visible tracks
                lines = visible_text.split('\n')
                track_lines = [line for line in lines if any(word in line.lower() for word in ['park', 'downs', 'meadows', 'track', 'racing', 'tulsa', 'fair'])]
                if track_lines:
                    logger.info(f"All visible tracks/racing text: {track_lines[:20]}")  # Show more tracks
                    
                # Also log any text containing "Fair" or "Tulsa"
                fair_tulsa_lines = [line for line in lines if 'fair' in line.lower() or 'tulsa' in line.lower()]
                if fair_tulsa_lines:
                    logger.info(f"Lines containing Fair/Tulsa: {fair_tulsa_lines}")
                    
                    # Check for Fair Meadows season
                    from datetime import date
                    today = date.today()
                    fair_meadows_start = date(2025, 6, 4)
                    fair_meadows_end = date(2025, 7, 19)
                    
                    if today < fair_meadows_start:
                        logger.info(f"Fair Meadows season hasn't started yet (starts {fair_meadows_start})")
                    elif today > fair_meadows_end:
                        logger.info(f"Fair Meadows season has ended (ended {fair_meadows_end})")
                    else:
                        logger.info("Fair Meadows should be in season but not showing on RTN")
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error finding Fair Meadows: {e}")
            return False
    
    def capture_odds_data(self):
        """Capture odds data from the Fair Meadows page"""
        try:
            # Take full page screenshot
            self.take_screenshot("debug_race_page.png")
            
            # First check if we're on a race page
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            if "Race" not in page_text:
                logger.warning("Not on a race page")
                return []
                
            # Extract race number from page
            race_number = None
            for line in page_text.split('\n'):
                if line.startswith("Race ") and any(c.isdigit() for c in line):
                    try:
                        race_number = int(''.join(c for c in line.split()[1] if c.isdigit()))
                        logger.info(f"Capturing data for Race {race_number}")
                        break
                    except:
                        pass
                        
            # Look for horse entries - Fair Meadows uses a specific format
            horses_data = []
            
            # Method 1: Look for numbered rows (program numbers)
            for i in range(1, 15):  # Up to 14 horses
                try:
                    # Find elements containing the program number
                    program_elements = self.driver.find_elements(By.XPATH, f"//td[text()='{i}'] | //div[text()='{i}']")
                    
                    for elem in program_elements:
                        try:
                            # Get the parent row/container
                            parent = elem.find_element(By.XPATH, "..")
                            row_text = parent.text
                            
                            # Parse horse info from row
                            parts = row_text.split()
                            if len(parts) >= 3:  # Program, Horse Name, ML Odds
                                horse_info = {
                                    'program_number': i,
                                    'horse_name': ' '.join(parts[1:-1]),  # Everything between program and odds
                                    'odds': parts[-1],
                                    'confidence': 80
                                }
                                horses_data.append(horse_info)
                                logger.info(f"Found horse: {horse_info}")
                                break
                        except:
                            continue
                except:
                    continue
                    
            # Method 2: Look for the race entries table/list
            if not horses_data:
                try:
                    # Look for any table or list containing horse names
                    tables = self.driver.find_elements(By.TAG_NAME, "table")
                    for table in tables:
                        if "Runner" in table.text or "Horse" in table.text:
                            rows = table.find_elements(By.TAG_NAME, "tr")
                            for row in rows[1:]:  # Skip header
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if len(cells) >= 3:
                                    try:
                                        horse_info = {
                                            'program_number': int(cells[0].text.strip()),
                                            'horse_name': cells[1].text.strip(),
                                            'odds': cells[2].text.strip() if len(cells) > 2 else "SCR",
                                            'confidence': 90
                                        }
                                        horses_data.append(horse_info)
                                    except:
                                        pass
                except:
                    pass
                    
            if horses_data:
                logger.info(f"Captured {len(horses_data)} horses for race {race_number}")
            else:
                logger.warning("No horse data found on page")
                
            return horses_data
                
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
            logger.info("Exiting - only capturing Fair Meadows data")
            # Take final screenshot showing available tracks
            capture.take_screenshot("debug_no_fair_meadows_final.png")
            return
        
        # Start capture session only if Fair Meadows found
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