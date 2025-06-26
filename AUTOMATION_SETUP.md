# ST0CK Automation Setup Guide

## Overview
The ST0CK automation system runs continuously to collect race data without manual intervention.

## Components

1. **automation_runner.py** - Main automation controller
   - Runs every 5 minutes to collect race data
   - Hourly status checks
   - Daily maintenance tasks at 6 AM

2. **api_quota_tracker.py** - Manages API usage limits
   - Tracks daily API calls
   - Prevents quota exceeded errors

3. **start_automation.sh** - Startup script with auto-restart

## Setup Instructions

### 1. Install Dependencies
```bash
cd /Users/alecrichmond/Library/Mobile\ Documents/com~apple~CloudDocs/STALL10N
pip3 install -r requirements.txt
```

### 2. Configure Environment
Edit `start_automation.sh` and set your credentials:
- DATABASE_URL: Your PostgreSQL connection string
- RACE_API_KEY: Your race data API key

### 3. Make Scripts Executable
```bash
chmod +x start_automation.sh
chmod +x automation_runner.py
```

### 4. Set Up Auto-Start on macOS

Install the launch daemon:
```bash
# Copy the plist file to LaunchAgents
cp com.stock.automation.plist ~/Library/LaunchAgents/

# Load the service
launchctl load ~/Library/LaunchAgents/com.stock.automation.plist
```

To start manually:
```bash
launchctl start com.stock.automation
```

To stop:
```bash
launchctl stop com.stock.automation
```

To remove auto-start:
```bash
launchctl unload ~/Library/LaunchAgents/com.stock.automation.plist
```

### 5. For Linux Systems

Create systemd service at `/etc/systemd/system/stock-automation.service`:
```ini
[Unit]
Description=ST0CK Automation Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/STALL10N
ExecStart=/path/to/STALL10N/start_automation.sh
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

Then enable:
```bash
sudo systemctl enable stock-automation
sudo systemctl start stock-automation
```

## Monitoring

### Check Logs
```bash
# View today's log
tail -f logs/automation_$(date +%Y%m%d).log

# View daily reports
cat logs/daily_report_$(date +%Y%m%d).txt
```

### Check Service Status (macOS)
```bash
launchctl list | grep stock
```

### Check API Quota
```bash
cat api_quota_status.json
```

## Schedule

The automation runs:
- **Every 5 minutes**: Check for races starting in 10-15 minutes and pull data
- **Every hour**: Status check and upcoming race preview
- **Daily at 6 AM**: 
  - Rotate logs (keep 7 days)
  - Populate race schedule for next 3 days
  - Generate daily report

## Troubleshooting

1. **Service won't start**
   - Check logs in `logs/automation_stderr.log`
   - Verify database connection
   - Ensure Python path is correct

2. **API errors**
   - Check `api_quota_status.json` for quota
   - Verify API key in environment

3. **Database errors**
   - Ensure PostgreSQL is running
   - Check DATABASE_URL is correct
   - Run database setup if needed

## Manual Testing

Test the automation without auto-start:
```bash
cd /Users/alecrichmond/Library/Mobile\ Documents/com~apple~CloudDocs/STALL10N
python3 automation_runner.py
```

Press Ctrl+C to stop.