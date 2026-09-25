// Screenshots: node source/shots.cjs <course> <outPrefix> [holes comma list] [w] [h]
const puppeteer = require('puppeteer-core'), path = require('path');
(async () => {
  const [course = 'marshall-canyon', out = 'shot', holes = '12', w = '1180', h = '820'] = process.argv.slice(2);
  const browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'] });
  const page = await browser.newPage(); await page.setViewport({ width: +w, height: +h });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('file:///' + path.resolve(__dirname, '../test_site/index.html').split(path.sep).join('/') + `?course=${course}`);
  await page.waitForFunction('window.__golf', { timeout: 60000 }); await new Promise(r => setTimeout(r, 4000));
  await page.screenshot({ path: `${out}-lobby.png` });
  for (const hn of holes.split(',').map(Number)) {
    await page.evaluate(hn => { try { localStorage.setItem('sdc18:name', JSON.stringify('Shot Bot')); } catch {} const G = window.__golf; G.beginRound({ mode: 'practice', day: G.game.day, seq: [hn - 1], tee: 'white', level: 2 }); document.getElementById('skip').click(); }, hn);
    await new Promise(r => setTimeout(r, 3500));
    await page.screenshot({ path: `${out}-h${hn}.png` });
  }
  console.log('ERRORS:', errors.length ? errors.join(' | ') : 'none');
  await browser.close();
})();
