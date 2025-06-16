# Render Deployment Setup for STALL10N with HorseAPI

## Prerequisites
- Render account (https://render.com)
- PostgreSQL database on Render
- HorseAPI access key from https://statpal.io

## Step 1: Database Setup on Render

1. **Create PostgreSQL Database**
   - Go to Render Dashboard → New → PostgreSQL
   - Choose your plan (free tier available)
   - Name: `stall10n-db`
   - Wait for provisioning (~2 minutes)
   - Copy the `Internal Database URL` (starts with `postgres://`)

## Step 2: Web Service Setup

1. **Connect GitHub Repository**
   - New → Web Service
   - Connect your GitHub account
   - Select the STALL10N repository

2. **Configure Build Settings**
   - Name: `stall10n`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`

## Step 3: Environment Variables

In the Render dashboard for your web service, go to "Environment" and add:

```
DATABASE_URL=<paste your Internal Database URL from Step 1>
HORSEAPI_ACCESS_KEY=<your HorseAPI key>
PYTHON_VERSION=3.11.0
PORT=10000
```

## Step 4: Deploy

1. Click "Create Web Service"
2. Wait for initial deploy (~5 minutes)
3. Your app will be available at: `https://stall10n.onrender.com`

## Step 5: Initialize Database Tables

After deployment, run these commands in Render Shell:

```bash
python -c "from horseapi_db_integration import HorseAPIOddsDB; db = HorseAPIOddsDB(); db.create_odds_tables()"
```

## Step 6: Background Worker (Optional)

For continuous odds monitoring, create a Background Worker:

1. New → Background Worker
2. Same repository and environment
3. Start Command: `python horseapi_odds_monitor.py`
4. Add same environment variables

## Monitoring & Logs

- **View Logs**: Dashboard → Your Service → Logs
- **Monitor Status**: `https://stall10n.onrender.com/api/horseapi/monitor/status`
- **Database**: Use Render's database dashboard for queries

## Render-Specific Features

### Auto-Deploy
- Pushes to main branch trigger automatic deploys
- Disable in Settings → Build & Deploy if needed

### Custom Domain
- Settings → Custom Domains
- Add your domain and follow DNS instructions

### Scaling
- Free tier: Spins down after 15 min inactivity
- Paid tier: Always on, more resources

## Troubleshooting

### Common Issues

1. **"Application failed to respond"**
   - Check PORT environment variable is set
   - Verify Start Command is correct

2. **Database Connection Error**
   - Verify DATABASE_URL is the Internal URL
   - Check database is active in dashboard

3. **API Key Error**
   - Verify HORSEAPI_ACCESS_KEY is set correctly
   - No quotes needed in Render env vars

### Health Checks

Add to app.py for Render health checks:
```python
@app.route('/health')
def health():
    return {'status': 'healthy'}, 200
```

## Cost Optimization

- **Free Tier Limits**:
  - Web Service: 750 hours/month
  - PostgreSQL: 1GB storage, 90 days retention
  - Spins down after 15 min inactivity

- **For Production**:
  - Upgrade to Starter ($7/month) for always-on
  - Consider managed PostgreSQL for better performance

## Deployment Checklist

- [ ] PostgreSQL database created
- [ ] DATABASE_URL environment variable set
- [ ] HORSEAPI_ACCESS_KEY environment variable set
- [ ] Web service deployed successfully
- [ ] Database tables initialized
- [ ] Test API endpoints working
- [ ] Monitor endpoint accessible
- [ ] (Optional) Background worker running