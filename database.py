"""Database connection and operations for XML data"""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import os
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_url):
        self.db_url = db_url
        
    @contextmanager
    def get_cursor(self, dict_cursor=True):
        """Get database cursor with automatic cleanup"""
        conn = psycopg2.connect(self.db_url)
        try:
            cursor_factory = RealDictCursor if dict_cursor else None
            cur = conn.cursor(cursor_factory=cursor_factory)
            yield cur
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def create_tables(self):
        """Create database tables from XML schema"""
        with open('schema.sql', 'r') as f:
            schema = f.read()
        
        with self.get_cursor(dict_cursor=False) as cur:
            cur.execute(schema)
        logger.info("XML database tables created successfully")
    
    def save_race(self, race_data):
        """Save race and return race_id"""
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT INTO races (
                    date, race_number, track_name, track_code, country, 
                    distance, dist_unit, dist_disp, surface, course_id,
                    race_type, stk_clm_md, stkorclm, purse, claimamt,
                    post_time, age_restr, sex_restriction, race_conditions,
                    betting_options, track_record, partim, raceord,
                    breed_type, todays_cls, pdf_filename
                )
                VALUES (
                    %(date)s, %(race_number)s, %(track_name)s, %(track_code)s, %(country)s,
                    %(distance)s, %(dist_unit)s, %(dist_disp)s, %(surface)s, %(course_id)s,
                    %(race_type)s, %(stk_clm_md)s, %(stkorclm)s, %(purse)s, %(claimamt)s,
                    %(post_time)s, %(age_restr)s, %(sex_restriction)s, %(race_conditions)s,
                    %(betting_options)s, %(track_record)s, %(partim)s, %(raceord)s,
                    %(breed_type)s, %(todays_cls)s, %(pdf_filename)s
                )
                ON CONFLICT (date, race_number, track_code) 
                DO UPDATE SET 
                    distance = EXCLUDED.distance,
                    race_type = EXCLUDED.race_type,
                    purse = EXCLUDED.purse,
                    post_time = EXCLUDED.post_time,
                    race_conditions = EXCLUDED.race_conditions,
                    betting_options = EXCLUDED.betting_options,
                    todays_cls = EXCLUDED.todays_cls
                RETURNING id
            """, race_data)
            return cur.fetchone()['id']
    
    def save_entry(self, entry_data):
        """Save race entry and return entry_id"""
        with self.get_cursor() as cur:
            # Convert empty strings to None for numeric fields
            for field in ['weight', 'weight_shift', 'age', 'todays_cls', 'avg_speed', 
                         'avg_class', 'last_speed', 'best_speed', 'class_rating', 
                         'claiming_price', 'apprweight', 'lst_saleda']:
                if field in entry_data and entry_data[field] == '':
                    entry_data[field] = None
            
            # Convert empty strings to None for decimal fields
            for field in ['power_rating', 'av_pur_val', 'lst_salepr', 'win_pct',
                         'jockey_win_pct', 'trainer_win_pct', 'jt_combo_pct']:
                if field in entry_data and entry_data[field] == '':
                    entry_data[field] = None
                    
            cur.execute("""
                INSERT INTO entries (
                    race_id, program_number, post_position, horse_name, owner_name,
                    sex, age, foal_date, color, breed_type, breeder, where_bred,
                    weight, weight_shift, medication, equipment, morning_line_odds,
                    claiming_price, power_rating, power_symb, avg_speed, avg_class,
                    todays_cls, last_speed, best_speed, class_rating,
                    pstyerl, pstymid, pstyfin, pstynum, pstyoff,
                    psprstyerl, psprstymid, psprstyfin, psprstynum, psprstyoff,
                    prtestyerl, prtestymid, prtestyfin, prtestynum, prtestyoff,
                    pallstyerl, pallstymid, pallstyfin, pallstynum, pallstyoff,
                    pfigerl, pfigmid, pfigfin, pfignum, pfigoff,
                    psprfigerl, psprfigmid, psprfigfin, psprfignum, psprfigoff,
                    prtefigerl, prtefigmid, prtefigfin, prtefignum, prtefigoff,
                    pallfigerl, pallfigmid, pallfigfin, pallfignum, pallfigoff,
                    tmmark, av_pur_val, ae_flag, horse_comment,
                    lst_salena, lst_salepr, lst_saleda, apprweight, axciskey,
                    avg_spd_sd, ave_cl_sd, hi_spd_sd,
                    jockey, trainer, win_pct, jockey_win_pct, trainer_win_pct, jt_combo_pct
                )
                VALUES (
                    %(race_id)s, %(program_number)s, %(post_position)s, %(horse_name)s, %(owner_name)s,
                    %(sex)s, %(age)s, %(foal_date)s, %(color)s, %(breed_type)s, %(breeder)s, %(where_bred)s,
                    %(weight)s, %(weight_shift)s, %(medication)s, %(equipment)s, %(morning_line_odds)s,
                    %(claiming_price)s, %(power_rating)s, %(power_symb)s, %(avg_speed)s, %(avg_class)s,
                    %(todays_cls)s, %(last_speed)s, %(best_speed)s, %(class_rating)s,
                    %(pstyerl)s, %(pstymid)s, %(pstyfin)s, %(pstynum)s, %(pstyoff)s,
                    %(psprstyerl)s, %(psprstymid)s, %(psprstyfin)s, %(psprstynum)s, %(psprstyoff)s,
                    %(prtestyerl)s, %(prtestymid)s, %(prtestyfin)s, %(prtestynum)s, %(prtestyoff)s,
                    %(pallstyerl)s, %(pallstymid)s, %(pallstyfin)s, %(pallstynum)s, %(pallstyoff)s,
                    %(pfigerl)s, %(pfigmid)s, %(pfigfin)s, %(pfignum)s, %(pfigoff)s,
                    %(psprfigerl)s, %(psprfigmid)s, %(psprfigfin)s, %(psprfignum)s, %(psprfigoff)s,
                    %(prtefigerl)s, %(prtefigmid)s, %(prtefigfin)s, %(prtefignum)s, %(prtefigoff)s,
                    %(pallfigerl)s, %(pallfigmid)s, %(pallfigfin)s, %(pallfignum)s, %(pallfigoff)s,
                    %(tmmark)s, %(av_pur_val)s, %(ae_flag)s, %(horse_comment)s,
                    %(lst_salena)s, %(lst_salepr)s, %(lst_saleda)s, %(apprweight)s, %(axciskey)s,
                    %(avg_spd_sd)s, %(ave_cl_sd)s, %(hi_spd_sd)s,
                    %(jockey)s, %(trainer)s, %(win_pct)s, %(jockey_win_pct)s, %(trainer_win_pct)s, %(jt_combo_pct)s
                )
                ON CONFLICT (race_id, program_number)
                DO UPDATE SET
                    horse_name = EXCLUDED.horse_name,
                    jockey = EXCLUDED.jockey,
                    trainer = EXCLUDED.trainer,
                    power_rating = EXCLUDED.power_rating,
                    morning_line_odds = EXCLUDED.morning_line_odds,
                    weight = EXCLUDED.weight,
                    horse_comment = EXCLUDED.horse_comment
                RETURNING id
            """, entry_data)
            return cur.fetchone()['id']
    
    def save_horse_stats(self, entry_id, stats_dict):
        """Save horse statistics"""
        with self.get_cursor() as cur:
            for stat_type, stats in stats_dict.items():
                if isinstance(stats, dict) and 'starts' in stats:
                    cur.execute("""
                        INSERT INTO horse_stats (
                            entry_id, stat_type, starts, wins, places, shows, 
                            earnings, paid, roi
                        )
                        VALUES (
                            %(entry_id)s, %(stat_type)s, %(starts)s, %(wins)s, 
                            %(places)s, %(shows)s, %(earnings)s, %(paid)s, %(roi)s
                        )
                        ON CONFLICT (entry_id, stat_type)
                        DO UPDATE SET
                            starts = EXCLUDED.starts,
                            wins = EXCLUDED.wins,
                            places = EXCLUDED.places,
                            shows = EXCLUDED.shows,
                            earnings = EXCLUDED.earnings,
                            paid = EXCLUDED.paid,
                            roi = EXCLUDED.roi
                    """, {
                        'entry_id': entry_id,
                        'stat_type': stat_type,
                        'starts': stats.get('starts', 0),
                        'wins': stats.get('wins', 0),
                        'places': stats.get('places', 0),
                        'shows': stats.get('shows', 0),
                        'earnings': stats.get('earnings', 0),
                        'paid': stats.get('paid'),
                        'roi': stats.get('roi')
                    })
    
    def save_jockey_info_and_stats(self, entry_id, jockey_data):
        """Save jockey information and statistics"""
        with self.get_cursor() as cur:
            # Extract jockey info
            jockey_name = jockey_data.get('jockey_name', '')
            jock_key = jockey_data.get('jock_key', '')
            j_type = jockey_data.get('j_type', '')
            stat_breed = jockey_data.get('stat_breed', '')
            
            # Save stats
            for stat_type, stats in jockey_data.get('stats', {}).items():
                if isinstance(stats, dict) and 'starts' in stats:
                    cur.execute("""
                        INSERT INTO jockey_stats (
                            entry_id, jockey_name, jock_key, j_type, stat_breed,
                            stat_type, starts, wins, places, shows, earnings, paid, roi
                        )
                        VALUES (
                            %(entry_id)s, %(jockey_name)s, %(jock_key)s, %(j_type)s, 
                            %(stat_breed)s, %(stat_type)s, %(starts)s, %(wins)s, 
                            %(places)s, %(shows)s, %(earnings)s, %(paid)s, %(roi)s
                        )
                        ON CONFLICT (entry_id, stat_type)
                        DO UPDATE SET
                            jockey_name = EXCLUDED.jockey_name,
                            jock_key = EXCLUDED.jock_key,
                            starts = EXCLUDED.starts,
                            wins = EXCLUDED.wins,
                            places = EXCLUDED.places,
                            shows = EXCLUDED.shows,
                            earnings = EXCLUDED.earnings,
                            paid = EXCLUDED.paid,
                            roi = EXCLUDED.roi
                    """, {
                        'entry_id': entry_id,
                        'jockey_name': jockey_name,
                        'jock_key': jock_key,
                        'j_type': j_type,
                        'stat_breed': stat_breed,
                        'stat_type': stat_type,
                        'starts': stats.get('starts', 0),
                        'wins': stats.get('wins', 0),
                        'places': stats.get('places', 0),
                        'shows': stats.get('shows', 0),
                        'earnings': stats.get('earnings'),
                        'paid': stats.get('paid'),
                        'roi': stats.get('roi')
                    })
    
    def save_trainer_info_and_stats(self, entry_id, trainer_data):
        """Save trainer information and statistics"""
        with self.get_cursor() as cur:
            # Extract trainer info
            trainer_name = trainer_data.get('trainer_name', '')
            train_key = trainer_data.get('train_key', '')
            t_type = trainer_data.get('t_type', '')
            stat_breed = trainer_data.get('stat_breed', '')
            
            # Save stats
            for stat_type, stats in trainer_data.get('stats', {}).items():
                if isinstance(stats, dict) and 'starts' in stats:
                    cur.execute("""
                        INSERT INTO trainer_stats (
                            entry_id, trainer_name, train_key, t_type, stat_breed,
                            stat_type, starts, wins, places, shows, earnings, paid, roi
                        )
                        VALUES (
                            %(entry_id)s, %(trainer_name)s, %(train_key)s, %(t_type)s, 
                            %(stat_breed)s, %(stat_type)s, %(starts)s, %(wins)s, 
                            %(places)s, %(shows)s, %(earnings)s, %(paid)s, %(roi)s
                        )
                        ON CONFLICT (entry_id, stat_type)
                        DO UPDATE SET
                            trainer_name = EXCLUDED.trainer_name,
                            train_key = EXCLUDED.train_key,
                            starts = EXCLUDED.starts,
                            wins = EXCLUDED.wins,
                            places = EXCLUDED.places,
                            shows = EXCLUDED.shows,
                            earnings = EXCLUDED.earnings,
                            paid = EXCLUDED.paid,
                            roi = EXCLUDED.roi
                    """, {
                        'entry_id': entry_id,
                        'trainer_name': trainer_name,
                        'train_key': train_key,
                        't_type': t_type,
                        'stat_breed': stat_breed,
                        'stat_type': stat_type,
                        'starts': stats.get('starts', 0),
                        'wins': stats.get('wins', 0),
                        'places': stats.get('places', 0),
                        'shows': stats.get('shows', 0),
                        'earnings': stats.get('earnings'),
                        'paid': stats.get('paid'),
                        'roi': stats.get('roi')
                    })
    
    def save_sire_info_and_stats(self, entry_id, sire_data):
        """Save sire information and statistics"""
        with self.get_cursor() as cur:
            # Extract sire info
            sire_name = sire_data.get('sire_name', '')
            stud_fee = sire_data.get('stud_fee', 0)
            stat_breed = sire_data.get('stat_breed', '')
            tmmark = sire_data.get('tmmark', '')
            
            # Save stats
            for stat_type, stats in sire_data.get('stats', {}).items():
                if isinstance(stats, dict) and 'starts' in stats:
                    cur.execute("""
                        INSERT INTO sire_stats (
                            entry_id, sire_name, stud_fee, stat_breed, tmmark,
                            stat_type, starts, wins, places, shows, earnings, paid, roi
                        )
                        VALUES (
                            %(entry_id)s, %(sire_name)s, %(stud_fee)s, %(stat_breed)s, 
                            %(tmmark)s, %(stat_type)s, %(starts)s, %(wins)s, 
                            %(places)s, %(shows)s, %(earnings)s, %(paid)s, %(roi)s
                        )
                        ON CONFLICT (entry_id, stat_type)
                        DO UPDATE SET
                            sire_name = EXCLUDED.sire_name,
                            stud_fee = EXCLUDED.stud_fee,
                            starts = EXCLUDED.starts,
                            wins = EXCLUDED.wins,
                            places = EXCLUDED.places,
                            shows = EXCLUDED.shows,
                            earnings = EXCLUDED.earnings,
                            paid = EXCLUDED.paid,
                            roi = EXCLUDED.roi
                    """, {
                        'entry_id': entry_id,
                        'sire_name': sire_name,
                        'stud_fee': stud_fee,
                        'stat_breed': stat_breed,
                        'tmmark': tmmark,
                        'stat_type': stat_type,
                        'starts': stats.get('starts', 0),
                        'wins': stats.get('wins', 0),
                        'places': stats.get('places', 0),
                        'shows': stats.get('shows', 0),
                        'earnings': stats.get('earnings'),
                        'paid': stats.get('paid'),
                        'roi': stats.get('roi')
                    })
    
    def save_dam_info_and_stats(self, entry_id, dam_data):
        """Save dam information and statistics"""
        with self.get_cursor() as cur:
            # Extract dam info
            dam_name = dam_data.get('dam_name', '')
            damsire_name = dam_data.get('damsire_name', '')
            stat_breed = dam_data.get('stat_breed', '')
            tmmark = dam_data.get('tmmark', '')
            
            # Save stats
            for stat_type, stats in dam_data.get('stats', {}).items():
                if isinstance(stats, dict) and 'starts' in stats:
                    cur.execute("""
                        INSERT INTO dam_stats (
                            entry_id, dam_name, damsire_name, stat_breed, tmmark,
                            stat_type, starts, wins, places, shows, earnings, paid, roi
                        )
                        VALUES (
                            %(entry_id)s, %(dam_name)s, %(damsire_name)s, %(stat_breed)s, 
                            %(tmmark)s, %(stat_type)s, %(starts)s, %(wins)s, 
                            %(places)s, %(shows)s, %(earnings)s, %(paid)s, %(roi)s
                        )
                        ON CONFLICT (entry_id, stat_type)
                        DO UPDATE SET
                            dam_name = EXCLUDED.dam_name,
                            damsire_name = EXCLUDED.damsire_name,
                            starts = EXCLUDED.starts,
                            wins = EXCLUDED.wins,
                            places = EXCLUDED.places,
                            shows = EXCLUDED.shows,
                            earnings = EXCLUDED.earnings,
                            paid = EXCLUDED.paid,
                            roi = EXCLUDED.roi
                    """, {
                        'entry_id': entry_id,
                        'dam_name': dam_name,
                        'damsire_name': damsire_name,
                        'stat_breed': stat_breed,
                        'tmmark': tmmark,
                        'stat_type': stat_type,
                        'starts': stats.get('starts', 0),
                        'wins': stats.get('wins', 0),
                        'places': stats.get('places', 0),
                        'shows': stats.get('shows', 0),
                        'earnings': stats.get('earnings'),
                        'paid': stats.get('paid'),
                        'roi': stats.get('roi')
                    })
    
    def save_workouts(self, entry_id, workouts):
        """Save workout data"""
        with self.get_cursor() as cur:
            # Delete existing workouts for this entry
            cur.execute("DELETE FROM workouts WHERE entry_id = %s", (entry_id,))
            
            # Insert new workouts
            for i, workout in enumerate(workouts):
                cur.execute("""
                    INSERT INTO workouts (
                        entry_id, workout_number, days_back, description, 
                        ranking, rank_group
                    )
                    VALUES (
                        %(entry_id)s, %(workout_number)s, %(days_back)s, 
                        %(description)s, %(ranking)s, %(rank_group)s
                    )
                """, {
                    'entry_id': entry_id,
                    'workout_number': i + 1,
                    'days_back': workout.get('days_back'),
                    'description': workout.get('description'),
                    'ranking': workout.get('ranking'),
                    'rank_group': workout.get('rank_group')
                })
    
    def save_pp_data(self, entry_id, pp_data_list):
        """Save past performance data"""
        with self.get_cursor() as cur:
            for pp in pp_data_list:
                # Convert date format
                racedate = pp.get('racedate', '')
                if racedate and len(racedate) == 8:
                    racedate = f"{racedate[:4]}-{racedate[4:6]}-{racedate[6:8]}"
                
                # Convert empty strings to None for numeric fields
                for field in ['claimprice', 'purse', 'classratin', 'distance', 'windspeed',
                             'trackvaria', 'racegrade', 'postpositi', 'favorite', 'weightcarr',
                             'fieldsize', 'gatebreak', 'position1', 'position2', 'positionst',
                             'positionfi', 'pacefigure', 'pacefigur2', 'speedfigur', 'winnersspe',
                             'foreignspe', 'horseclaim', 'domesticpp', 'oflfinish', 'runup_dist',
                             'rail_dist', 'apprweight']:
                    if field in pp and pp[field] == '':
                        pp[field] = None
                
                cur.execute("""
                    INSERT INTO pp_data (
                        entry_id, racedate, trackcode, trackname, racenumber, racebreed,
                        country, racetype, raceclass, claimprice, purse, classratin,
                        trackcondi, distance, disttype, aboutdist, courseid, surface,
                        pulledofft, winddirect, windspeed, trackvaria, sealedtrac,
                        racegrade, agerestric, sexrestric, statebredr, abbrevcond,
                        postpositi, favorite, weightcarr, jockfirst, jockmiddle,
                        jocklast, jocksuffix, jockdisp, equipment, medication,
                        fieldsize, posttimeod, shortcomme, longcommen, gatebreak,
                        position1, lenback1, horsetime1, leadertime, pacefigure,
                        position2, lenback2, horsetime2, leadertim2, pacefigur2,
                        positionst, lenbackstr, horsetimes, leadertim3, dqindicato,
                        positionfi, lenbackfin, horsetimef, leadertim4, speedfigur,
                        turffigure, winnersspe, foreignspe, horseclaim, biasstyle,
                        biaspath, complineho, complinele, complinewe, complinedq,
                        complineh2, complinel2, complinew2, complined2, complineh3,
                        complinel3, complinew3, complined3, linebefore, lineafter,
                        domesticpp, oflfinish, runup_dist, rail_dist, apprweight,
                        vd_claim, vd_reason
                    )
                    VALUES (
                        %(entry_id)s, %(racedate)s, %(trackcode)s, %(trackname)s, %(racenumber)s, %(racebreed)s,
                        %(country)s, %(racetype)s, %(raceclass)s, %(claimprice)s, %(purse)s, %(classratin)s,
                        %(trackcondi)s, %(distance)s, %(disttype)s, %(aboutdist)s, %(courseid)s, %(surface)s,
                        %(pulledofft)s, %(winddirect)s, %(windspeed)s, %(trackvaria)s, %(sealedtrac)s,
                        %(racegrade)s, %(agerestric)s, %(sexrestric)s, %(statebredr)s, %(abbrevcond)s,
                        %(postpositi)s, %(favorite)s, %(weightcarr)s, %(jockfirst)s, %(jockmiddle)s,
                        %(jocklast)s, %(jocksuffix)s, %(jockdisp)s, %(equipment)s, %(medication)s,
                        %(fieldsize)s, %(posttimeod)s, %(shortcomme)s, %(longcommen)s, %(gatebreak)s,
                        %(position1)s, %(lenback1)s, %(horsetime1)s, %(leadertime)s, %(pacefigure)s,
                        %(position2)s, %(lenback2)s, %(horsetime2)s, %(leadertim2)s, %(pacefigur2)s,
                        %(positionst)s, %(lenbackstr)s, %(horsetimes)s, %(leadertim3)s, %(dqindicato)s,
                        %(positionfi)s, %(lenbackfin)s, %(horsetimef)s, %(leadertim4)s, %(speedfigur)s,
                        %(turffigure)s, %(winnersspe)s, %(foreignspe)s, %(horseclaim)s, %(biasstyle)s,
                        %(biaspath)s, %(complineho)s, %(complinele)s, %(complinewe)s, %(complinedq)s,
                        %(complineh2)s, %(complinel2)s, %(complinew2)s, %(complined2)s, %(complineh3)s,
                        %(complinel3)s, %(complinew3)s, %(complined3)s, %(linebefore)s, %(lineafter)s,
                        %(domesticpp)s, %(oflfinish)s, %(runup_dist)s, %(rail_dist)s, %(apprweight)s,
                        %(vd_claim)s, %(vd_reason)s
                    )
                """, {
                    'entry_id': entry_id,
                    'racedate': racedate,
                    **pp
                })
    
    def save_analysis(self, analysis_data):
        """Save analysis results"""
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT INTO analysis (
                    entry_id, speed_score, class_score, jockey_score,
                    trainer_score, overall_score, recommendation, confidence
                )
                VALUES (
                    %(entry_id)s, %(speed_score)s, %(class_score)s, %(jockey_score)s,
                    %(trainer_score)s, %(overall_score)s, %(recommendation)s, %(confidence)s
                )
            """, analysis_data)
    
    def get_races_by_date(self, date):
        """Get all races for a specific date"""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT r.*, COUNT(e.id) as horse_count
                FROM races r
                LEFT JOIN entries e ON e.race_id = r.id
                WHERE r.date = %s
                GROUP BY r.id
                ORDER BY r.race_number
            """, (date,))
            return cur.fetchall()
    
    def get_race_entries(self, race_id):
        """Get all entries for a race with analysis"""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT e.*, a.overall_score, a.recommendation, a.confidence
                FROM entries e
                LEFT JOIN analysis a ON a.entry_id = e.id
                WHERE e.race_id = %s
                ORDER BY a.overall_score DESC NULLS LAST, e.program_number
            """, (race_id,))
            return cur.fetchall()
    
    def get_dates_with_data(self):
        """Get all dates that have race data"""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT DISTINCT date, 
                       COUNT(DISTINCT id) as race_count,
                       track_code,
                       track_name
                FROM races 
                GROUP BY date, track_code, track_name
                ORDER BY date DESC
                LIMIT 30
            """)
            return cur.fetchall()
    
    def clear_all_data(self):
        """Clear all data from all tables"""
        with self.get_cursor() as cur:
            # Tables will cascade delete due to foreign key constraints
            cur.execute("TRUNCATE TABLE races CASCADE")
            logger.info("All data cleared from database")