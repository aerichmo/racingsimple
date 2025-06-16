# STALL10N Deployment Checklist

## ✅ Completed

1. **Enhanced Database Schema**
   - Created `race_results` table for historical data
   - Created `live_odds_snapshot` table for odds tracking
   - Created `race_schedule` table for automated pulls

2. **API Integration**
   - Integrated Horse Racing USA API with quota management
   - Limited to 40 calls/day
   - 1-hour caching to preserve quota

3. **Updated Main Racing Page**
   - Added "Live Odds" column
   - Added "Status" column (shows WIN/Finished)
   - Auto-refreshes every 2 minutes
   - Shows results from completed races

4. **Automated Data Pulling**
   - Pulls data 10 minutes before post time
   - Gets previous race results + current live odds
   - Cron job ready (`cron_scheduler.py`)

## 🚀 Deploy to Render (Recommended)

### Quick Deploy with render.yaml
1. **Connect GitHub Repository**
   - Go to https://dashboard.render.com
   - New → Blueprint
   - Connect STALL10N repository
   - Render will auto-configure from `render.yaml`

2. **Set Environment Variables**
   ```
   HORSEAPI_ACCESS_KEY = your_api_key_here
   ```

3. **Initialize After Deploy**
   ```bash
   python render_init.py
   ```

See `RENDER_QUICK_DEPLOY.md` for detailed instructions.

### Manual Deploy Steps
1. **Push Code to GitHub**
   ```bash
   git add .
   git commit -m "Add live odds and race results integration"
   git push origin main
   ```

2. **Render will auto-deploy** the following new features:
   - Live odds display on main page
   - Race results tracking
   - Automated data pulling system
   - Admin interface for race scheduling

## 📋 Today's Setup (June 13, 2025)

### Option 1: Through Admin Interface

1. Go to: https://stall10n.onrender.com/admin
2. Navigate to "Race Data Management"
3. Schedule each race with accurate post times:
   - Race 1: 6:00 PM
   - Race 2: 6:30 PM
   - Race 3: 7:00 PM
   - Race 4: 7:30 PM
   - Race 5: 8:00 PM
   - Race 6: 8:30 PM
   - Race 7: 9:00 PM
   - Race 8: 9:30 PM

### Option 2: Manual Entry + Live Updates

1. Enter horses manually through admin interface
2. System will automatically:
   - Pull live odds 10 minutes before each race
   - Update results after each race completes
   - Display on main page in real-time

## 🔍 Monitoring

1. **Check API Quota**
   - View at: `/api/upcoming-pulls`
   - 40 calls/day limit
   - ~5 calls per race (be conservative)

2. **View Live Page**
   - https://stall10n.onrender.com/
   - Live odds appear in blue
   - Winners marked in green
   - Auto-refreshes every 2 minutes

3. **Database Queries** (if needed)
   ```sql
   -- Check scheduled races
   SELECT * FROM race_schedule WHERE race_date = '2025-06-13';
   
   -- View live odds
   SELECT * FROM live_odds_snapshot WHERE race_date = '2025-06-13';
   
   -- See race results
   SELECT * FROM race_results WHERE race_date = '2025-06-13';
   ```

## ⚠️ Important Notes

1. **API Race IDs**: Still need to discover how to get current race IDs from Horse Racing USA API
2. **Time Zones**: Ensure post times match your server timezone
3. **Manual Backup**: Can still enter all data manually if API issues occur
4. **Quota Management**: With 8 races, you'll use ~16-24 API calls (well within 40 limit)

## 🛠️ Troubleshooting

- **No live odds showing**: Check if race is scheduled in `race_schedule` table
- **Quota exceeded**: Use manual entry for remaining races
- **Missing results**: Ensure previous race has `finished` status

## 📞 Next Steps

1. Contact RapidAPI support for current race ID discovery
2. Set up automated cron job on server
3. Consider upgrading API plan if successful
4. Add SMS/email alerts for low quota