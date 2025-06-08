"""XML Parser for TrackMaster Plus horse racing data"""
import xml.etree.ElementTree as ET
import logging
from datetime import datetime, date
from typing import List, Dict, Optional
import re

logger = logging.getLogger(__name__)

class RacingXMLParser:
    """Parse TrackMaster Plus XML racing data files"""
    
    def parse_xml_file(self, xml_path: str) -> List[Dict]:
        """Parse XML file and return list of races with entries"""
        races = []
        
        try:
            # Parse the XML file
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Find all racedata elements (one per race)
            for racedata in root.findall('racedata'):
                # Parse race information
                race_info = self._parse_race_info(racedata)
                
                # Parse all horse entries for this race
                entries = []
                for horsedata in racedata.findall('horsedata'):
                    entry = self._parse_horse_entry(horsedata)
                    if entry:
                        entries.append(entry)
                
                if entries:
                    race_info['entries'] = entries
                    races.append(race_info)
                else:
                    logger.warning(f"Race {race_info['race_number']} has no entries")
                
        except Exception as e:
            logger.error(f"Error parsing XML: {e}", exc_info=True)
            
        return races
    
    def _parse_race_info(self, racedata) -> Dict:
        """Parse race-level information"""
        race = {
            'race_number': self._get_int(racedata, 'race', 1),
            'track': self._get_text(racedata, 'track', 'Fair Meadows'),
            'race_date': self._parse_date(self._get_text(racedata, 'race_date')),
            'post_time': self._get_text(racedata, 'post_time'),
            'distance': self._format_distance(racedata),
            'surface': self._get_text(racedata, 'surface', 'D'),
            'race_type': self._determine_race_type(racedata),
            'purse': self._get_int(racedata, 'purse'),
            'claiming_price': self._get_int(racedata, 'claimamt'),
            'race_conditions': self._get_text(racedata, 'race_text'),
            'betting_options': self._get_text(racedata, 'bet_opt')
        }
        
        # Clean up track name
        if race['track'] == 'FMT':
            race['track'] = 'Fair Meadows Tulsa'
            
        return race
    
    def _parse_horse_entry(self, horsedata) -> Optional[Dict]:
        """Parse individual horse entry"""
        try:
            entry = {
                'program_number': self._get_int(horsedata, 'program'),
                'post_position': self._get_int(horsedata, 'pp'),
                'horse_name': self._get_text(horsedata, 'horse_name'),
                'morning_line_odds': self._get_text(horsedata, 'morn_odds'),
                'weight': self._get_int(horsedata, 'weight'),
                'medication': self._get_text(horsedata, 'med'),
                'equipment': self._get_text(horsedata, 'equip'),
                'power_rating': self._get_float(horsedata, 'power'),
                'avg_speed': self._get_int(horsedata, 'avgspd'),
                'avg_class': self._get_int(horsedata, 'avgcls'),
                'sex': self._get_text(horsedata, 'sex'),
                'age': self._calculate_age(self._get_text(horsedata, 'foal_date')),
                'color': self._get_text(horsedata, 'color'),
                'breeder': self._get_text(horsedata, 'breeder'),
                'owner': self._get_text(horsedata, 'owner_name'),
                'claiming_price': self._get_int(horsedata, 'claimprice'),
                'comments': self._get_text(horsedata, 'horse_comm')
            }
            
            # Parse jockey information
            jockey_elem = horsedata.find('jockey')
            if jockey_elem is not None:
                entry['jockey'] = self._get_text(jockey_elem, 'jock_disp')
                entry['jockey_stats'] = self._parse_stats(jockey_elem)
            
            # Parse trainer information
            trainer_elem = horsedata.find('trainer')
            if trainer_elem is not None:
                entry['trainer'] = self._get_text(trainer_elem, 'tran_disp')
                entry['trainer_stats'] = self._parse_stats(trainer_elem)
            
            # Parse horse statistics
            stats_elem = horsedata.find('stats_data')
            if stats_elem is not None:
                entry['horse_stats'] = self._parse_stats_data(stats_elem)
            
            # Parse workout data
            workouts = []
            for workout in horsedata.findall('workoutdata'):
                workouts.append({
                    'days_back': self._get_int(workout, 'days_back'),
                    'description': self._get_text(workout, 'worktext'),
                    'ranking': self._get_int(workout, 'ranking'),
                    'rank_group': self._get_int(workout, 'rank_group')
                })
            if workouts:
                entry['workouts'] = workouts
            
            # Calculate derived stats for analysis
            entry['win_pct'] = self._calculate_win_percentage(entry.get('horse_stats', {}))
            entry['jockey_win_pct'] = self._calculate_win_percentage(entry.get('jockey_stats', {}))
            entry['trainer_win_pct'] = self._calculate_win_percentage(entry.get('trainer_stats', {}))
            
            # Speed figures from XML
            entry['last_speed'] = self._get_int(horsedata, 'prtefigfin')
            entry['best_speed'] = self._get_int(horsedata, 'pallfigerl')
            entry['class_rating'] = self._get_int(horsedata, 'todays_cls')
            
            return entry
            
        except Exception as e:
            logger.error(f"Error parsing horse entry: {e}")
            return None
    
    def _parse_stats(self, element) -> Dict:
        """Parse stats from jockey or trainer element"""
        stats = {}
        stats_data = element.find('stats_data')
        if stats_data is not None:
            # Get overall stats
            for stat in stats_data.findall('stat'):
                stat_type = stat.get('type', '')
                if stat_type in ['OVERALL', 'AT_TRK', 'CURR_YEAR']:
                    stats[stat_type.lower()] = {
                        'starts': self._get_int(stat, 'starts', 0),
                        'wins': self._get_int(stat, 'wins', 0),
                        'places': self._get_int(stat, 'places', 0),
                        'shows': self._get_int(stat, 'shows', 0),
                        'earnings': self._get_float(stat, 'earnings', 0),
                        'roi': self._get_float(stat, 'roi', 0)
                    }
        return stats
    
    def _parse_stats_data(self, stats_data) -> Dict:
        """Parse horse statistics data"""
        stats = {}
        for stat in stats_data.findall('stat'):
            stat_type = stat.get('type', '')
            stats[stat_type] = {
                'starts': self._get_int(stat, 'starts', 0),
                'wins': self._get_int(stat, 'wins', 0),
                'places': self._get_int(stat, 'places', 0),
                'shows': self._get_int(stat, 'shows', 0),
                'earnings': self._get_float(stat, 'earnings', 0),
                'roi': self._get_float(stat, 'roi', 0)
            }
        return stats
    
    def _calculate_win_percentage(self, stats: Dict) -> Optional[float]:
        """Calculate win percentage from stats"""
        overall = stats.get('overall', stats.get('OVERALL', {}))
        if overall:
            starts = overall.get('starts', 0)
            wins = overall.get('wins', 0)
            if starts > 0:
                return round((wins / starts) * 100, 1)
        return None
    
    def _format_distance(self, racedata) -> str:
        """Format race distance"""
        distance = self._get_float(racedata, 'distance')
        unit = self._get_text(racedata, 'dist_unit', 'F')
        
        if distance and unit:
            if unit == 'F':
                # Convert furlongs to display format
                if distance == 400:
                    return "4 Furlongs"
                elif distance == 600:
                    return "6 Furlongs"
                elif distance == 870:
                    return "7 Furlongs"
                else:
                    return f"{distance/100:.1f} Furlongs"
            elif unit == 'Y':
                return f"{int(distance)} Yards"
            elif unit == 'M':
                return f"{distance} Miles"
        
        return self._get_text(racedata, 'dist_disp', '')
    
    def _determine_race_type(self, racedata) -> str:
        """Determine race type from various fields"""
        stk_clm_md = self._get_text(racedata, 'stk_clm_md', '')
        stkorclm = self._get_text(racedata, 'stkorclm', '')
        race_text = self._get_text(racedata, 'race_text', '').upper()
        
        if stk_clm_md == 'STK' or stkorclm == 'S':
            return 'STAKES'
        elif stk_clm_md == 'CLM' or stkorclm == 'CL':
            return 'CLAIMING'
        elif stk_clm_md == 'ALW':
            return 'ALLOWANCE'
        elif 'MAIDEN' in race_text:
            return 'MAIDEN'
        elif 'CLAIMING' in race_text:
            return 'CLAIMING'
        elif 'ALLOWANCE' in race_text:
            return 'ALLOWANCE'
        elif 'STAKES' in race_text or 'HANDICAP' in race_text:
            return 'STAKES'
        
        return 'ALLOWANCE'  # Default
    
    def _parse_date(self, date_str: str) -> str:
        """Parse date from YYYYMMDD format to ISO format"""
        if date_str and len(date_str) == 8:
            try:
                year = date_str[:4]
                month = date_str[4:6]
                day = date_str[6:8]
                return f"{year}-{month}-{day}"
            except:
                pass
        return datetime.now().date().isoformat()
    
    def _calculate_age(self, foal_date: str) -> Optional[int]:
        """Calculate horse age from foaling date"""
        if foal_date and len(foal_date) == 8:
            try:
                birth_year = int(foal_date[:4])
                current_year = datetime.now().year
                return current_year - birth_year
            except:
                pass
        return None
    
    def _get_text(self, element, tag: str, default: str = '') -> str:
        """Safely get text from XML element"""
        child = element.find(tag)
        if child is not None and child.text:
            # Handle CDATA sections
            text = child.text.strip()
            # Remove CDATA markers if present
            if text.startswith('<![CDATA[') and text.endswith(']]>'):
                text = text[9:-3]
            return text
        return default
    
    def _get_int(self, element, tag: str, default: int = 0) -> int:
        """Safely get integer from XML element"""
        text = self._get_text(element, tag)
        if text:
            try:
                return int(float(text))
            except:
                pass
        return default
    
    def _get_float(self, element, tag: str, default: float = 0.0) -> float:
        """Safely get float from XML element"""
        text = self._get_text(element, tag)
        if text:
            try:
                return float(text)
            except:
                pass
        return default


# Backwards compatibility wrapper
class EquibasePDFParser:
    """Wrapper to maintain compatibility with existing code that expects PDF parser"""
    
    def __init__(self):
        self.parser = RacingXMLParser()
    
    def parse_pdf_file(self, file_path: str) -> List[Dict]:
        """Parse file - will work with XML files"""
        if file_path.lower().endswith('.xml'):
            return self.parser.parse_xml_file(file_path)
        else:
            # For actual PDFs, return empty list or implement PDF parsing
            logger.warning(f"File {file_path} is not an XML file")
            return []