const puppeteer = require('puppeteer');
const { Client } = require('pg');
require('dotenv').config();

class RacingDataVerifier {
  constructor() {
    this.dbClient = new Client({
      connectionString: process.env.DATABASE_URL
    });
    this.baseUrl = 'https://stall10n.onrender.com';
  }

  async connect() {
    await this.dbClient.connect();
    console.log('Connected to database');
  }

  async disconnect() {
    await this.dbClient.end();
    console.log('Disconnected from database');
  }

  async getDbRaces(date) {
    const query = `
      SELECT r.*, 
        json_agg(
          json_build_object(
            'program_number', h.program_number,
            'horse_name', h.horse_name,
            'jockey', h.jockey,
            'trainer', h.trainer,
            'morning_line_odds', h.morning_line_odds,
            'weight', h.weight
          ) ORDER BY h.program_number
        ) as horses
      FROM races r
      LEFT JOIN horses h ON h.race_id = r.id
      WHERE r.date = $1
      GROUP BY r.id
      ORDER BY r.race_number
    `;
    
    const result = await this.dbClient.query(query, [date]);
    return result.rows;
  }

  async scrapeWebData(date) {
    const browser = await puppeteer.launch({ 
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
      const page = await browser.newPage();
      console.log(`Navigating to ${this.baseUrl}`);
      
      // Go to the website
      await page.goto(this.baseUrl, { waitUntil: 'networkidle2', timeout: 60000 });
      
      // Wait for the page to load
      await page.waitForSelector('#race-date', { timeout: 30000 });
      
      // Set the date
      await page.evaluate((dateValue) => {
        document.getElementById('race-date').value = dateValue;
        // Trigger change event
        document.getElementById('race-date').dispatchEvent(new Event('change'));
      }, date);
      
      // Wait for races to load
      await page.waitForTimeout(3000);
      
      // Extract race data
      const webRaces = await page.evaluate(() => {
        const races = [];
        const raceCards = document.querySelectorAll('.race-card');
        
        raceCards.forEach(card => {
          const raceHeader = card.querySelector('.race-header h3')?.textContent || '';
          const raceMatch = raceHeader.match(/Race (\d+) - (.+)/);
          
          if (raceMatch) {
            const raceData = {
              race_number: parseInt(raceMatch[1]),
              track_name: raceMatch[2],
              details: {},
              horses: []
            };
            
            // Extract race details
            const detailSpans = card.querySelectorAll('.race-details span');
            detailSpans.forEach(span => {
              const text = span.textContent;
              if (text.includes('Post Time:')) raceData.details.post_time = text.replace('Post Time:', '').trim();
              if (text.includes('Distance:')) raceData.details.distance = text.replace('Distance:', '').trim();
              if (text.includes('Surface:')) raceData.details.surface = text.replace('Surface:', '').trim();
              if (text.includes('Purse:')) raceData.details.purse = text.replace('Purse:', '').trim();
            });
            
            // Extract race type
            raceData.race_type = card.querySelector('.race-type')?.textContent || 'N/A';
            
            // Extract horses
            const horseRows = card.querySelectorAll('.horses-table tbody tr');
            horseRows.forEach(row => {
              const cells = row.querySelectorAll('td');
              if (cells.length >= 7) {
                raceData.horses.push({
                  program_number: cells[0].textContent.trim(),
                  horse_name: cells[1].textContent.trim(),
                  jockey: cells[2].textContent.trim(),
                  trainer: cells[3].textContent.trim(),
                  weight: cells[4].textContent.trim(),
                  morning_line_odds: cells[5].textContent.trim(),
                  live_odds: cells[6].textContent.trim()
                });
              }
            });
            
            races.push(raceData);
          }
        });
        
        return races;
      });
      
      return webRaces;
      
    } finally {
      await browser.close();
    }
  }

  compareData(dbRaces, webRaces) {
    const report = {
      date: new Date().toISOString(),
      summary: {
        db_race_count: dbRaces.length,
        web_race_count: webRaces.length,
        matches: 0,
        mismatches: 0
      },
      details: []
    };

    // Compare each race
    dbRaces.forEach(dbRace => {
      const webRace = webRaces.find(wr => 
        wr.race_number === dbRace.race_number && 
        wr.track_name === dbRace.track_name
      );

      if (webRace) {
        report.summary.matches++;
        
        const raceComparison = {
          race_number: dbRace.race_number,
          track_name: dbRace.track_name,
          status: 'found',
          differences: []
        };

        // Compare horses
        const dbHorses = dbRace.horses || [];
        const webHorses = webRace.horses || [];

        if (dbHorses.length !== webHorses.length) {
          raceComparison.differences.push({
            field: 'horse_count',
            db_value: dbHorses.length,
            web_value: webHorses.length
          });
        }

        // Compare each horse
        dbHorses.forEach(dbHorse => {
          const webHorse = webHorses.find(wh => 
            wh.program_number === dbHorse.program_number
          );

          if (!webHorse) {
            raceComparison.differences.push({
              field: 'missing_horse',
              horse: dbHorse.horse_name,
              program_number: dbHorse.program_number
            });
          }
        });

        if (raceComparison.differences.length > 0) {
          report.summary.mismatches++;
        }

        report.details.push(raceComparison);
      } else {
        report.summary.mismatches++;
        report.details.push({
          race_number: dbRace.race_number,
          track_name: dbRace.track_name,
          status: 'missing_on_web',
          horse_count: dbRace.horses?.length || 0
        });
      }
    });

    return report;
  }

  async performInitialSync() {
    console.log('Starting initial sync...');
    const today = new Date().toISOString().split('T')[0];
    
    try {
      // Import Python scraper functionality
      const { spawn } = require('child_process');
      
      // Run the Python scraper
      const pythonProcess = spawn('python', ['scraper.py']);
      
      pythonProcess.stdout.on('data', (data) => {
        console.log(`Scraper: ${data}`);
      });
      
      pythonProcess.stderr.on('data', (data) => {
        console.error(`Scraper Error: ${data}`);
      });
      
      await new Promise((resolve, reject) => {
        pythonProcess.on('close', (code) => {
          if (code === 0) {
            console.log('Initial sync completed successfully');
            resolve();
          } else {
            reject(new Error(`Scraper exited with code ${code}`));
          }
        });
      });
      
      // Also run morning line odds sync
      const oddsProcess = spawn('python', ['-c', 'from odds_scraper import run_morning_odds_sync; run_morning_odds_sync()']);
      
      await new Promise((resolve, reject) => {
        oddsProcess.on('close', (code) => {
          if (code === 0) {
            console.log('Morning line odds sync completed');
            resolve();
          } else {
            reject(new Error(`Odds sync exited with code ${code}`));
          }
        });
      });
      
    } catch (error) {
      console.error('Error during initial sync:', error);
      throw error;
    }
  }

  async verify(date = null) {
    if (!date) {
      date = new Date().toISOString().split('T')[0];
    }

    console.log(`\n=== Verifying Racing Data for ${date} ===\n`);

    try {
      // Get data from database
      console.log('Fetching data from database...');
      const dbRaces = await this.getDbRaces(date);
      console.log(`Found ${dbRaces.length} races in database`);

      // Get data from website
      console.log('\nScraping data from website...');
      const webRaces = await this.scrapeWebData(date);
      console.log(`Found ${webRaces.length} races on website`);

      // Compare data
      console.log('\nComparing data...');
      const report = this.compareData(dbRaces, webRaces);

      // Print report
      console.log('\n=== Verification Report ===');
      console.log(`Database races: ${report.summary.db_race_count}`);
      console.log(`Website races: ${report.summary.web_race_count}`);
      console.log(`Matches: ${report.summary.matches}`);
      console.log(`Mismatches: ${report.summary.mismatches}`);

      if (report.details.length > 0) {
        console.log('\n=== Detailed Findings ===');
        report.details.forEach(detail => {
          if (detail.status === 'missing_on_web') {
            console.log(`\n❌ Race ${detail.race_number} at ${detail.track_name} is in DB but not on website`);
            console.log(`   DB has ${detail.horse_count} horses`);
          } else if (detail.differences.length > 0) {
            console.log(`\n⚠️  Race ${detail.race_number} at ${detail.track_name} has differences:`);
            detail.differences.forEach(diff => {
              console.log(`   - ${diff.field}: DB=${diff.db_value}, Web=${diff.web_value}`);
            });
          } else {
            console.log(`\n✅ Race ${detail.race_number} at ${detail.track_name} matches perfectly`);
          }
        });
      }

      return report;
    } catch (error) {
      console.error('Error during verification:', error);
      throw error;
    }
  }
}

// Main execution
async function main() {
  const verifier = new RacingDataVerifier();
  
  try {
    await verifier.connect();
    
    // Check if initial sync is needed
    const args = process.argv.slice(2);
    if (args.includes('--sync')) {
      await verifier.performInitialSync();
      console.log('\nWaiting 10 seconds for data to propagate...');
      await new Promise(resolve => setTimeout(resolve, 10000));
    }
    
    // Run verification
    const date = args.find(arg => arg.match(/^\d{4}-\d{2}-\d{2}$/)) || null;
    await verifier.verify(date);
    
  } catch (error) {
    console.error('Fatal error:', error);
    process.exit(1);
  } finally {
    await verifier.disconnect();
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = RacingDataVerifier;