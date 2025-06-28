const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ 
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  
  try {
    console.log('Loading API data...');
    
    // First check what dates are in the database via the API
    await page.goto('https://stall10n.onrender.com/api/races', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    const apiData = await page.evaluate(() => {
      return JSON.parse(document.body.textContent);
    });
    
    // Get unique dates
    const uniqueDates = [...new Set(apiData.map(race => race.race_date))].sort();
    
    console.log('\nUnique dates in database:', uniqueDates);
    console.log('Total races:', apiData.length);
    
    // Count races per date
    const racesByDate = {};
    apiData.forEach(race => {
      if (!racesByDate[race.race_date]) {
        racesByDate[race.race_date] = 0;
      }
      racesByDate[race.race_date]++;
    });
    
    console.log('\nRaces per date:');
    Object.entries(racesByDate).forEach(([date, count]) => {
      console.log(`${date}: ${count} horses`);
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();