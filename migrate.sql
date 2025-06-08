-- Migration script to update existing database

-- Add missing columns if they don't exist
DO $$ 
BEGIN
    -- Add pdf_filename column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='races' AND column_name='pdf_filename') THEN
        ALTER TABLE races ADD COLUMN pdf_filename VARCHAR(255);
    END IF;
    
    -- Add surface column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='races' AND column_name='surface') THEN
        ALTER TABLE races ADD COLUMN surface VARCHAR(20) DEFAULT 'Dirt';
    END IF;
    
    -- Rename columns if needed
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='races' AND column_name='race_date') THEN
        ALTER TABLE races RENAME COLUMN race_date TO date;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='races' AND column_name='track') THEN
        ALTER TABLE races RENAME COLUMN track TO track_name;
    END IF;
END $$;