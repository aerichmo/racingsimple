# GitHub Actions Setup for Automated RTN Capture

## Overview
This setup provides fully automated, hands-off capture of Fair Meadows race data from RTN using GitHub Actions.

## Features
- **Automatic scheduling** - Runs Thursday-Sunday during racing season
- **Headless browser** - No desktop required
- **Error handling** - Automatic retries and notifications
- **Debug artifacts** - Screenshots saved for troubleshooting
- **Status monitoring** - Daily status checks

## Setup Steps

### 1. Add Repository Secrets
Go to Settings → Secrets and variables → Actions

Add these secrets:
- `RTN_USERNAME` - Your RTN login username
- `RTN_PASSWORD` - Your RTN login password  
- `DATABASE_URL` - PostgreSQL connection string
- `DISCORD_WEBHOOK` (optional) - For status notifications

### 2. Enable GitHub Actions
- Go to Actions tab in your repository
- Enable workflows if not already enabled

### 3. Test Manual Run
1. Go to Actions tab
2. Select "RTN Fair Meadows Capture"
3. Click "Run workflow"
4. Set duration (default 3 hours)
5. Click "Run workflow" button

## Workflows Created

### 1. `rtn_capture.yml` - Main Capture
- **Schedule**: Thu-Sun at 5:30 PM CT (during season)
- **Duration**: 3 hours per run
- **What it does**:
  - Logs into RTN
  - Navigates to Fair Meadows
  - Captures odds every 5 minutes
  - Saves to database
  - Uploads debug screenshots

### 2. `rtn_monitor.yml` - Status Monitor
- **Schedule**: Daily at 9 PM CT
- **What it does**:
  - Checks database for today's captures
  - Reports races captured and snapshot count
  - Sends Discord notification (if configured)

## Cost Considerations
- **GitHub Actions Free Tier**: 2,000 minutes/month
- **Each capture run**: ~180 minutes (3 hours)
- **Monthly usage**: ~2,160 minutes (4 days × 4 weeks × 3 hours)
- **Recommendation**: Use GitHub Pro ($4/month) for 3,000 minutes

## Monitoring

### Check Workflow Runs
1. Go to Actions tab
2. View workflow history
3. Check for green checkmarks

### Download Debug Images
1. Click on a workflow run
2. Scroll to "Artifacts"
3. Download "debug-images"

### Database Queries
```sql
-- Today's capture summary
SELECT 
    race_number,
    COUNT(DISTINCT program_number) as horses,
    COUNT(*) as snapshots,
    MIN(snapshot_time) as first,
    MAX(snapshot_time) as last
FROM rtn_odds_snapshots
WHERE race_date = CURRENT_DATE
GROUP BY race_number
ORDER BY race_number;

-- Latest odds
SELECT * FROM rtn_odds_snapshots
WHERE race_date = CURRENT_DATE
ORDER BY snapshot_time DESC
LIMIT 20;
```

## Troubleshooting

### Workflow Fails
1. Check workflow logs for errors
2. Download debug screenshots
3. Common issues:
   - RTN login page changed
   - Fair Meadows not racing
   - Browser timeout

### No Data Captured
- Verify Fair Meadows is racing (June 4 - July 19)
- Check RTN subscription is active
- Review debug screenshots for page layout changes

### Manual Intervention
If automated capture fails:
```bash
# SSH into a cloud VM and run manually
python rtn_runner.py
```

## Advanced Configuration

### Adjust Capture Times
Edit `.github/workflows/rtn_capture.yml`:
```yaml
schedule:
  # Change time here (UTC)
  - cron: '30 22 * * 4-7'
```

### Add More Tracks
Modify `rtn_runner_headless.py`:
```python
capture.find_track("Remington Park")  # Add other tracks
```

### Increase Capture Frequency
Change interval in `rtn_runner_headless.py`:
```python
time.sleep(120)  # 2 minutes instead of 5
```

## Notifications

### Discord Webhook
1. Create webhook in Discord server
2. Add URL as `DISCORD_WEBHOOK` secret
3. Get notifications for:
   - Daily status reports
   - Capture failures (via issues)

### Email Notifications
GitHub automatically emails on workflow failures.

## Security Notes
- Credentials stored as encrypted secrets
- No credentials in code
- Screenshots don't contain sensitive data
- Database connection is encrypted

## Next Steps
1. Test with manual workflow run
2. Verify data in database
3. Wait for scheduled run on race day
4. Monitor Discord for status updates