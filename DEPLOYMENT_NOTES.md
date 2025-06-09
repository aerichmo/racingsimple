# Deployment Notes

## Apply Database Schema on Render

To apply the simplified schema to your production database on Render:

### Option 1: Using Render Shell

1. Go to your Render dashboard
2. Navigate to your web service
3. Click on "Shell" tab
4. Run: `python apply_schema.py`

### Option 2: Using psql directly

1. Get your database URL from Render dashboard
2. Run locally:
   ```bash
   export DATABASE_URL="your-render-database-url"
   psql $DATABASE_URL < schema.sql
   ```

### Option 3: Manual SQL execution

1. Go to your Render PostgreSQL dashboard
2. Use the SQL query interface
3. Copy and paste the contents of `schema.sql`
4. Execute the SQL

## Important Notes

- The schema will DROP existing tables and recreate them
- All previous data will be lost (this is intentional for the simplification)
- Only 3 tables will exist after: sessions, races, race_entries

## Verify Schema Applied

After applying, you can verify with:
```sql
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

Should show:
- sessions
- races  
- race_entries