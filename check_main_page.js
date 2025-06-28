const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    // Go to the main page
    await page.goto('https://stall10n.onrender.com/', { waitUntil: 'networkidle2' });
    
    // Take a screenshot of the main page
    await page.screenshot({ path: 'main-page-screenshot.png', fullPage: true });
    console.log('Screenshot saved as main-page-screenshot.png');
    
    // Check if there's a dropdown
    const dropdown = await page.$('#raceDate');
    const dropdownExists = dropdown !== null;
    console.log('Dropdown exists:', dropdownExists);
    
    // Get all options in the dropdown
    if (dropdownExists) {
      const options = await page.$$eval('#raceDate option', opts => opts.map(opt => opt.textContent));
      console.log('Dropdown options:', options);
    }
    
    // Check for the June 27/28 links box
    const june2728Links = await page.$$eval('a[href*="/races/2025-06-"]', links => 
      links.map(link => ({
        text: link.textContent,
        href: link.href
      }))
    );
    console.log('June links found:', june2728Links);
    
    // Check the structure of the page
    const pageStructure = await page.evaluate(() => {
      const mainContainer = document.querySelector('.container');
      const sections = [];
      
      // Find all major sections
      mainContainer.querySelectorAll('div').forEach(div => {
        if (div.style.background || div.style.backgroundColor) {
          sections.push({
            html: div.outerHTML.substring(0, 200) + '...',
            hasJuneLinks: div.textContent.includes('June 27') || div.textContent.includes('June 28')
          });
        }
      });
      
      return sections;
    });
    
    console.log('\nPage sections:');
    pageStructure.forEach((section, i) => {
      console.log(`Section ${i + 1}: Has June links: ${section.hasJuneLinks}`);
    });
    
  } catch (error) {
    console.error('Error:', error);
  } finally {
    await browser.close();
  }
})();