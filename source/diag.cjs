// Diagnostics for a course: tee lies, tree counts, arroyo coverage, and a shot-by-shot replay of chosen holes
const puppeteer = require('puppeteer-core'), path = require('path');
(async () => {
  const [course = 'marshall-canyon', holesArg = '3', tee = 'white'] = process.argv.slice(2);
  const browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'] });
  const page = await browser.newPage(); await page.setViewport({ width: 900, height: 650 });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('file:///' + path.resolve(__dirname, '../test_site/index.html').split(path.sep).join('/') + `?course=${course}`);
  await page.waitForFunction('window.__golf', { timeout: 60000 });
  const info = await page.evaluate(() => {
    const G = window.__golf, S = G.P.S, name = c => G.P.SURF[c].name, out = [];
    for (const h of G.HOLES) out.push(`${h.n}: ` + Object.entries(h.tees).map(([k, t]) => `${k}=${name(G.surface(t[0], t[1]))}`).join(' '));
    const kinds = {}; for (const t of G.trees) kinds[t.kind] = (kinds[t.kind] || 0) + 1;
    return out.join('\n') + '\ntrees ' + JSON.stringify(kinds);
  });
  console.log(info);
  for (const hn of holesArg.split(',').map(Number)) {
    const log = await page.evaluate(async (hn, tee) => {
      const G = window.__golf, g = G.game, lines = [];
      G.beginRound({ mode: 'practice', day: g.day, seq: [hn - 1], tee, level: 2 });
      g.timeScale = 25; g.noRender = true;
      const wait = ms => new Promise(r => setTimeout(r, ms));
      for (let n = 0; n < 14; n++) {
        for (let k = 0; k < 200 && g.phase !== 'address'; k++) { if (g.phase === 'flyover') document.getElementById('skip').click(); if (!document.getElementById('scoreSheet').hidden) break; await wait(50); }
        if (!document.getElementById('scoreSheet').hidden) break;
        const b = g.ball, pin = g.pins[g.hole], d = Math.hypot(pin[0] - b.x, pin[1] - b.y), c = G.CLUBS[g.club];
        let power = 100;
        if (c.putter) power = Math.min(110, (d / 0.3048) / g.putScale * 100 * 1.03);
        else { const carry = G.carryTable()[g.club].carry; if (d < carry) power = Math.max(15, Math.min(100, ((d / carry) - 0.25) / 0.75 * 100)); }
        const lie = G.P.SURF[G.surface(b.x, b.y)].name;
        G.hit(power, 0);
        for (let k = 0; k < 300 && g.phase === 'flight'; k++) await wait(50);
        await wait(150);
        lines.push(`  ${c.s}@${power.toFixed(0)} from ${lie} ${Math.round(d / 0.9144)}yd -> ${document.getElementById('toast').textContent}`);
      }
      return `hole ${hn}: ` + g.scores[g.hole] + '\n' + lines.join('\n');
    }, hn, tee);
    console.log(log);
  }
  console.log('ERRORS:', errors.length ? errors.join(' | ') : 'none');
  await browser.close();
})();
