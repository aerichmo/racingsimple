# Fair Meadows Data Scheduler Setup

## Overview
This document explains how to automatically pull Fair Meadows race data at 8am on race days.

## Manual Execution
To manually pull data for today:
```bash
python3 pull_fair_meadows_data.py
```

To pull data for a specific date (only works for current day):
```bash
python3 pull_fair_meadows_data.py --date 2025-06-18
```

## Automatic Scheduling Options

### Option 1: macOS (using cron)

1. Open Terminal and edit crontab:
```bash
crontab -e
```

2. Add this line to run at 8am CST every day:
```bash
0 8 * * * cd /Users/alecrichmond/Library/Mobile\ Documents/com~apple~CloudDocs/STALL10N && /usr/bin/python3 pull_fair_meadows_data.py >> fair_meadows_pull.log 2>&1
```

3. Save and exit (in vim: `:wq`)

### Option 2: macOS (using launchd - Recommended)

1. Create a plist file:
```bash
nano ~/Library/LaunchAgents/com.stall10n.fairmeadows.plist
```

2. Add this content:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.stall10n.fairmeadows</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/alecrichmond/Library/Mobile Documents/com~apple~CloudDocs/STALL10N/pull_fair_meadows_data.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/alecrichmond/Library/Mobile Documents/com~apple~CloudDocs/STALL10N/fair_meadows_pull.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/alecrichmond/Library/Mobile Documents/com~apple~CloudDocs/STALL10N/fair_meadows_pull_error.log</string>
</dict>
</plist>
```

3. Load the schedule:
```bash
launchctl load ~/Library/LaunchAgents/com.stall10n.fairmeadows.plist
```

To unload:
```bash
launchctl unload ~/Library/LaunchAgents/com.stall10n.fairmeadows.plist
```

### Option 3: Cloud Deployment (Render.com)

Add to your `render.yaml`:
```yaml
services:
  - type: cron
    name: fair-meadows-puller
    runtime: python
    schedule: "0 13 * * *"  # 8am CST = 1pm UTC
    buildCommand: pip install -r requirements.txt
    startCommand: python pull_fair_meadows_data.py
    envVars:
      - key: STATPAL_ACCESS_KEY
        sync: false
```

## Important Notes

1. **Time Zone**: Adjust the hour based on your system's time zone. The examples use:
   - 8am local time for cron/launchd
   - 1pm UTC for Render (8am CST)

2. **API Limitations**: StatPal only provides current day data, so the script will only return real data when run on the actual race day.

3. **File Outputs**: The script creates:
   - `fair_meadows_june18_2025.json` - Race data in JSON format
   - `fair_meadows_june18_2025.html` - Formatted HTML page
   - Removes the placeholder page when real data is available

4. **Logs**: Check logs for execution status:
   - `fair_meadows_pull.log` - Standard output
   - `fair_meadows_pull_error.log` - Error messages

## Testing

To test if your schedule is working:
1. Set it to run in 2 minutes
2. Check if the log files are created
3. Verify the HTML page is generated
4. Reset to 8am for production