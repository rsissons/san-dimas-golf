// Golf ball physics: flight (drag, Magnus lift, spin decay, wind), impacts with spin-aware friction,
// rolling with slope and rolling resistance, trees, and the cup. World units are metres, z up.
const GolfPhysics = (() => {
  const g = 9.81, m = 0.04593, R = 0.02135, A = Math.PI * R * R, RHO = 1.16, K = 0.5 * RHO * A / m;
  // Aerodynamics fitted to TrackMan PGA Tour averages (see calibration notes)
  const AERO = { cd0: 0.2493, cd1: 0.2038, cl: 0.485, clp: 0.412, clMax: 0.3395, decay: 0.0172, cdv: 0.0192 };
  const CUP_R = 0.054;

  // Surface codes shared with the lie map
  const S = { OB: 0, ROUGH: 1, FAIRWAY: 2, GREEN: 3, FRINGE: 4, TEE: 5, BUNKER: 6, WATER: 7, PATH: 8, NATIVE: 9, ARROYO: 10 };
  // e: restitution, mu: impact friction, roll: rolling resistance (× g), hold: extra static friction on slopes
  const SURF = {
    [S.OB]:      { name: 'Out of bounds', e: 0.18, mu: 0.55, roll: 0.40, hold: 1.6, soft: 0.5, drag: 0.3 },
    [S.ROUGH]:   { name: 'Rough',         e: 0.16, mu: 0.30, roll: 0.36, hold: 1.8, soft: 0.5, drag: 0.3 },
    [S.FAIRWAY]: { name: 'Fairway',       e: 0.34, mu: 0.42, roll: 0.105, hold: 1.25, soft: 0.25, drag: 0.12 },
    [S.GREEN]:   { name: 'Green',         e: 0.22, mu: 0.50, roll: 0.058, hold: 1.25, soft: 0.36, drag: 0.08 },
    [S.FRINGE]:  { name: 'Fringe',        e: 0.26, mu: 0.45, roll: 0.13, hold: 1.3, soft: 0.34, drag: 0.12 },
    [S.TEE]:     { name: 'Tee box',       e: 0.34, mu: 0.42, roll: 0.11, hold: 1.25, soft: 0.25, drag: 0.12 },
    [S.BUNKER]:  { name: 'Bunker',        e: 0.04, mu: 0.90, roll: 1.4, hold: 3, soft: 1.2 },
    [S.WATER]:   { name: 'Water',         e: 0, mu: 1, roll: 5, hold: 5, soft: 2 },
    [S.PATH]:    { name: 'Cart path',     e: 0.58, mu: 0.30, roll: 0.035, hold: 1.2, soft: 0.05 },
    [S.NATIVE]:  { name: 'Native area',   e: 0.12, mu: 0.60, roll: 0.60, hold: 2.5, soft: 0.7, drag: 0.4 },
    [S.ARROYO]:  { name: 'Arroyo',        e: 0, mu: 1, roll: 5, hold: 5, soft: 2 },
  };
  // Hazards: the ball is gone (water) or unplayable in the brush (a dry arroyo); both play as a penalty and a drop
  const HAZARD = sc => sc === S.WATER || sc === S.ARROYO;

  const v3 = (x, y, z) => ({ x, y, z });
  const dot = (a, b) => a.x * b.x + a.y * b.y + a.z * b.z;
  const len = a => Math.hypot(a.x, a.y, a.z);
  const scale = (a, s) => v3(a.x * s, a.y * s, a.z * s);
  const add = (a, b) => v3(a.x + b.x, a.y + b.y, a.z + b.z);
  const sub = (a, b) => v3(a.x - b.x, a.y - b.y, a.z - b.z);
  const cross = (a, b) => v3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x);
  const norm = a => { const l = len(a) || 1; return scale(a, 1 / l); };
  const UP = v3(0, 0, 1);

  // world: { height(x,y), normal(x,y) -> {x,y,z}, surface(x,y) -> code, wind: {x,y} m/s,
  //          trees: [{x,y,base,trunk,cz,rx,rz}], treeGrid, cup: {x,y} | null, rng() }
  function simulate(world, start, shot) {
    const rng = world.rng || Math.random;
    const path = [];
    let p = v3(start.x, start.y, start.z);
    const dir = v3(Math.cos(shot.dir), Math.sin(shot.dir), 0);
    const la = shot.launch * Math.PI / 180;
    let v = add(scale(dir, shot.speed * Math.cos(la)), scale(UP, shot.speed * Math.sin(la)));
    let w = (shot.rpm || 0) * 2 * Math.PI / 60;          // backspin, rad/s
    const tilt = (shot.tilt || 0) * Math.PI / 180;        // spin-axis tilt: + curves right
    let t = 0, mode = shot.putt ? 'roll' : 'air';
    let firstLand = null, result = 'rest', bounces = 0, hitTree = false, hazard = null, lastSurf = world.surface(p.x, p.y);
    let air = 0, lipped = false;
    const rec = () => path.push([+t.toFixed(3), +p.x.toFixed(3), +p.y.toFixed(3), +p.z.toFixed(3)]);
    rec();

    const windAt = z => {
      const agl = Math.max(0, z - world.height(p.x, p.y));
      const f = agl < 2 ? agl / 2 * 0.6 : Math.min(1.25, 0.6 + 0.4 * Math.pow(agl / 10, 0.3));
      return v3(world.wind.x * f, world.wind.y * f, 0);
    };

    while (t < 45) {
      if (mode === 'air') {
        const dt = 1 / 240;
        const vr = sub(v, windAt(p.z)), sp = len(vr);
        if (sp > 0.05) {
          const vh = scale(vr, 1 / sp), Sr = R * w / sp;
          const Cd = Math.max(0.12, AERO.cd0 + AERO.cd1 * Sr - AERO.cdv * (sp - 50) / 25);
          const Cl = Math.min(AERO.clMax, AERO.cl * Math.pow(Math.max(Sr, 0), AERO.clp));
          let L0 = sub(UP, scale(vh, dot(UP, vh))); L0 = len(L0) > 1e-6 ? norm(L0) : UP;
          const side = norm(cross(vh, UP));
          const ldir = add(scale(L0, Math.cos(tilt)), scale(side, Math.sin(tilt)));
          const acc = add(add(scale(vr, -K * Cd * sp), scale(ldir, K * Cl * sp * sp)), v3(0, 0, -g));
          v = add(v, scale(acc, dt));
        } else v = add(v, v3(0, 0, -g * dt));
        const prev = p;
        p = add(p, scale(v, dt));
        w *= Math.exp(-AERO.decay * dt);
        t += dt; air += dt;

        // Trees: canopy slows and deflects the ball; trunks bounce it back
        if (world.trees && world.treeAt) {
          for (const tr of world.treeAt(p.x, p.y)) {
            const dx = p.x - tr.x, dy = p.y - tr.y;
            if (p.z < tr.base + tr.trunk && Math.hypot(dx, dy) < tr.tr) {
              const nn = norm(v3(dx, dy, 0)); const vn = dot(v, nn);
              if (vn < 0) { v = sub(v, scale(nn, 1.45 * vn)); v = scale(v, 0.6); w *= 0.5; hitTree = true; }
              continue;
            }
            const ez = (p.z - tr.cz) / tr.rz, er = Math.hypot(dx, dy) / tr.rx;
            if (er * er + ez * ez < 1) {
              const step = len(sub(p, prev));
              if (rng() < step * tr.dens) {
                const s = len(v) * (0.15 + 0.3 * rng());
                const a = rng() * Math.PI * 2;
                v = add(scale(norm(v), s * 0.5), v3(Math.cos(a) * s * 0.6, Math.sin(a) * s * 0.6, -s * 0.3 * rng()));
                w *= 0.3; hitTree = true;
              }
            }
          }
        }

        const zg = world.height(p.x, p.y);
        if (p.z <= zg + R && v.z < 0) {
          p = v3(p.x, p.y, zg + R);
          const sc = world.surface(p.x, p.y);
          if (!firstLand) firstLand = { x: p.x, y: p.y, t, surface: sc };
          lastSurf = sc;
          if (HAZARD(sc)) { result = 'water'; hazard = sc; rec(); break; }
          // Direct hit in the cup
          if (world.cup && Math.hypot(p.x - world.cup.x, p.y - world.cup.y) < CUP_R + 0.02 && len(v) < 12) { result = 'holed'; rec(); break; }
          const su = SURF[sc], n = world.normal(p.x, p.y);
          const vn = dot(v, n); let vt = sub(v, scale(n, vn));
          const vtl = len(vt);
          // Softer landings lose more energy when they come in steep and fast
          const e = su.e * Math.max(0.35, 1 - Math.abs(vn) / 45);
          const vnNew = -e * vn;
          // Spin-aware friction: backspin speeds up the contact patch, so friction can check or reverse the ball
          if (vtl > 1e-4) {
            const th = scale(vt, 1 / vtl);
            const slip = vtl + w * R;
            const J = su.mu * (1 + e) * Math.abs(vn);
            let vtNew, wNew;
            if (J >= (2 / 7) * Math.abs(slip)) { vtNew = (5 * vtl - 2 * w * R) / 7; wNew = -vtNew / R; }
            else { vtNew = vtl - J * Math.sign(slip); wNew = w - 2.5 * J * Math.sign(slip) / R; }
            // Turf absorbs forward speed in proportion to how hard the ball lands (the pitch mark)
            const absorb = su.soft * Math.abs(vn);
            vtNew = vtNew > 0 ? Math.max(0, vtNew - absorb) : Math.min(0, vtNew + absorb * 0.5);
            vt = scale(th, vtNew); w = Math.max(wNew, -Math.abs(vtNew) / R);
          }
          v = add(vt, scale(n, vnNew));
          bounces++;
          if (vnNew < 0.45 || bounces > 12) { mode = 'roll'; v = sub(v, scale(n, dot(v, n))); }
        }
        if (path.length === 0 || t - path[path.length - 1][0] >= 1 / 60) rec();
      } else {
        // Rolling on the surface
        const dt = 1 / 240;
        const sc = world.surface(p.x, p.y);
        lastSurf = sc;
        if (HAZARD(sc)) { result = 'water'; hazard = sc; rec(); break; }
        const su = SURF[sc], n = world.normal(p.x, p.y);
        // A rolling ball feels 5/7 of the slope's pull (the rest goes into spinning it faster)
        const gt = scale(sub(v3(0, 0, -g), scale(n, dot(v3(0, 0, -g), n))), 5 / 7);
        let sp = len(v);
        if (sp < 0.02) {
          if (len(gt) <= su.roll * su.hold * g) { v = v3(0, 0, 0); break; }
          v = add(v, scale(gt, dt));
        } else {
          // Rolling resistance, plus grass drag that grows with speed (a fast ball skips through the grass)
          const fr = scale(norm(v), -(su.roll * g + (su.drag || 0) * Math.max(0, sp - 1.8) ** 2));
          const nv = add(v, scale(add(gt, fr), dt));
          // Friction can't reverse the ball on its own
          if (dot(nv, v) <= 0 && len(gt) <= su.roll * su.hold * g) { v = v3(0, 0, 0); break; }
          v = nv;
        }
        v = sub(v, scale(n, dot(v, n)));
        const prev = p;
        p = add(p, scale(v, dt));
        p = v3(p.x, p.y, world.height(p.x, p.y) + R);
        t += dt;
        // The cup: when the ball reaches the cup's edge, it drops if its line passes close enough to the
        // centre for its speed (a ball faster than ~1.6 m/s only drops dead centre); otherwise it lips out.
        if (world.cup) {
          const cx = world.cup.x, cy = world.cup.y;
          const dx = p.x - prev.x, dy = p.y - prev.y, L2 = dx * dx + dy * dy || 1e-9;
          const u = Math.max(0, Math.min(1, ((cx - prev.x) * dx + (cy - prev.y) * dy) / L2));
          const dist = Math.hypot(cx - (prev.x + u * dx), cy - (prev.y + u * dy));
          sp = len(v);
          if (dist < CUP_R && !lipped) {
            const vh = sp > 1e-6 ? scale(v, 1 / sp) : v3(0, 0, 0);
            const miss = Math.abs(vh.x * (cy - prev.y) - vh.y * (cx - prev.x));   // closest approach of the line
            const allow = CUP_R * Math.max(0, 1 - (sp / 1.63) ** 2);
            if (miss < allow || sp < 0.25) { p = v3(cx, cy, world.height(cx, cy) - 0.05); result = 'holed'; rec(); break; }
            lipped = true;                                                       // lips out: bends away and slows
            const sgn = (vh.x * (cy - prev.y) - vh.y * (cx - prev.x)) > 0 ? -1 : 1;
            const side = v3(-vh.y * sgn, vh.x * sgn, 0);
            v = scale(norm(add(vh, scale(side, 0.6 * (1 - miss / CUP_R)))), sp * 0.8);
          }
          if (dist > CUP_R * 2) lipped = false;
        }
        if (t - path[path.length - 1][0] >= 1 / 30) rec();
      }
    }
    rec();
    const out = world.surface(p.x, p.y);
    if (result === 'rest' && out === S.OB) result = 'ob';
    return { path, end: p, result, surface: out, firstLand, hitTree, hazard, airtime: air };
  }

  return { simulate, S, SURF, CUP_R, AERO, R };
})();
if (typeof module !== 'undefined') module.exports = GolfPhysics;
