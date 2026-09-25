// Plays the bot round in headless Chrome: node source/test.cjs <course-id> [round|daily] [tee]
const puppeteer = require('puppeteer-core'), path = require('path');
(async () => {
  const [course = 'san-dimas', mode = 'round', tee = 'white'] = process.argv.slice(2);
  const browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new',
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
  const page = await browser.newPage(); await page.setViewport({ width: 900, height: 650 });
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  const url = 'file:///' + path.resolve(__dirname, '../test_site/bot.html').split(path.sep).join('/') + `?course=${course}&tee=${tee}#${mode}`;
  await page.goto(url, { waitUntil: 'load' });
  const t0 = Date.now();
  while (!(await page.evaluate(() => window.__done)) && Date.now() - t0 < 900000) await new Promise(r => setTimeout(r, 2000));
  console.log((await page.evaluate(() => window.__log)).join('\n'));
  console.log('ERRORS:', errors.length ? errors.join('\n') : 'none', '|', Math.round((Date.now() - t0) / 1000), 's');
  await browser.close();
})();
