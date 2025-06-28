const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ 
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  
  try {
    console.log('Loading page...');
    await page.goto('https://stall10n.onrender.com/', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    console.log('Page loaded, checking structure...');
    
    // Get the HTML of the main container
    const pageContent = await page.evaluate(() => {
      const container = document.querySelector('.container');
      if (!container) return 'No container found';
      
      // Find the June 27/28 box
      const juneBox = Array.from(container.querySelectorAll('div')).find(div => 
        div.textContent.includes('June 27') && div.textContent.includes('June 28')
      );
      
      // Check dropdown options
      const dropdown = document.querySelector('#raceDate');
      const dropdownOptions = dropdown ? Array.from(dropdown.options).map(opt => opt.textContent) : [];
      
      return {
        hasJuneBox: !!juneBox,
        juneBoxHTML: juneBox ? juneBox.outerHTML.substring(0, 500) : null,
        dropdownOptions: dropdownOptions,
        hasDropdown: !!dropdown
      };
    });
    
    console.log('\nPage Analysis:');
    console.log('Has dropdown:', pageContent.hasDropdown);
    console.log('Dropdown options:', pageContent.dropdownOptions);
    console.log('Has separate June 27/28 box:', pageContent.hasJuneBox);
    
    if (pageContent.juneBoxHTML) {
      console.log('\nJune box HTML preview:');
      console.log(pageContent.juneBoxHTML);
    }
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();