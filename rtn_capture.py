#!/usr/bin/env python3
"""
RTN (Racetrack Television Network) Video Capture and Data Extraction
Captures live race data from RTN streams for Fair Meadows
"""

import time
import json
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyautogui
import cv2
import numpy as np
import pytesseract
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RTNCapture:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.driver = None
        self.capture_regions = {
            'video': (0, 0, 1280, 720),  # Will be set after login
            'odds_board': (1300, 100, 600, 800),  # Right side odds display
            'race_info': (100, 50, 400, 150),  # Top left race info
            'tote_board': (100, 650, 1000, 70)  # Bottom tote display
        }
        
    def setup_browser(self):
        """Initialize Chrome with options for video capture"""
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Full screen for consistent capture regions
        options.add_argument('--start-fullscreen')
        
        self.driver = webdriver.Chrome(options=options)
        logger.info("Browser initialized")
        
    def login_to_rtn(self):
        """Login to RTN website"""
        try:
            self.driver.get("https://online.rtn.tv")
            time.sleep(3)
            
            # Wait for login form
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_field = self.driver.find_element(By.NAME, "password")
            
            username_field.send_keys(self.username)
            password_field.send_keys(self.password)
            
            # Click login button
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            logger.info("Logged in to RTN")
            time.sleep(5)  # Wait for dashboard to load
            
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def navigate_to_track(self, track_name="Fair Meadows"):
        """Navigate to specific track stream"""
        try:
            # Look for track in the schedule or track list
            track_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, track_name))
            )
            track_link.click()
            
            logger.info(f"Navigated to {track_name}")
            time.sleep(3)  # Wait for video to load
            
            # Update capture regions based on actual video position
            self._update_capture_regions()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to track: {e}")
            return False
    
    def _update_capture_regions(self):
        """Update capture regions based on actual element positions"""
        try:
            # Find video player element
            video_element = self.driver.find_element(By.TAG_NAME, "video")
            location = video_element.location
            size = video_element.size
            
            # Update video region
            self.capture_regions['video'] = (
                location['x'], 
                location['y'], 
                size['width'], 
                size['height']
            )
            
            logger.info(f"Updated video region: {self.capture_regions['video']}")
            
        except Exception as e:
            logger.warning(f"Could not find video element, using defaults: {e}")
    
    def capture_screen_region(self, region_name):
        """Capture specific region of screen"""
        region = self.capture_regions.get(region_name)
        if not region:
            logger.error(f"Unknown region: {region_name}")
            return None
        
        x, y, width, height = region
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        
        # Convert to numpy array for OpenCV processing
        img_array = np.array(screenshot)
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        return img_array
    
    def extract_odds_from_image(self, image):
        """Extract odds data using OCR"""
        # Preprocess image for better OCR
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold to get black text on white background
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        # OCR the image
        text = pytesseract.image_to_string(thresh)
        
        # Parse odds data
        odds_data = self._parse_odds_text(text)
        
        return odds_data
    
    def _parse_odds_text(self, text):
        """Parse OCR text to extract odds information"""
        odds_data = []
        lines = text.strip().split('\n')
        
        for line in lines:
            # Look for patterns like "1 HORSE NAME 5/2"
            # Adjust regex based on actual RTN format
            parts = line.split()
            if len(parts) >= 3 and parts[0].isdigit():
                try:
                    program_num = int(parts[0])
                    horse_name = ' '.join(parts[1:-1])
                    odds = parts[-1]
                    
                    odds_data.append({
                        'program_number': program_num,
                        'horse_name': horse_name,
                        'odds': odds,
                        'timestamp': datetime.now().isoformat()
                    })
                except:
                    continue
        
        return odds_data
    
    def capture_race_data(self, race_number):
        """Main capture loop for a specific race"""
        logger.info(f"Starting capture for Race {race_number}")
        
        race_data = {
            'track': 'Fair Meadows',
            'race_number': race_number,
            'capture_start': datetime.now().isoformat(),
            'odds_snapshots': [],
            'race_info': None,
            'final_results': None
        }
        
        # Capture race info once
        race_info_img = self.capture_screen_region('race_info')
        if race_info_img is not None:
            race_info_text = pytesseract.image_to_string(race_info_img)
            race_data['race_info'] = race_info_text.strip()
        
        # Capture odds every 30 seconds until race starts
        odds_capture_count = 0
        while odds_capture_count < 20:  # Max 10 minutes of capture
            # Capture odds board
            odds_img = self.capture_screen_region('odds_board')
            if odds_img is not None:
                odds = self.extract_odds_from_image(odds_img)
                if odds:
                    race_data['odds_snapshots'].append({
                        'snapshot_time': datetime.now().isoformat(),
                        'odds': odds
                    })
                    logger.info(f"Captured odds snapshot {odds_capture_count + 1}")
                
                # Save image for debugging
                cv2.imwrite(f"debug_odds_{race_number}_{odds_capture_count}.png", odds_img)
            
            odds_capture_count += 1
            time.sleep(30)  # Wait 30 seconds between captures
        
        # Save race data
        filename = f"rtn_race_{race_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(race_data, f, indent=2)
        
        logger.info(f"Race data saved to {filename}")
        
        return race_data
    
    def monitor_track(self, duration_hours=3):
        """Monitor track for specified duration"""
        end_time = time.time() + (duration_hours * 3600)
        race_count = 1
        
        while time.time() < end_time:
            logger.info(f"Monitoring for race {race_count}")
            
            # Check if new race is starting (you'll need to implement race detection)
            # For now, we'll capture every 20 minutes
            self.capture_race_data(race_count)
            
            race_count += 1
            time.sleep(1200)  # Wait 20 minutes between races
    
    def cleanup(self):
        """Close browser and cleanup"""
        if self.driver:
            self.driver.quit()
        logger.info("Cleanup complete")


def main():
    # RTN credentials (you'll need to set these)
    RTN_USERNAME = "your_username"
    RTN_PASSWORD = "your_password"
    
    capture = RTNCapture(RTN_USERNAME, RTN_PASSWORD)
    
    try:
        # Setup and login
        capture.setup_browser()
        
        if not capture.login_to_rtn():
            logger.error("Failed to login to RTN")
            return
        
        # Navigate to Fair Meadows
        if not capture.navigate_to_track("Fair Meadows"):
            logger.error("Failed to navigate to Fair Meadows")
            return
        
        # Monitor for 3 hours
        capture.monitor_track(duration_hours=3)
        
    except KeyboardInterrupt:
        logger.info("Capture interrupted by user")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    
    finally:
        capture.cleanup()


if __name__ == "__main__":
    main()