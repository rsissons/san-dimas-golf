// Test bot for v3: plays a full 18 (or the daily 3) with perfect tempo and sensible power.
window.__log = [];
window.addEventListener('error', e => window.__log.push('ERROR ' + e.message + ' @' + e.lineno));
try { localStorage.setItem('sdc18:name', JSON.stringify('Test Bot')); } catch {}
(function wait(t0) { if (!window.__golf) { if (Date.now() - t0 > 60000) { window.__log.push('no __golf'); window.__done = true; return; } setTimeout(() => wait(t0), 200); return; } setTimeout(run, 800); })(Date.now());
function run() {
  const G = window.__golf;
  const mode = (location.hash || '#round').slice(1);
  if (mode === 'daily') document.getElementById('chPlay').click();
  else G.beginRound({ mode: 'round', day: G.game.day, seq: [...G.HOLES.keys()], tee: (new URLSearchParams(location.search).get('tee') || 'white'), level: 2 });
  G.game.timeScale = 25; G.game.noRender = true;
  let shots = 0, holeShots = [];
  const tick = () => {
    const g = G.game;
    if (g.phase === 'flyover') document.getElementById('skip').click();
    if (!document.getElementById('nameSheet').hidden) { window.__log.push('name sheet shown'); }
    if (!document.getElementById('scoreSheet').hidden) {
      const res = !document.getElementById('resultBox').hidden;
      if (res) { window.__log.push('RESULT ' + document.getElementById('resultBig').textContent + ' | ' + document.getElementById('resultSub').textContent); window.__done = true; return; }
      window.__log.push(`hole ${G.HOLES[g.hole].n}: ${g.scores[g.hole]} (par ${G.parOf(G.HOLES[g.hole])}) ${holeShots.join(' | ')}`);
      holeShots = [];
      document.querySelector('#scButtons .btnGo').click();
    } else if (g.phase === 'address') {
      const b = g.ball, pin = g.pins[g.hole], d = Math.hypot(pin[0] - b.x, pin[1] - b.y), c = G.CLUBS[g.club];
      let power = 100;
      if (c.putter) power = Math.min(110, (d / 0.3048) / g.putScale * 100 * 1.03);
      else { const carry = G.carryTable()[g.club].carry; if (d < carry) power = Math.max(15, Math.min(100, ((d / carry) - 0.25) / 0.75 * 100)); }
      holeShots.push(`${c.s}@${power.toFixed(0)}`);
      shots++; G.hit(power, 0);
    }
    if (shots > 400) { window.__log.push('too many shots'); window.__done = true; return; }
    setTimeout(tick, 60);
  };
  tick();
}
