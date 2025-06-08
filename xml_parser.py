"""Complete XML Parser for TrackMaster Plus horse racing data"""
import xml.etree.ElementTree as ET
import logging
from datetime import datetime, date
from typing import List, Dict, Optional, Any
import re

logger = logging.getLogger(__name__)

class RacingXMLParser:
    """Parse TrackMaster Plus XML racing data files with ALL fields"""
    
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
        """Parse race-level information with all fields"""
        race = {
            # Basic race info
            'race_number': self._get_int(racedata, 'race', 1),
            'track': self._get_text(racedata, 'track', 'Fair Meadows'),
            'track_code': self._get_text(racedata, 'track'),
            'race_date': self._parse_date(self._get_text(racedata, 'race_date')),
            'post_time': self._get_text(racedata, 'post_time'),
            
            # Distance info
            'distance': self._get_float(racedata, 'distance'),
            'dist_unit': self._get_text(racedata, 'dist_unit', 'F'),
            'dist_disp': self._get_text(racedata, 'dist_disp'),
            
            # Surface and course
            'surface': self._get_text(racedata, 'surface', 'D'),
            'course_id': self._get_text(racedata, 'course_id', 'D'),
            
            # Race type and class
            'race_type': self._determine_race_type(racedata),
            'stk_clm_md': self._get_text(racedata, 'stk_clm_md'),
            'stkorclm': self._get_text(racedata, 'stkorclm'),
            'todays_cls': self._get_int(racedata, 'todays_cls'),
            
            # Purse and claiming
            'purse': self._get_int(racedata, 'purse'),
            'claimamt': self._get_int(racedata, 'claimamt'),
            'claiming_price': self._get_int(racedata, 'claimamt'),
            
            # Race conditions
            'race_conditions': self._get_text(racedata, 'race_text'),
            'age_restr': self._get_text(racedata, 'age_restr'),
            'sex_restriction': self._get_text(racedata, 'sex_restriction'),
            
            # Additional info
            'betting_options': self._get_text(racedata, 'bet_opt'),
            'country': self._get_text(racedata, 'country', 'USA'),
            'partim': self._get_text(racedata, 'partim'),
            'raceord': self._get_int(racedata, 'raceord'),
            'breed_type': self._get_text(racedata, 'breed_type', 'TB'),
            'track_record': None  # Could be extracted from race_text if needed
        }
        
        # Clean up track name
        if race['track'] == 'FMT':
            race['track'] = 'Fair Meadows Tulsa'
            
        return race
    
    def _parse_horse_entry(self, horsedata) -> Optional[Dict]:
        """Parse individual horse entry with all fields"""
        try:
            entry = {
                # Basic info
                'program_number': self._get_int(horsedata, 'program'),
                'post_position': self._get_int(horsedata, 'pp'),
                'horse_name': self._get_text(horsedata, 'horse_name'),
                'owner_name': self._get_text(horsedata, 'owner_name'),
                
                # Physical attributes
                'sex': self._get_text(horsedata, 'sex'),
                'age': self._calculate_age(self._get_text(horsedata, 'foal_date')),
                'foal_date': self._parse_foal_date(self._get_text(horsedata, 'foal_date')),
                'color': self._get_text(horsedata, 'color'),
                'breeder': self._get_text(horsedata, 'breeder'),
                'where_bred': self._get_text(horsedata, 'wh_foaled'),
                'breed_type': self._get_text(horsedata, 'breed_type', 'TB'),
                
                # Racing attributes
                'weight': self._get_int(horsedata, 'weight'),
                'weight_shift': self._get_int(horsedata, 'wght_shift', 0),
                'medication': self._get_text(horsedata, 'med'),
                'equipment': self._get_text(horsedata, 'equip'),
                'morning_line_odds': self._get_text(horsedata, 'morn_odds'),
                'claiming_price': self._get_int(horsedata, 'claimprice'),
                
                # Performance metrics
                'power_rating': self._get_float(horsedata, 'power'),
                'power_symb': self._get_text(horsedata, 'power_symb'),
                'avg_speed': self._get_int(horsedata, 'avgspd'),
                'avg_class': self._get_int(horsedata, 'avgcls'),
                'todays_cls': self._get_int(horsedata, 'todays_cls'),
                'class_rating': self._get_int(horsedata, 'todays_cls'),
                'last_speed': self._get_int(horsedata, 'prtefigfin'),
                'best_speed': self._get_int(horsedata, 'pallfigerl'),
                
                # Speed/Style figures
                'pstyerl': self._get_float(horsedata, 'pstyerl'),
                'pstymid': self._get_float(horsedata, 'pstymid'),
                'pstyfin': self._get_float(horsedata, 'pstyfin'),
                'pstynum': self._get_int(horsedata, 'pstynum'),
                'pstyoff': self._get_int(horsedata, 'pstyoff'),
                
                'psprstyerl': self._get_float(horsedata, 'psprstyerl'),
                'psprstymid': self._get_float(horsedata, 'psprstymid'),
                'psprstyfin': self._get_float(horsedata, 'psprstyfin'),
                'psprstynum': self._get_int(horsedata, 'psprstynum'),
                'psprstyoff': self._get_int(horsedata, 'psprstyoff'),
                
                'prtestyerl': self._get_float(horsedata, 'prtestyerl'),
                'prtestymid': self._get_float(horsedata, 'prtestymid'),
                'prtestyfin': self._get_float(horsedata, 'prtestyfin'),
                'prtestynum': self._get_int(horsedata, 'prtestynum'),
                'prtestyoff': self._get_int(horsedata, 'prtestyoff'),
                
                'pallstyerl': self._get_float(horsedata, 'pallstyerl'),
                'pallstymid': self._get_float(horsedata, 'pallstymid'),
                'pallstyfin': self._get_float(horsedata, 'pallstyfin'),
                'pallstynum': self._get_int(horsedata, 'pallstynum'),
                'pallstyoff': self._get_int(horsedata, 'pallstyoff'),
                
                # Figure ratings
                'pfigerl': self._get_float(horsedata, 'pfigerl'),
                'pfigmid': self._get_float(horsedata, 'pfigmid'),
                'pfigfin': self._get_float(horsedata, 'pfigfin'),
                'pfignum': self._get_int(horsedata, 'pfignum'),
                'pfigoff': self._get_int(horsedata, 'pfigoff'),
                
                'psprfigerl': self._get_float(horsedata, 'psprfigerl'),
                'psprfigmid': self._get_float(horsedata, 'psprfigmid'),
                'psprfigfin': self._get_float(horsedata, 'psprfigfin'),
                'psprfignum': self._get_int(horsedata, 'psprfignum'),
                'psprfigoff': self._get_int(horsedata, 'psprfigoff'),
                
                'prtefigerl': self._get_float(horsedata, 'prtefigerl'),
                'prtefigmid': self._get_float(horsedata, 'prtefigmid'),
                'prtefigfin': self._get_float(horsedata, 'prtefigfin'),
                'prtefignum': self._get_int(horsedata, 'prtefignum'),
                'prtefigoff': self._get_int(horsedata, 'prtefigoff'),
                
                'pallfigerl': self._get_float(horsedata, 'pallfigerl'),
                'pallfigmid': self._get_float(horsedata, 'pallfigmid'),
                'pallfigfin': self._get_float(horsedata, 'pallfigfin'),
                'pallfignum': self._get_int(horsedata, 'pallfignum'),
                'pallfigoff': self._get_int(horsedata, 'pallfigoff'),
                
                # Additional metrics
                'tmmark': self._get_text(horsedata, 'tmmark'),
                'av_pur_val': self._get_float(horsedata, 'av_pur_val'),
                'ae_flag': self._get_text(horsedata, 'ae_flag'),
                'horse_comment': self._get_text(horsedata, 'horse_comm'),
                'lst_salena': self._get_text(horsedata, 'lst_salena'),
                'lst_salepr': self._get_float(horsedata, 'lst_salepr'),
                'lst_saleda': self._get_int(horsedata, 'lst_saleda'),
                'apprweight': self._get_int(horsedata, 'apprweight'),
                'axciskey': self._get_text(horsedata, 'axciskey'),
                
                # Standard deviation fields
                'avg_spd_sd': self._get_text(horsedata, 'avg_spd_sd'),
                'ave_cl_sd': self._get_text(horsedata, 'ave_cl_sd'),
                'hi_spd_sd': self._get_text(horsedata, 'hi_spd_sd'),
            }
            
            # Parse jockey information
            jockey_elem = horsedata.find('jockey')
            if jockey_elem is not None:
                entry['jockey'] = self._get_text(jockey_elem, 'jock_disp')
                entry['jockey_data'] = {
                    'jockey_name': self._get_text(jockey_elem, 'jock_disp'),
                    'jock_key': self._get_text(jockey_elem, 'jock_key'),
                    'j_type': self._get_text(jockey_elem, 'j_type'),
                    'stat_breed': self._get_text(jockey_elem, 'stat_breed'),
                    'stats': self._parse_stats_data(jockey_elem.find('stats_data'))
                }
                entry['jockey_stats'] = entry['jockey_data']['stats']
            
            # Parse trainer information
            trainer_elem = horsedata.find('trainer')
            if trainer_elem is not None:
                entry['trainer'] = self._get_text(trainer_elem, 'tran_disp')
                entry['trainer_data'] = {
                    'trainer_name': self._get_text(trainer_elem, 'tran_disp'),
                    'train_key': self._get_text(trainer_elem, 'train_key'),
                    't_type': self._get_text(trainer_elem, 't_type'),
                    'stat_breed': self._get_text(trainer_elem, 'stat_breed'),
                    'stats': self._parse_stats_data(trainer_elem.find('stats_data'))
                }
                entry['trainer_stats'] = entry['trainer_data']['stats']
            
            # Parse horse statistics
            stats_elem = horsedata.find('stats_data')
            if stats_elem is not None:
                entry['horse_stats'] = self._parse_stats_data(stats_elem)
            
            # Parse sire information
            sire_elem = horsedata.find('sire')
            if sire_elem is not None:
                entry['sire_data'] = {
                    'sire_name': self._get_text(sire_elem, 'sirename'),
                    'stud_fee': self._get_float(sire_elem, 'stud_fee'),
                    'stat_breed': self._get_text(sire_elem, 'stat_breed'),
                    'tmmark': self._get_text(sire_elem, 'tmmark'),
                    'stats': self._parse_stats_data(sire_elem.find('stats_data'))
                }
            
            # Parse dam information
            dam_elem = horsedata.find('dam')
            if dam_elem is not None:
                entry['dam_data'] = {
                    'dam_name': self._get_text(dam_elem, 'damname'),
                    'damsire_name': self._get_text(dam_elem, 'damsire'),
                    'stat_breed': self._get_text(dam_elem, 'stat_breed'),
                    'tmmark': self._get_text(dam_elem, 'tmmark'),
                    'stats': self._parse_stats_data(dam_elem.find('stats_data'))
                }
            
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
            
            # Parse past performance data
            pp_data = []
            for pp in horsedata.findall('ppdata'):
                pp_data.append(self._parse_pp_data(pp))
            if pp_data:
                entry['pp_data'] = pp_data
            
            # Calculate derived stats for analysis
            entry['win_pct'] = self._calculate_win_percentage(entry.get('horse_stats', {}))
            entry['jockey_win_pct'] = self._calculate_win_percentage(entry.get('jockey_stats', {}))
            entry['trainer_win_pct'] = self._calculate_win_percentage(entry.get('trainer_stats', {}))
            
            return entry
            
        except Exception as e:
            logger.error(f"Error parsing horse entry: {e}")
            return None
    
    def _parse_stats_data(self, stats_data) -> Dict:
        """Parse statistics data"""
        stats = {}
        if stats_data is not None:
            for stat in stats_data.findall('stat'):
                stat_type = stat.get('type', '')
                stats[stat_type] = {
                    'starts': self._get_int(stat, 'starts', 0),
                    'wins': self._get_int(stat, 'wins', 0),
                    'places': self._get_int(stat, 'places', 0),
                    'shows': self._get_int(stat, 'shows', 0),
                    'earnings': self._get_float(stat, 'earnings', 0),
                    'paid': self._get_float(stat, 'paid', 0),
                    'roi': self._get_float(stat, 'roi')
                }
        return stats
    
    def _parse_pp_data(self, pp) -> Dict:
        """Parse past performance data"""
        return {
            'racedate': self._get_text(pp, 'racedate'),
            'trackcode': self._get_text(pp, 'trackcode'),
            'trackname': self._get_text(pp, 'trackname'),
            'racenumber': self._get_int(pp, 'racenumber'),
            'racebreed': self._get_text(pp, 'racebreed'),
            'country': self._get_text(pp, 'country'),
            'racetype': self._get_text(pp, 'racetype'),
            'raceclass': self._get_text(pp, 'raceclass'),
            'claimprice': self._get_int(pp, 'claimprice'),
            'purse': self._get_int(pp, 'purse'),
            'classratin': self._get_int(pp, 'classratin'),
            'trackcondi': self._get_text(pp, 'trackcondi'),
            'distance': self._get_int(pp, 'distance'),
            'disttype': self._get_text(pp, 'disttype'),
            'aboutdist': self._get_text(pp, 'aboutdist'),
            'courseid': self._get_text(pp, 'courseid'),
            'surface': self._get_text(pp, 'surface'),
            'pulledofft': self._get_int(pp, 'pulledofft'),
            'winddirect': self._get_text(pp, 'winddirect'),
            'windspeed': self._get_int(pp, 'windspeed'),
            'trackvaria': self._get_int(pp, 'trackvaria'),
            'sealedtrac': self._get_text(pp, 'sealedtrac'),
            'racegrade': self._get_int(pp, 'racegrade'),
            'agerestric': self._get_text(pp, 'agerestric'),
            'sexrestric': self._get_text(pp, 'sexrestric'),
            'statebredr': self._get_text(pp, 'statebredr'),
            'abbrevcond': self._get_text(pp, 'abbrevcond'),
            'postpositi': self._get_int(pp, 'postpositi'),
            'favorite': self._get_int(pp, 'favorite'),
            'weightcarr': self._get_int(pp, 'weightcarr'),
            'jockfirst': self._get_text(pp, 'jockfirst'),
            'jockmiddle': self._get_text(pp, 'jockmiddle'),
            'jocklast': self._get_text(pp, 'jocklast'),
            'jocksuffix': self._get_text(pp, 'jocksuffix'),
            'jockdisp': self._get_text(pp, 'jockdisp'),
            'equipment': self._get_text(pp, 'equipment'),
            'medication': self._get_text(pp, 'medication'),
            'fieldsize': self._get_int(pp, 'fieldsize'),
            'posttimeod': self._get_text(pp, 'posttimeod'),
            'shortcomme': self._get_text(pp, 'shortcomme'),
            'longcommen': self._get_text(pp, 'longcommen'),
            'gatebreak': self._get_int(pp, 'gatebreak'),
            'position1': self._get_int(pp, 'position1'),
            'lenback1': self._get_float(pp, 'lenback1'),
            'horsetime1': self._get_float(pp, 'horsetime1'),
            'leadertime': self._get_float(pp, 'leadertime'),
            'pacefigure': self._get_int(pp, 'pacefigure'),
            'position2': self._get_int(pp, 'position2'),
            'lenback2': self._get_float(pp, 'lenback2'),
            'horsetime2': self._get_float(pp, 'horsetime2'),
            'leadertim2': self._get_float(pp, 'leadertim2'),
            'pacefigur2': self._get_int(pp, 'pacefigur2'),
            'positionst': self._get_int(pp, 'positionst'),
            'lenbackstr': self._get_float(pp, 'lenbackstr'),
            'horsetimes': self._get_float(pp, 'horsetimes'),
            'leadertim3': self._get_float(pp, 'leadertim3'),
            'dqindicato': self._get_text(pp, 'dqindicato'),
            'positionfi': self._get_int(pp, 'positionfi'),
            'lenbackfin': self._get_float(pp, 'lenbackfin'),
            'horsetimef': self._get_float(pp, 'horsetimef'),
            'leadertim4': self._get_float(pp, 'leadertim4'),
            'speedfigur': self._get_int(pp, 'speedfigur'),
            'turffigure': self._get_float(pp, 'turffigure'),
            'winnersspe': self._get_int(pp, 'winnersspe'),
            'foreignspe': self._get_int(pp, 'foreignspe'),
            'horseclaim': self._get_int(pp, 'horseclaim'),
            'biasstyle': self._get_text(pp, 'biasstyle'),
            'biaspath': self._get_text(pp, 'biaspath'),
            'complineho': self._get_text(pp, 'complineho'),
            'complinele': self._get_float(pp, 'complinele'),
            'complinewe': self._get_int(pp, 'complinewe'),
            'complinedq': self._get_text(pp, 'complinedq'),
            'complineh2': self._get_text(pp, 'complineh2'),
            'complinel2': self._get_float(pp, 'complinel2'),
            'complinew2': self._get_int(pp, 'complinew2'),
            'complined2': self._get_text(pp, 'complined2'),
            'complineh3': self._get_text(pp, 'complineh3'),
            'complinel3': self._get_float(pp, 'complinel3'),
            'complinew3': self._get_int(pp, 'complinew3'),
            'complined3': self._get_text(pp, 'complined3'),
            'linebefore': self._get_text(pp, 'linebefore'),
            'lineafter': self._get_text(pp, 'lineafter'),
            'domesticpp': self._get_int(pp, 'domesticpp'),
            'oflfinish': self._get_int(pp, 'oflfinish'),
            'runup_dist': self._get_int(pp, 'runup_dist'),
            'rail_dist': self._get_int(pp, 'rail_dist'),
            'apprweight': self._get_int(pp, 'apprweight'),
            'vd_claim': self._get_text(pp, 'vd_claim'),
            'vd_reason': self._get_text(pp, 'vd_reason'),
        }
    
    def _calculate_win_percentage(self, stats: Dict) -> Optional[float]:
        """Calculate win percentage from stats"""
        overall = stats.get('overall', stats.get('OVERALL', stats.get('LIFETIME', {})))
        if overall:
            starts = overall.get('starts', 0)
            wins = overall.get('wins', 0)
            if starts > 0:
                # Cap at 99.9 to avoid rounding issues with DECIMAL(5,2)
                win_pct = (wins / starts) * 100
                return round(min(win_pct, 99.9), 1)
        return None
    
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
    
    def _parse_foal_date(self, foal_date: str) -> Optional[str]:
        """Parse foal date from YYYYMMDD to YYYY-MM-DD format"""
        if foal_date and len(foal_date) == 8:
            try:
                year = foal_date[:4]
                month = foal_date[4:6]
                day = foal_date[6:8]
                # Validate it's a real date
                datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
                return f"{year}-{month}-{day}"
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
        if text and text != 'NA':
            try:
                return int(float(text))
            except:
                pass
        return default
    
    def _get_float(self, element, tag: str, default: float = 0.0) -> float:
        """Safely get float from XML element"""
        text = self._get_text(element, tag)
        if text and text != 'NA':
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