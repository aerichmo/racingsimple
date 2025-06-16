# Quick Deploy to Render

## 1. One-Click Deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

Or manually:

## 2. Manual Deploy Steps

### A. Fork/Clone Repository
```bash
git clone https://github.com/yourusername/STALL10N.git
cd STALL10N
```

### B. Create Render Services

1. **Sign in to Render**: https://dashboard.render.com

2. **Create New → Blueprint**
   - Connect GitHub repo
   - Select STALL10N repository
   - Render will use `render.yaml`

3. **Set Environment Variables**
   When prompted, add:
   ```
   HORSEAPI_ACCESS_KEY = your_api_key_from_statpal.io
   ```

4. **Deploy**
   - Click "Apply"
   - Wait ~5 minutes for deployment

### C. Initialize Database

1. Go to your web service in Render dashboard
2. Click "Shell" tab
3. Run:
   ```bash
   python render_init.py
   ```

## 3. Verify Deployment

Check these endpoints:
- Health: `https://stall10n.onrender.com/health`
- Home: `https://stall10n.onrender.com/`
- API Status: `https://stall10n.onrender.com/api/horseapi/monitor/status`

## 4. Enable Race Monitoring

Use curl or Postman:
```bash
curl -X POST https://stall10n.onrender.com/api/horseapi/monitor/race/1 \
  -H "Content-Type: application/json" \
  -d '{
    "horse_api_race_id": "ABC123",
    "post_time": "2025-06-16T14:30:00"
  }'
```

## 5. Monitor Logs

- Web Service Logs: Dashboard → stall10n → Logs
- Background Worker Logs: Dashboard → stall10n-odds-monitor → Logs

## Troubleshooting

### "Application failed to respond"
- Check environment variables are set
- View logs for specific errors

### "Database connection failed"
- Verify database is active
- Check DATABASE_URL is using Internal URL

### "HorseAPI not configured"
- Add HORSEAPI_ACCESS_KEY in Environment tab
- Redeploy after adding

## Free Tier Notes

- Web service spins down after 15 min inactivity
- First request after spin down takes ~30 seconds
- Database free for 90 days
- 750 hours/month included