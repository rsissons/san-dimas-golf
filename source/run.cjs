const puppeteer = require('puppeteer-core');
const path = require('path');
(async () => {
  const browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new',
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--window-size=900,650'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 900, height: 650 });
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errors.push(m.type() + ': ' + m.text()); });
  await page.goto('file:///' + path.resolve(process.argv[3] || 'bot.html').split(path.sep).join('/'), { waitUntil: 'load' });
  await page.waitForFunction('window.__golf', { timeout: 60000 });
  const mode = process.argv[2] || 'bot';
  if (mode === 'shots') {
    await new Promise(r => setTimeout(r, 1500));
    await page.screenshot({ path: 'start.png' });
    await page.evaluate(() => { document.getElementById('startBtn').click(); });
    await new Promise(r => setTimeout(r, 1500));
    await page.screenshot({ path: 'flyover.png' });
    await page.evaluate(() => { document.getElementById('skip').click(); });
    await new Promise(r => setTimeout(r, 1200));
    await page.screenshot({ path: 'address.png' });
    await page.evaluate(() => window.__golf.hit(100, 0));
    await new Promise(r => setTimeout(r, 2600));
    await page.screenshot({ path: 'flight.png' });
    await new Promise(r => setTimeout(r, 9000));
    await page.screenshot({ path: 'after.png' });
    console.log(await page.evaluate(() => document.getElementById('toast').textContent + ' | ' + document.getElementById('hRow2').textContent));
  } else {
    const t0 = Date.now();
    while (Date.now() - t0 < 600000) {
      const st = await page.evaluate(() => ({ done: !!window.__done, log: window.__log.slice() }));
      if (st.done) break;
      await new Promise(r => setTimeout(r, 2000));
    }
    console.log((await page.evaluate(() => window.__log)).join('\n'));
  }
  console.log(errors.length ? errors.slice(0, 15).join('\n') : 'no console errors');
  await browser.close();
})();
