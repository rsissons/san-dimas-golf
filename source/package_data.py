# Builds data.js: terrain grids, course features, and per-hole tee/pin positions from the scorecard.
import json, math, os, base64, struct
os.chdir(os.path.dirname(os.path.abspath(__file__)))
c = json.load(open('course.json'))
dem = json.load(open('dem.json'))
bg = json.load(open('bg.json'))
YD = 0.9144

CARD = {
    'par':   [4, 3, 5, 4, 3, 5, 3, 4, 5, 3, 4, 5, 4, 4, 4, 3, 5, 4],
    'hcp':   [9, 17, 5, 1, 3, 15, 7, 11, 13, 16, 8, 14, 6, 2, 10, 12, 18, 4],
    'hcpRed': [11, 13, 1, 7, 15, 5, 17, 9, 3, 18, 12, 2, 6, 4, 10, 16, 8, 14],
    'blue':  [341, 145, 552, 393, 208, 452, 209, 351, 472, 198, 377, 462, 413, 416, 380, 178, 461, 392],
    'white': [323, 131, 523, 367, 176, 440, 181, 334, 449, 173, 351, 433, 394, 377, 362, 161, 446, 383],
    'red':   [300, 115, 483, 339, 139, 417, 120, 304, 413, 149, 332, 395, 337, 310, 353, 112, 428, 329],
}
RATING = {'blue': '71.7 / 126', 'white': 'M 70.0 / 122 · W 75.2 / 132', 'red': 'M 66.5 / 109 · W 72.5 / 128'}

def d(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])
def cen(r): return [sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)]
def inside(pt, poly):
    x, y = pt; ins = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: ins = not ins
    return ins

def edge_dist(p, poly):
    m = 1e9
    for i in range(len(poly)):
        a, b = poly[i - 1], poly[i]; dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy or 1e-9
        u = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        m = min(m, math.hypot(p[0] - a[0] - u * dx, p[1] - a[1] - u * dy))
    return m

def path_to_pin(pt, line):
    """Distance from a point to the pin along the hole line: to the nearest point on the line, then along it."""
    best = None
    for j in range(len(line) - 1):
        a, b = line[j], line[j + 1]; L2 = d(a, b) ** 2 or 1e-9
        u = max(0, min(1, ((pt[0] - a[0]) * (b[0] - a[0]) + (pt[1] - a[1]) * (b[1] - a[1])) / L2))
        q = [a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1])]
        rest = d(q, b) + sum(d(line[k], line[k + 1]) for k in range(j + 1, len(line) - 1))
        cand = d(pt, q) + rest
        if best is None or d(pt, q) < best[0]: best = (d(pt, q), cand)
    return best[1]

def along_from_pin(line, dist):
    """Point on the hole line `dist` metres back from the pin (extends past the tee end if needed)."""
    rem = dist
    for j in range(len(line) - 1, 0, -1):
        a, b = line[j], line[j - 1]; seg = d(a, b)
        if rem <= seg or j == 1:
            t = rem / seg
            return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
        rem -= seg

holes = []
for n in range(1, 19):
    h = c['holes'][str(n)]; line = h['line']; pin = line[-1]
    tees = {}
    notes = []
    for col in ('blue', 'white', 'red'):
        card_m = CARD[col][n - 1] * YD
        polys = [t for t in c['features']['tee'] if t.get('ref') == n and t.get('c') == col]
        pos = None
        if polys:
            ctr = cen(polys[0]['o'])
            if abs(path_to_pin(ctr, line) - card_m) <= 0.12 * card_m: pos = ctr
        if pos is None:
            dd = card_m
            pos = along_from_pin(line, dd)
            # Stay inside the course and at least 6 m clear of any building (the clubhouse sits behind 1 tee)
            def blocked(p):
                return (not inside(p, c['boundary'])) or any(inside(p, bl['o']) or edge_dist(p, bl['o']) < 6 for bl in c['buildings'] if abs(bl['o'][0][0] - p[0]) < 80 and abs(bl['o'][0][1] - p[1]) < 80)
            while blocked(pos) and dd > 30:
                dd -= 2; pos = along_from_pin(line, dd)
            notes.append(col)
        # Aim line from this tee: the tee, then the hole line's later vertices
        tees[col] = [round(pos[0], 1), round(pos[1], 1)]
    holes.append({'n': n, 'par': CARD['par'][n - 1], 'hcp': CARD['hcp'][n - 1], 'hcpRed': CARD['hcpRed'][n - 1],
                  'yards': {k: CARD[k][n - 1] for k in ('blue', 'white', 'red')},
                  'line': line, 'pin': pin, 'tees': tees})
    measured = {k: round(path_to_pin(v, line) / YD) for k, v in tees.items()}
    print(f'{n:2} par {CARD["par"][n-1]} measured {measured} card', {k: CARD[k][n - 1] for k in ("blue", "white", "red")}, 'placed on line:', notes)

