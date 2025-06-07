import os
import time
import random
from datetime import datetime
import psycopg2
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import undetected_chromedriver as uc
import cloudscraper
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class AdvancedEquibaseScraper:
    """Advanced scraper with multiple strategies to bypass protection"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.base_url = "https://www.equibase.com/static/entry/"
        
    def strategy_1_cloudscraper(self, date: datetime):
        """Use cloudscraper to bypass Cloudflare/Incapsula"""
        logger.info("Trying Strategy 1: CloudScraper")
        
        try:
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                }
            )
            
            url = self.generate_url(date)
            response = scraper.get(url)
            
            if response.status_code == 200 and 'Incapsula' not in response.text:
                logger.info("CloudScraper succeeded!")
                return response.text
            else:
                logger.warning(f"CloudScraper failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"CloudScraper error: {e}")
            return None
    
    def strategy_2_selenium_undetected(self, date: datetime):
        """Use undetected Chrome driver"""
        logger.info("Trying Strategy 2: Undetected Chrome")
        
        try:
            options = uc.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Randomize viewport
            width = random.randint(1200, 1920)
            height = random.randint(800, 1080)
            options.add_argument(f'--window-size={width},{height}')
            
            driver = uc.Chrome(options=options, version_main=120)
            
            # Add human-like behavior
            url = self.generate_url(date)
            driver.get("https://www.equibase.com")
            time.sleep(random.uniform(2, 4))
            
            # Navigate to entries page
            driver.get(url)
            time.sleep(random.uniform(3, 5))
            
            # Random scrolling
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
            time.sleep(random.uniform(1, 2))
            
            # Get page source
            html = driver.page_source
            driver.quit()
            
            if 'Incapsula' not in html:
                logger.info("Undetected Chrome succeeded!")
                return html
            else:
                logger.warning("Still blocked by Incapsula")
                return None
                
        except Exception as e:
            logger.error(f"Selenium error: {e}")
            if 'driver' in locals():
                driver.quit()
            return None
    
    def strategy_3_api_endpoints(self, date: datetime):
        """Try alternative API endpoints"""
        logger.info("Trying Strategy 3: API Endpoints")
        
        try:
            # Try different URL patterns
            date_formats = [
                date.strftime("%m%d%y"),  # 060725
                date.strftime("%m%d%Y"),  # 06072025
                date.strftime("%Y%m%d"),  # 20250607
            ]
            
            endpoints = [
                f"https://www.equibase.com/premium/eqbPDFChartPlus.cfm?RACE=A&BorP=P&TID=FMT&CTRY=USA&DT={df}&DAY=D&STYLE=EQB"
                for df in date_formats
            ]
            
            session = cloudscraper.create_scraper()
            
            for endpoint in endpoints:
                logger.info(f"Trying endpoint: {endpoint}")
                response = session.get(endpoint, timeout=10)
                
                if response.status_code == 200 and len(response.content) > 1000:
                    logger.info("Found working endpoint!")
                    return response.text
            
            return None
            
        except Exception as e:
            logger.error(f"API endpoint error: {e}")
            return None
    
    def strategy_4_mobile_site(self, date: datetime):
        """Try mobile version of the site"""
        logger.info("Trying Strategy 4: Mobile Site")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            # Try mobile URL patterns
            mobile_urls = [
                f"https://m.equibase.com/entries?date={date.strftime('%Y-%m-%d')}",
                f"https://www.equibase.com/mobile/entries/FMT{date.strftime('%m%d%y')}USA-EQB.html",
            ]
            
            scraper = cloudscraper.create_scraper()
            
            for url in mobile_urls:
                response = scraper.get(url, headers=headers)
                if response.status_code == 200 and 'Incapsula' not in response.text:
                    logger.info("Mobile site access succeeded!")
                    return response.text
            
            return None
            
        except Exception as e:
            logger.error(f"Mobile site error: {e}")
            return None
    
    def parse_any_format(self, html: str, date: datetime) -> list:
        """Parse HTML in any format we get"""
        soup = BeautifulSoup(html, 'html.parser')
        races = []
        
        # Try multiple parsing patterns
        patterns = [
            # Pattern 1: Table-based
            lambda: self._parse_tables(soup, date),
            # Pattern 2: Div-based
            lambda: self._parse_divs(soup, date),
            # Pattern 3: PDF text extraction
            lambda: self._parse_text(soup.get_text(), date),
        ]
        
        for pattern in patterns:
            try:
                result = pattern()
                if result:
                    races.extend(result)
            except Exception as e:
                logger.warning(f"Parse pattern failed: {e}")
                continue
        
        return races
    
    def _parse_tables(self, soup, date):
        """Parse table-based layout"""
        races = []
        tables = soup.find_all('table')
        
        for table in tables:
            if 'race' in str(table).lower():
                race = {'date': date.date(), 'horses': []}
                rows = table.find_all('tr')
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 4:
                        # Assume: Program, Horse, Jockey, Trainer
                        horse = {
                            'program_number': cells[0].get_text().strip(),
                            'horse_name': cells[1].get_text().strip(),
                            'jockey': cells[2].get_text().strip() if len(cells) > 2 else '',
                            'trainer': cells[3].get_text().strip() if len(cells) > 3 else '',
                        }
                        if horse['horse_name'] and not horse['horse_name'].lower() in ['horse', 'name', 'entries']:
                            race['horses'].append(horse)
                
                if race['horses']:
                    races.append(race)
        
        return races
    
    def _parse_divs(self, soup, date):
        """Parse div-based layout"""
        races = []
        # Implementation depends on actual HTML structure
        return races
    
    def _parse_text(self, text, date):
        """Parse raw text"""
        races = []
        # Implementation for text parsing
        return races
    
    def generate_url(self, date: datetime) -> str:
        """Generate Equibase URL for given date"""
        date_str = date.strftime("%m%d%y")
        return f"{self.base_url}FMT{date_str}USA-EQB.html"
    
    def fetch_with_all_strategies(self, date: datetime):
        """Try all strategies until one works"""
        strategies = [
            self.strategy_1_cloudscraper,
            self.strategy_2_selenium_undetected,
            self.strategy_3_api_endpoints,
            self.strategy_4_mobile_site,
        ]
        
        for i, strategy in enumerate(strategies, 1):
            logger.info(f"Attempting strategy {i} of {len(strategies)}")
            try:
                html = strategy(date)
                if html and 'Incapsula' not in html and len(html) > 500:
                    logger.info(f"Strategy {i} succeeded!")
                    
                    # Parse the HTML
                    races = self.parse_any_format(html, date)
                    if races:
                        return races
                    else:
                        logger.warning(f"Strategy {i} got HTML but no races parsed")
                        
            except Exception as e:
                logger.error(f"Strategy {i} failed: {e}")
                continue
            
            # Add delay between attempts
            time.sleep(random.uniform(2, 5))
        
        logger.error("All strategies failed")
        return None


def run_advanced_scraper(db_url: str):
    """Run the advanced scraper"""
    scraper = AdvancedEquibaseScraper(db_url)
    races = scraper.fetch_with_all_strategies(datetime.now())
    
    if races:
        logger.info(f"Successfully scraped {len(races)} races")
        # Save to database
        from scraper import EquibaseScraper
        eq_scraper = EquibaseScraper(db_url)
        eq_scraper.save_to_database(races)
        return True, races
    else:
        return False, []