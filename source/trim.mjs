import { fly } from './flight.mjs';
import { P, CLUBS } from './flight.mjs';
const MPH = 0.44704;
// Wedges (not in the TrackMan table above): typical tour gap / sand / lob numbers
const extra = [['GW', 95, 27.5, 9500, 122], ['SW', 88, 30, 10000, 108], ['LW', 80, 33, 10200, 93]];
const rows = [...CLUBS.map(c => c.slice(0, 5)), ...extra];
const out = [];
for (const [n, s, l, rpm, c] of rows) {
  let lo = 0.8, hi = 1.25;
  for (let i = 0; i < 40; i++) { const mid = (lo + hi) / 2; (fly(s * MPH * mid, l, rpm, P).carry < c ? lo = mid : hi = mid); }
  const k = (lo + hi) / 2, f = fly(s * MPH * k, l, rpm, P);
  out.push({ n, speed: +(s * MPH * k).toFixed(2), launch: l, rpm, carry: c });
  console.log(n.padEnd(7), 'trim', k.toFixed(3), 'carry', f.carry.toFixed(1), 'apex', f.apex.toFixed(0), 'land', f.land.toFixed(0));
}
console.log(JSON.stringify(out));
