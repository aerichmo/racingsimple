const puppeteer = require('puppeteer');

async function verifyRacingDisplay() {
    console.log('=== Verifying STALL10N Racing Display ===\n');
    
    const browser = await puppeteer.launch({ 
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
        const page = await browser.newPage();
        
        // Set viewport
        await page.setViewport({ width: 1400, height: 900 });
        
        // Navigate to the racing page
        console.log('Navigating to https://stall10n.onrender.com/');
        await page.goto('https://stall10n.onrender.com/', { 
            waitUntil: 'networkidle2',
            timeout: 30000 
        });
        
        // Wait for races to load
        await page.waitForSelector('#races', { timeout: 10000 });
        
        // Take a screenshot
        await page.screenshot({ 
            path: 'stall10n_racing_page.png',
            fullPage: true 
        });
        console.log('Screenshot saved as stall10n_racing_page.png');
        
        // Check if date selector exists and has options
        const dateOptions = await page.evaluate(() => {
            const select = document.getElementById('raceDate');
            if (!select) return [];
            return Array.from(select.options).map(opt => opt.value).filter(v => v);
        });
        
        console.log('\nAvailable dates:', dateOptions);
        
        // Check for June 11 and 12
        for (const date of ['2025-06-11', '2025-06-12']) {
            if (dateOptions.includes(date)) {
                console.log(`\nChecking ${date} data...`);
                
                // Select the date
                await page.select('#raceDate', date);
                await page.waitForTimeout(1000); // Wait for render
                
                // Check race data
                const raceData = await page.evaluate((targetDate) => {
                    const tables = document.querySelectorAll('table');
                    const races = [];
                    
                    tables.forEach((table, index) => {
                        const rows = table.querySelectorAll('tr');
                        const headers = Array.from(rows[0].querySelectorAll('th')).map(th => th.textContent);
                        const hasLiveOdds = headers.includes('Live Odds');
                        const hasStatus = headers.includes('Status');
                        
                        const horses = [];
                        for (let i = 1; i < rows.length; i++) {
                            const cells = rows[i].querySelectorAll('td');
                            if (cells.length > 0) {
                                const horseData = {
                                    programNumber: cells[0]?.textContent,
                                    horseName: cells[1]?.textContent,
                                    winProbability: cells[2]?.textContent,
                                    adjOdds: cells[3]?.textContent,
                                    morningLine: cells[4]?.textContent
                                };
                                
                                if (hasLiveOdds && cells[5]) {
                                    horseData.liveOdds = cells[5]?.textContent;
                                }
                                if (hasStatus && cells[6]) {
                                    horseData.status = cells[6]?.textContent;
                                }
                                
                                horses.push(horseData);
                            }
                        }
                        
                        if (horses.length > 0) {
                            races.push({
                                raceNumber: index + 1,
                                hasLiveOddsColumn: hasLiveOdds,
                                hasStatusColumn: hasStatus,
                                horseCount: horses.length,
                                sampleHorses: horses.slice(0, 3)
                            });
                        }
                    });
                    
                    return races;
                }, date);
                
                console.log(`Found ${raceData.length} races`);
                
                raceData.forEach(race => {
                    console.log(`\nRace ${race.raceNumber}:`);
                    console.log(`  - Has Live Odds column: ${race.hasLiveOddsColumn}`);
                    console.log(`  - Has Status column: ${race.hasStatusColumn}`);
                    console.log(`  - Number of horses: ${race.horseCount}`);
                    console.log('  - Sample horses:');
                    race.sampleHorses.forEach(horse => {
                        console.log(`    #${horse.programNumber} ${horse.horseName}`);
                        console.log(`      Win Prob: ${horse.winProbability}, ML: ${horse.morningLine}`);
                        if (horse.liveOdds !== undefined) {
                            console.log(`      Live Odds: ${horse.liveOdds}`);
                        }
                        if (horse.status !== undefined) {
                            console.log(`      Status: ${horse.status}`);
                        }
                    });
                });
                
                // Take screenshot of this date
                await page.screenshot({ 
                    path: `stall10n_${date}.png`,
                    fullPage: true 
                });
                console.log(`\nScreenshot saved as stall10n_${date}.png`);
            }
        }
        
        // Check if live data is being fetched
        console.log('\n=== Checking Live Data Fetch ===');
        
        // Wait a bit to see if fetchLiveData runs
        await page.waitForTimeout(2000);
        
        // Check console logs
        page.on('console', msg => {
            if (msg.text().includes('Error fetching data') || msg.text().includes('live')) {
                console.log('Console:', msg.text());
            }
        });
        
        // Check network requests for API calls
        const apiCalls = [];
        page.on('response', response => {
            const url = response.url();
            if (url.includes('/api/')) {
                apiCalls.push({
                    url: url,
                    status: response.status()
                });
            }
        });
        
        // Trigger a refresh to capture API calls
        await page.reload({ waitUntil: 'networkidle2' });
        await page.waitForTimeout(3000);
        
        console.log('\nAPI calls made:');
        apiCalls.forEach(call => {
            console.log(`  ${call.url} - Status: ${call.status}`);
        });
        
    } catch (error) {
        console.error('Error during verification:', error);
    } finally {
        await browser.close();
    }
    
    console.log('\n=== Verification Complete ===');
    console.log('Check the screenshot files to see the current display.');
}

// Run the verification
verifyRacingDisplay().catch(console.error);