def shape_surface(dem, poly, max_slope, keep, band):
    """Rebuild the ground under a green or tee: the real tilt capped at max_slope, `keep` of the real
    contours, blended back into the natural ground over `band` metres outside the edge."""
    nx, x0, y0, st, z = dem['nx'], dem['x0'], dem['y0'], dem['step'], dem['z']
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    i0 = max(0, int((min(xs) - band - x0) / st)); i1 = min(nx - 1, int((max(xs) + band - x0) / st) + 1)
    j0 = max(0, int((min(ys) - band - y0) / st)); j1 = min(dem['ny'] - 1, int((max(ys) + band - y0) / st) + 1)
    pts = []
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            p = (x0 + i * st, y0 + j * st)
            if inside(p, poly): pts.append((p[0], p[1], z[j * nx + i]))
    if len(pts) < 3: return
    # Least-squares plane z = a + b(x - cx) + c(y - cy)
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts); cz = sum(p[2] for p in pts) / len(pts)
    sxx = sum((p[0] - cx) ** 2 for p in pts); syy = sum((p[1] - cy) ** 2 for p in pts); sxy = sum((p[0] - cx) * (p[1] - cy) for p in pts)
    sxz = sum((p[0] - cx) * (p[2] - cz) for p in pts); syz = sum((p[1] - cy) * (p[2] - cz) for p in pts)
    det = sxx * syy - sxy * sxy or 1e-9
    b = (sxz * syy - syz * sxy) / det; c = (syz * sxx - sxz * sxy) / det
    s = math.hypot(b, c); k = min(1, max_slope / s) if s > 0 else 1
    plane = lambda x, y: cz + b * (x - cx) + c * (y - cy)
    shaped = lambda x, y, zz: cz + k * (b * (x - cx) + c * (y - cy)) + keep * (zz - plane(x, y))
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            p = (x0 + i * st, y0 + j * st); idx = j * nx + i; zz = z[idx]
            if inside(p, poly): z[idx] = shaped(p[0], p[1], zz)
            else:
                d = edge_dist(p, poly)
                if d < band:
                    w = 0.5 * (1 + math.cos(math.pi * d / band))     # smooth fall-off to the natural ground
                    z[idx] = w * shaped(p[0], p[1], zz) + (1 - w) * zz
    return s, s * k

for g in c['features']['green']:
    r = shape_surface(dem, g['o'], 0.025, 0.25, 7)
    if r: print('green slope %.1f%% -> %.1f%%' % (r[0] * 100, r[1] * 100))
for t in c['features']['tee']:
    shape_surface(dem, t['o'], 0.01, 0.0, 4)
for h in holes:
    for col, p in h['tees'].items():
        pad = [[p[0] + 3.2 * math.cos(a / 8 * math.pi), p[1] + 3.2 * math.sin(a / 8 * math.pi)] for a in range(16)]
        shape_surface(dem, pad, 0.01, 0.0, 3)

def pack_grid(g, res):
    z = [v for v in g['z']]
    zmin = min(z)
    raw = b''.join(struct.pack('<H', max(0, min(65535, round((v - zmin) / res)))) for v in z)
    return {'x0': round(g['x0'], 2), 'y0': round(g['y0'], 2), 'step': g['step'], 'nx': g['nx'], 'ny': g['ny'],
            'zmin': round(zmin, 3), 'res': res, 'b64': base64.b64encode(raw).decode()}

data = {
    'name': 'San Dimas Canyon Golf Course', 'origin': c['origin'], 'rating': RATING,
    'boundary': c['boundary'], 'features': c['features'], 'roads': c['roads'], 'buildings': c['buildings'],
    'holes': holes, 'dem': pack_grid(dem, 0.01), 'bg': pack_grid(bg, 0.1),
}
js = 'const COURSE = ' + json.dumps(data, separators=(',', ':')) + ';\n'
open('data.js', 'w').write(js)
print('data.js', round(len(js) / 1024), 'KB')
