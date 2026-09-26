// Hole picker test: node source/jump_test.cjs [course]. Uses test_site (leaderboard off).
const puppeteer = require('puppeteer-core'), path = require('path');
(async () => {
  const course = process.argv[2] || 'san-dimas';
  const browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new',
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
  const out = [], ok = (n, p, note = '') => out.push(`${p ? 'PASS' : 'FAIL'}  ${n}${note ? '  - ' + note : ''}`);
  const errors = [];
  const url = 'file:///' + path.resolve(__dirname, '../test_site/index.html').split(path.sep).join('/') + `?course=${course}`;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  for (const [w, h, tag] of [[1180, 820, 'ipad'], [390, 844, 'phone']]) {
    const page = await browser.newPage(); await page.setViewport({ width: w, height: h });
    page.on('pageerror', e => errors.push(tag + ' pageerror: ' + String(e.stack || e.message).split(String.fromCharCode(10)).slice(0, 4).join(' / ')));
    page.on('console', m => { if (m.type() === 'error') errors.push(tag + ' console: ' + m.text()); });
    await page.goto(url, { waitUntil: 'load' });
    await page.evaluate(() => { localStorage.clear(); localStorage.setItem('sdc18:name', JSON.stringify('Tester')); });
    await page.reload({ waitUntil: 'load' });
    await page.waitForFunction(() => { const l = document.getElementById('loading'); return !!window.__golf && (!l || l.hidden || l.style.display === 'none'); }, { timeout: 60000 });
    await sleep(1500);
    await page.click('#freeGo');
    await page.waitForFunction(() => ['address', 'flyover'].includes(window.__golf.game.phase), { timeout: 30000 });
    // Finish hole 1 with a 5 and move to hole 2, so there's a saved scored round
    await page.evaluate(() => { const G = window.__golf; G.game.scores[0] = 5; G.startHole(1, false); });
    const saved0 = await page.evaluate(() => Object.entries(localStorage).find(([k]) => k.endsWith('round'))?.[1]);
    const vis = await page.$eval('#holesBtn', b => !b.hidden && b.getBoundingClientRect().width > 0);
    ok(`${tag}: Holes button shows in Full 18`, vis);
    const overlap = await page.evaluate(() => { const r = id => document.getElementById(id).getBoundingClientRect(); const a = r('topRight'), b = r('leftCol'); return a.left < b.right && a.bottom > b.top; });
    ok(`${tag}: top buttons clear of the hole card`, !overlap);
    await page.screenshot({ path: `shots/jump_${tag}_hud.png` });
    await page.click('#holesBtn'); await sleep(300);
    const sheet = await page.evaluate(() => ({ open: !document.getElementById('holesSheet').hidden, warn: !document.getElementById('hjWarn').hidden, n: document.querySelectorAll('#hjGrid .hj').length, cur: document.querySelector('.hj[aria-current="true"] .n')?.textContent, s1: document.querySelector('#hjGrid .hj .s').textContent }));
    ok(`${tag}: picker opens with 18 holes, practice warning, hole 2 current, hole 1 shows 5`, sheet.open && sheet.warn && sheet.n === 18 && sheet.cur === '2' && sheet.s1 === '5', JSON.stringify(sheet));
    await page.screenshot({ path: `shots/jump_${tag}_picker.png` });
    await page.evaluate(() => document.querySelectorAll('#hjGrid .hj')[6].click());
    await sleep(500);
    const st = await page.evaluate(() => ({ mode: window.__golf.game.mode, hole: window.__golf.game.hole, closed: document.getElementById('holesSheet').hidden }));
    ok(`${tag}: jump to hole 7 makes it practice`, st.mode === 'practice' && st.hole === 6 && st.closed, JSON.stringify(st));
    const saved1 = await page.evaluate(() => Object.entries(localStorage).find(([k]) => k.endsWith('round'))?.[1]);
    ok(`${tag}: saved scored round untouched`, saved1 === saved0 && !!saved0);
    // Play 7 with a 4, jump to 18, score it, finish
    await page.evaluate(() => { const G = window.__golf; G.game.scores[6] = 4; G.jumpTo(17); G.game.scores[17] = 6; });
    await page.evaluate(() => window.__golf.finishRound()); await sleep(300);
    const res = await page.evaluate(() => ({ big: document.getElementById('resultBig').textContent, sub: document.getElementById('resultSub').textContent, board: document.getElementById('resultBoard').hidden, saved: Object.entries(localStorage).find(([k]) => k.endsWith('round'))?.[1] }));
    ok(`${tag}: practice results count only played holes, no posting, round kept`, /over the 3 holes/.test(res.sub) && res.board && res.saved === saved0, `${res.big} | ${res.sub}`);
    await page.evaluate(() => window.__golf.showLobby()); await sleep(300);
    ok(`${tag}: Resume still offered in the lobby`, await page.$eval('#freeResume', b => !b.hidden));
    // Scored daily hides the button
    await page.evaluate(() => { const G = window.__golf, d = G.dailyHoles(G.game.day || undefined); document.getElementById('scoreSheet').hidden = true; G.beginRound({ mode: 'daily', day: G.game.day, seq: G.dailyHoles(G.game.day), tee: 'white', level: 2 }); });
    await sleep(500);
    ok(`${tag}: Holes button hidden in the scored daily`, await page.$eval('#holesBtn', b => b.hidden));
    await page.close();
  }
  console.log(out.join('\n')); console.log('ERRORS:', errors.length ? errors.join('\n') : 'none');
  await browser.close();
})();
