"""Scraper for Off Track Betting (OTB) race results"""
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re

logger = logging.getLogger(__name__)

class OTBResultsScraper:
    """Scrape race results from OTB website"""
    
    BASE_URL = "https://www.offtrackbetting.com/results"
    TRACK_ID = "158"  # Fair Meadows Downs
    
    def get_results_url(self, date: str) -> str:
        """Generate URL for specific date
        Args:
            date: Date in YYYY-MM-DD format
        Returns:
            URL string
        """
        # Convert date to MM/DD/YYYY format for OTB
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        date_formatted = date_obj.strftime('%m/%d/%Y')
        return f"{self.BASE_URL}/{self.TRACK_ID}/fair-meadows-downs.html?date={date_formatted}"
    
    def scrape_results(self, date: str) -> List[Dict]:
        """Scrape results for a specific date
        Args:
            date: Date in YYYY-MM-DD format
        Returns:
            List of races with results
        """
        url = self.get_results_url(date)
        logger.info(f"Scraping OTB results from: {url}")
        
        try:
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            races = self._parse_races(soup, date)
            
            logger.info(f"Successfully scraped {len(races)} races for {date}")
            return races
            
        except Exception as e:
            logger.error(f"Error scraping OTB results: {e}")
            return []
    
    def _parse_races(self, soup: BeautifulSoup, date: str) -> List[Dict]:
        """Parse races from HTML"""
        races = []
        
        # Find all race containers
        race_tables = soup.find_all('table', class_='race-results-table')
        
        for race_table in race_tables:
            try:
                race_data = self._parse_single_race(race_table, date)
                if race_data:
                    races.append(race_data)
            except Exception as e:
                logger.error(f"Error parsing race: {e}")
                continue
        
        return races
    
    def _parse_single_race(self, race_table, date: str) -> Optional[Dict]:
        """Parse a single race from table"""
        race_data = {
            'date': date,
            'track': 'Fair Meadows Downs',
            'results': []
        }
        
        # Try to find race number from various possible locations
        # Look for race header in different formats
        race_num = None
        
        # Try previous sibling elements
        prev = race_table.find_previous_sibling()
        while prev and race_num is None:
            if prev.name in ['h2', 'h3', 'h4', 'div']:
                race_num_match = re.search(r'Race\s+(\d+)', prev.text)
                if race_num_match:
                    race_num = int(race_num_match.group(1))
                    break
            prev = prev.find_previous_sibling()
        
        # If not found, try parent container
        if not race_num:
            parent = race_table.parent
            if parent:
                race_num_match = re.search(r'Race\s+(\d+)', parent.text)
                if race_num_match:
                    race_num = int(race_num_match.group(1))
        
        if race_num:
            race_data['race_number'] = race_num
        
        # Parse results table - handle different column layouts
        rows = race_table.find_all('tr')
        
        # Skip header row(s)
        data_rows = []
        for row in rows:
            # Check if it's a data row (has td elements with numbers)
            tds = row.find_all('td')
            if tds and len(tds) >= 5:  # Minimum columns needed
                first_cell = self._clean_text(tds[0].text)
                # Check if first cell is a number (finish position)
                if first_cell.isdigit():
                    data_rows.append(row)
        
        for row in data_rows:
            cols = row.find_all('td')
            
            # Basic result data - adjust indices based on actual layout
            result = {
                'finish_position': None,
                'program_number': None,
                'horse_name': None,
                'jockey': None,
                'trainer': None,
                'final_odds': None,
                'win_payoff': None,
                'place_payoff': None,
                'show_payoff': None
            }
            
            # Parse based on number of columns
            if len(cols) >= 5:
                result['finish_position'] = self._clean_text(cols[0].text)
                
                # Program number might be combined with horse name
                col_idx = 1
                pgm_text = self._clean_text(cols[col_idx].text)
                if pgm_text.isdigit():
                    result['program_number'] = pgm_text
                    col_idx += 1
                
                # Horse name
                if col_idx < len(cols):
                    result['horse_name'] = self._clean_text(cols[col_idx].text)
                    col_idx += 1
                
                # Jockey
                if col_idx < len(cols):
                    result['jockey'] = self._clean_text(cols[col_idx].text)
                    col_idx += 1
                
                # Final odds or win amount
                if col_idx < len(cols):
                    odds_text = self._clean_text(cols[col_idx].text)
                    if '$' in odds_text:
                        result['win_payoff'] = odds_text.replace('$', '')
                    else:
                        result['final_odds'] = odds_text
                    col_idx += 1
                
                # Additional payoffs
                if col_idx < len(cols) and '$' in cols[col_idx].text:
                    result['place_payoff'] = self._clean_text(cols[col_idx].text).replace('$', '')
                    col_idx += 1
                
                if col_idx < len(cols) and '$' in cols[col_idx].text:
                    result['show_payoff'] = self._clean_text(cols[col_idx].text).replace('$', '')
            
            # Only add if we have valid data
            if result['finish_position'] and result['horse_name']:
                # Convert finish position to int
                try:
                    result['finish_position'] = int(result['finish_position'])
                except:
                    pass
                
                race_data['results'].append(result)
        
        return race_data if race_data['results'] else None
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        return text.strip().replace('\n', ' ').replace('\t', ' ').strip()
    
    def _extract_distance(self, text: str) -> Optional[str]:
        """Extract distance from race info text"""
        distance_match = re.search(r'(\d+(?:\s+\d+/\d+)?\s*(?:Miles?|Furlongs?|Yards?))', text, re.I)
        return distance_match.group(1) if distance_match else None
    
    def _extract_race_type(self, text: str) -> Optional[str]:
        """Extract race type from text"""
        types = ['Maiden', 'Claiming', 'Allowance', 'Stakes', 'Handicap']
        for race_type in types:
            if race_type.lower() in text.lower():
                return race_type
        return None
    
    def _extract_purse(self, text: str) -> Optional[int]:
        """Extract purse amount from text"""
        purse_match = re.search(r'\$([0-9,]+)', text)
        if purse_match:
            return int(purse_match.group(1).replace(',', ''))
        return None


# Test function
if __name__ == "__main__":
    scraper = OTBResultsScraper()
    results = scraper.scrape_results('2025-06-07')
    print(f"Found {len(results)} races")
    for race in results:
        print(f"Race {race.get('race_number')}: {len(race['results'])} finishers")