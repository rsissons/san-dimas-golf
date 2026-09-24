// Ball-flight model calibration: drag + Magnus lift + spin decay, fitted to TrackMan PGA Tour averages.
const MPH = 0.44704, YD = 0.9144, RPM = 2 * Math.PI / 60;
const m = 0.04593, r = 0.02135, A = Math.PI * r * r, rho = 1.16, g = 9.81; // rho at ~1,200 ft
// TrackMan PGA Tour averages: ball speed mph, launch deg, spin rpm, carry yd, apex yd
const CLUBS = [
  ['Driver', 167, 10.9, 2686, 275, 32], ['3 Wood', 158, 9.2, 3655, 243, 30], ['5 Wood', 152, 9.4, 4350, 230, 31],
  ['Hybrid', 146, 10.2, 4437, 225, 29], ['3 Iron', 142, 10.4, 4630, 212, 27], ['4 Iron', 137, 11.0, 4836, 203, 28],
  ['5 Iron', 132, 12.1, 5361, 194, 31], ['6 Iron', 127, 14.1, 6231, 183, 30], ['7 Iron', 120, 16.3, 7097, 172, 32],
  ['8 Iron', 115, 18.1, 7998, 160, 31], ['9 Iron', 109, 20.4, 8647, 148, 30], ['PW', 102, 24.2, 9304, 136, 29],
];
export function fly(speed, launchDeg, rpm, P) {
  let x = 0, y = 0, vx = speed * Math.cos(launchDeg * Math.PI / 180), vy = speed * Math.sin(launchDeg * Math.PI / 180);
  let w = rpm * RPM, t = 0, apex = 0; const dt = 1 / 500;
  while (y >= 0 || t < 0.1) {
    const v = Math.hypot(vx, vy), S = r * w / v;
    const Cd = Math.max(0.12, P.cd0 + P.cd1 * S - P.cdv * (v - 50) / 25), Cl = Math.min(P.clMax, P.cl * Math.pow(S, P.clp));
    const k = 0.5 * rho * A * v / m;
    const ax = -k * (Cd * vx + Cl * vy), ay = -g + k * (Cl * vx - Cd * vy);
    vx += ax * dt; vy += ay * dt; x += vx * dt; y += vy * dt; t += dt;
    w *= Math.exp(-P.decay * dt); apex = Math.max(apex, y);
    if (t > 15) break;
  }
  return { carry: x / YD, apex: apex / YD, t, land: Math.atan2(-vy, vx) * 180 / Math.PI };
}
function err(P) {
  let e = 0;
  for (const [, s, l, rpm, c, a] of CLUBS) { const f = fly(s * MPH, l, rpm, P); e += ((f.carry - c) / c) ** 2 + 0.25 * ((f.apex - a) / a) ** 2; }
  return e;
}
export const P = { cd0: 0.2493, cd1: 0.2038, cl: 0.485, clp: 0.412, clMax: 0.3395, decay: 0.0172, cdv: 0.0192 };
export { CLUBS };
