const puppeteer = require('puppeteer-core'); const path = require('path');
(async () => {
  const browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage();
  await page.goto('file:///' + path.resolve('bot.html').split(path.sep).join('/'), { waitUntil: 'load' });
  await page.waitForFunction('window.__golf');
  const out = await page.evaluate(() => {
    const G = window.__golf, P = G.P, S = P.S, g = G.game;
    const res = [];
    for (let h = 0; h < 18; h++) {
      const pin = g.pins[h];
      const world = { height: G.height, normal: (x, y) => { const e = 1, hh = G.height; const dzx = (hh(x + e, y) - hh(x - e, y)) / 2, dzy = (hh(x, y + e) - hh(x, y - e)) / 2, l = Math.hypot(dzx, dzy, 1); return { x: -dzx / l, y: -dzy / l, z: 1 / l }; }, surface: G.surface, wind: { x: 0, y: 0 }, cup: { x: pin[0], y: pin[1] }, rng: Math.random };
      let made = { 0.3: 0, 1: 0, 2: 0 }, slopes = [];
      for (const d of [0.3, 1, 2]) for (let k = 0; k < 12; k++) {
        const a = k / 12 * Math.PI * 2, x = pin[0] + Math.cos(a) * d, y = pin[1] + Math.sin(a) * d;
        if (G.surface(x, y) !== S.GREEN) continue;
        // pace to roll 0.4 m past on flat, aimed dead straight (no read)
        const v = Math.sqrt(2 * 0.569 * (d + 0.4));
        const r = P.simulate(world, { x, y, z: G.height(x, y) + P.R }, { speed: v, launch: 0, rpm: 0, dir: Math.atan2(pin[1] - y, pin[0] - x), putt: true });
        if (r.result === 'holed') made[d]++;
        const n = world.normal(x, y); slopes.push(Math.hypot(n.x, n.y) / n.z * 100);
      }
      const s = slopes.sort((a, b) => a - b);
      res.push(`hole ${h + 1}: made 1ft ${made[0.3]}/12, 3ft ${made[1]}/12, 6.5ft ${made[2]}/12 | slope % median ${s[s.length >> 1]?.toFixed(1)} max ${s[s.length - 1]?.toFixed(1)}`);
    }
    return res;
  });
  console.log(out.join('\n')); await browser.close();
})();
