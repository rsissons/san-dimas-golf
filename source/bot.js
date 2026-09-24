// Test bot: plays a full round with perfect tempo and sensible power, logging every hole.
window.__log = [];
window.addEventListener('error', e => window.__log.push('ERROR ' + e.message + ' @' + e.lineno));
setTimeout(function run() {
  const G = window.__golf; if (!G) { window.__log.push('no __golf'); return; }
  document.getElementById('startBtn').click();
  G.game.timeScale = 25; G.game.noRender = true;
  let shots = 0, lastPhase = '', holeShots = [];
  const tick = () => {
    const g = G.game;
    if (g.phase === 'flyover') document.getElementById('skip').click();
    if (!document.getElementById('scoreSheet').hidden) {
      window.__log.push(`hole ${g.hole + 1}: ${g.scores[g.hole]} (par ${G.HOLES[g.hole].par}) shots: ${holeShots.join(' | ')}`);
      holeShots = [];
      const btn = document.querySelector('#scButtons .primary');
      if (g.scores.every(s => s != null)) { window.__log.push('DONE total ' + g.scores.reduce((a, b) => a + b, 0)); window.__done = true; return; }
      btn.click();
    } else if (g.phase === 'address') {
      const b = g.ball, pin = g.pins[g.hole], d = Math.hypot(pin[0] - b.x, pin[1] - b.y), c = G.CLUBS[g.club];
      let power = 100;
      if (c.putter) power = Math.min(110, (d / 0.3048) / g.putScale * 100 * 1.03);
      else { const carry = G.carryTable()[g.club].carry; if (d < carry) power = Math.max(15, Math.min(100, ((d / carry) - 0.25) / 0.75 * 100)); }
      holeShots.push(`${c.n.replace(' Iron', 'i').replace(' Wood', 'W').replace(' Wedge', 'W')}@${power.toFixed(0)} ${G.P.SURF[G.surface(b.x, b.y)].name[0]} ${Math.round(d / 0.9144)}y`);
      shots++;
      G.hit(power, 0);
      window.__shots = shots;
    }
    if (shots > 400) { window.__log.push('too many shots'); window.__done = true; return; }
    setTimeout(tick, 60);
  };
  tick();
}, 1500);
