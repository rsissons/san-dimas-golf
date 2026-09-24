const P = require('./physics.js');
const CL = {"Driver":[78.44,10.9,2686],"3 Wood":[70.56,9.2,3655],"5 Iron":[58.09,12.1,5361],"7 Iron":[53.72,16.3,7097],"PW":[46.58,24.2,9304],"SW":[39.92,30,10000]};
const YD = 0.9144;
const flat = (surf, slope = 0) => ({ height: (x, y) => x * slope, normal: () => { const n = Math.hypot(slope, 1); return { x: -slope / n, y: 0, z: 1 / n }; }, surface: () => surf, wind: { x: 0, y: 0 }, cup: null, rng: () => 0.5 });
const land = (sLand, sRoll) => ({ ...flat(sRoll), surface: (x) => x < 5 ? P.S.TEE : sLand });
for (const [n, [sp, la, rpm]] of Object.entries(CL)) {
  for (const s of [P.S.FAIRWAY, P.S.GREEN, P.S.ROUGH]) {
    const r = P.simulate(land(s), { x: 0, y: 0, z: P.R }, { speed: sp, launch: la, rpm, dir: 0 });
    const carry = r.firstLand.x / YD, total = r.end.x / YD;
    console.log(n.padEnd(7), P.SURF[s].name.padEnd(8), 'carry', carry.toFixed(0), 'total', total.toFixed(0), 'roll', (total - carry).toFixed(1), 'yd');
  }
}
// Stimpmeter: 1.83 m/s on a flat green should roll about 3 m (stimp 10 ft)
const st = P.simulate(flat(P.S.GREEN), { x: 0, y: 0, z: P.R }, { speed: 1.83, launch: 0, rpm: 0, dir: 0, putt: true });
console.log('stimp roll', (st.end.x / 0.3048).toFixed(1), 'ft');
// Downhill 2% green: does a stopped ball keep rolling?
const dh = P.simulate(flat(P.S.GREEN, -0.02), { x: 0, y: 0, z: P.R }, { speed: 1.83, launch: 0, rpm: 0, dir: 0, putt: true });
console.log('2% downhill stimp', (dh.end.x / 0.3048).toFixed(1), 'ft; 4% ->', (P.simulate(flat(P.S.GREEN, -0.04), { x: 0, y: 0, z: P.R }, { speed: 1.83, launch: 0, rpm: 0, dir: 0, putt: true }).end.x / 0.3048).toFixed(1));
// Putt into cup at various speeds
for (const v of [1.8, 1.9, 2.0, 2.2, 2.4, 2.8]) {
  const w = { ...flat(P.S.GREEN), cup: { x: 3, y: 0 } };
  console.log('putt', v, 'm/s ->', P.simulate(w, { x: 0, y: 0, z: P.R }, { speed: v, launch: 0, rpm: 0, dir: 0, putt: true }).result);
}
// Curve: 7 iron with 10 degree tilt
const c = P.simulate(land(P.S.FAIRWAY), { x: 0, y: 0, z: P.R }, { speed: 53.72, launch: 16.3, rpm: 7097, dir: 0, tilt: 10 });
console.log('7i tilt +10: lands', (c.firstLand.x / YD).toFixed(0), 'yd,', (-c.firstLand.y / YD).toFixed(1), 'yd right');
// Wind: 10 mph into and helping
for (const wx of [-4.47, 4.47]) { const w = { ...land(P.S.FAIRWAY), wind: { x: wx, y: 0 } }; const r = P.simulate(w, { x: 0, y: 0, z: P.R }, { speed: 53.72, launch: 16.3, rpm: 7097, dir: 0 }); console.log('7i wind', wx > 0 ? 'helping' : 'into', 'carry', (r.firstLand.x / YD).toFixed(0)); }
