# Builds one course's game data from its config (courses/<id>/course.json):
#   fetch    OpenStreetMap: the course features (Overpass) and the scenery around it (roads, buildings)
#   dem      USGS 3DEP 1 m bare-earth elevation: a 4 m grid over the course and a 40 m grid for the hills around it
#   extract  course features in local metres (x east, y north) around the course centre -> raw/course.json
#   package  tees from the scorecard, reshaped greens and tees, packed terrain -> courses/<id>/data.js
#   all      every step; finished downloads are cached in raw/ and reused
# Usage: python source/course_tool.py <course-id> [fetch|dem|extract|package|all]
import base64, collections, json, math, os, struct, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
M = 111320.0
YD = 0.9144
UA = {'User-Agent': 'CanyonGolf/1.0 (github.com/rsissons/san-dimas-golf)'}


def load(p): return json.load(open(p, encoding='utf-8'))
def save(p, o): json.dump(o, open(p, 'w', encoding='utf-8'))


# ---------------------------------------------------------------- Fetch (OpenStreetMap)
def overpass(query):
    body = urllib.parse.urlencode({'data': query}).encode()
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request('https://overpass-api.de/api/interpreter', data=body, headers=UA), timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as ex:
            if 400 <= ex.code < 500 and ex.code != 429: raise SystemExit(f'Overpass rejected the query ({ex.code}): {ex.read()[:300]}')
            print('overpass attempt', attempt, 'failed:', ex, flush=True)
            time.sleep(15 * (attempt + 1))
        except Exception as ex:
            print('overpass attempt', attempt, 'failed:', ex, flush=True)
            time.sleep(15 * (attempt + 1))
    raise SystemExit('Overpass kept failing')


def fetch(cfg, raw):
    osm = cfg['osm']
    if 'way' in osm:
        area = f"way({osm['way']});map_to_area->.c;"
    else:
        raise SystemExit('fetch needs "osm": {"way": id} (older courses were fetched by name; their raw/osm.json is kept)')
    if not os.path.exists(os.path.join(raw, 'osm.json')):
        q = (f"[out:json][timeout:120];way({osm['way']});out geom;{area}"
             "(nwr(area.c)[golf];nwr(area.c)[natural=water];way(area.c)[waterway];nwr(area.c)[leisure=golf_course];);out geom;")
        save(os.path.join(raw, 'osm.json'), overpass(q))
        print('osm.json saved', flush=True)
    E = load(os.path.join(raw, 'osm.json'))['elements']
    c = next(e for e in E if e['type'] == 'way' and e['id'] == osm['way'])
    lats = [p['lat'] for p in c['geometry']]; lons = [p['lon'] for p in c['geometry']]
    s, w, n, e = min(lats), min(lons), max(lats), max(lons)
    if not os.path.exists(os.path.join(raw, 'frame.json')):
        save(os.path.join(raw, 'frame.json'), {'lat0': round((s + n) / 2, 6), 'lon0': round((w + e) / 2, 6), 'bbox': [s, w, n, e]})
    if not os.path.exists(os.path.join(raw, 'power.json')):
        pad = 0.006
        save(os.path.join(raw, 'power.json'), overpass(f'[out:json][timeout:120];(nwr[power]({s - pad},{w - pad},{n + pad},{e + pad}););out geom;'))
        print('power.json saved', flush=True)
    if not os.path.exists(os.path.join(raw, 'osm2.json')):
        pad = 0.004
        bb = f'{s - pad},{w - pad},{n + pad},{e + pad}'
        q = f'[out:json][timeout:120];(way[building]({bb});way[highway]({bb}););out geom;'
        save(os.path.join(raw, 'osm2.json'), overpass(q))
        print('osm2.json saved', flush=True)


# ---------------------------------------------------------------- Elevation (USGS 3DEP)
def sample_grid(raw, name, pad, step):
    out_path = os.path.join(raw, name + '.json')
    if os.path.exists(out_path): return
    f = load(os.path.join(raw, 'frame.json'))
    lat0, lon0 = f['lat0'], f['lon0']; mx = math.cos(math.radians(lat0)) * M
    s, w, n, e = f['bbox']
    x0 = (w - lon0) * mx - pad; x1 = (e - lon0) * mx + pad
    y0 = (s - lat0) * M - pad; y1 = (n - lat0) * M + pad
    nx = int((x1 - x0) / step) + 1; ny = int((y1 - y0) / step) + 1
    pts = [(lon0 + (x0 + i * step) / mx, lat0 + (y0 + j * step) / M) for j in range(ny) for i in range(nx)]
    parts = os.path.join(raw, name + '_parts'); os.makedirs(parts, exist_ok=True)
    url = 'https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/getSamples'
    B = 1000; batches = (len(pts) + B - 1) // B
    print(name, 'grid', nx, 'x', ny, '=', nx * ny, 'samples in', batches, 'requests', flush=True)
    for b in range(batches):
        part = os.path.join(parts, f'{b:04d}.json')
        if os.path.exists(part): continue
        chunk = pts[b * B:(b + 1) * B]
        body = urllib.parse.urlencode({
            'geometry': json.dumps({'points': [[round(x, 7), round(y, 7)] for x, y in chunk], 'spatialReference': {'wkid': 4326}}),
            'geometryType': 'esriGeometryMultipoint', 'returnFirstValueOnly': 'true', 'f': 'json'}).encode()
        for attempt in range(6):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=UA), timeout=120) as r:
                    res = json.load(r)
                vals = {smp['locationId']: float(smp['value']) for smp in res['samples'] if smp.get('value') not in (None, 'NoData')}
                if len(vals) < len(chunk) * 0.95: raise RuntimeError(f'only {len(vals)} of {len(chunk)} values')
                save(part, [vals.get(k) for k in range(len(chunk))])
                break
            except Exception as ex:
                print(name, 'batch', b, 'attempt', attempt, 'failed:', ex, flush=True)
                time.sleep(5 * (attempt + 1))
        else:
            raise SystemExit(f'gave up on {name} batch {b}')
    vals = []
    for b in range(batches): vals += load(os.path.join(parts, f'{b:04d}.json'))
    save(out_path, {'x0': x0, 'y0': y0, 'step': step, 'nx': nx, 'ny': ny, 'z': vals})
    print(name, 'done, missing', sum(v is None for v in vals), flush=True)


# ---------------------------------------------------------------- Geometry helpers
def inside(pt, poly):
    x, y = pt; c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c


def d(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])
def cen(r): return [sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)]


def edge_dist(p, poly):
    m = 1e9
    for i in range(len(poly)):
        a, b = poly[i - 1], poly[i]; dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy or 1e-9
        u = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        m = min(m, math.hypot(p[0] - a[0] - u * dx, p[1] - a[1] - u * dy))
    return m


def join(parts):
    """Stitch open way segments into closed rings."""
    parts = [p[:] for p in parts]; out = []
    while parts:
        ring = parts.pop(0); changed = True
        while ring[0] != ring[-1] and changed:
            changed = False
            for i, p in enumerate(parts):
                if p[0] == ring[-1]: ring += p[1:]
                elif p[-1] == ring[-1]: ring += p[::-1][1:]
                elif p[-1] == ring[0]: ring = p[:-1] + ring
                elif p[0] == ring[0]: ring = p[::-1][:-1] + ring
                else: continue
                parts.pop(i); changed = True; break
        out.append(ring)
    return out


# ---------------------------------------------------------------- Extract (OSM -> local metres)
def extract(cfg, raw):
    f = load(os.path.join(raw, 'frame.json'))
    lat0, lon0 = f['lat0'], f['lon0']; mx = math.cos(math.radians(lat0)) * M
    P = lambda lat, lon: [round((lon - lon0) * mx, 1), round((lat - lat0) * M, 1)]
    E = load(os.path.join(raw, 'osm.json'))['elements']
    E2 = load(os.path.join(raw, 'osm2.json'))['elements']
    osm = cfg['osm']
    if 'way' in osm: course = next(e for e in E if e['type'] == 'way' and e['id'] == osm['way'])
    else: course = [e for e in E if e.get('tags', {}).get('name') == osm['name']][0]
    boundary = [P(p['lat'], p['lon']) for p in course['geometry']]

    def near_course(pt, pad):
        xs = [p[0] for p in boundary]; ys = [p[1] for p in boundary]
        return min(xs) - pad <= pt[0] <= max(xs) + pad and min(ys) - pad <= pt[1] <= max(ys) + pad

    def rings(e):
        if e['type'] == 'way': return [[P(p['lat'], p['lon']) for p in e['geometry']]], []
        outer, inner = [], []
        for m in e.get('members', []):
            if 'geometry' not in m: continue
            r = [P(p['lat'], p['lon']) for p in m['geometry']]
            (inner if m.get('role') == 'inner' else outer).append(r)
        return join(outer), join(inner)

    feat = collections.defaultdict(list); holes = {}
    for e in E:
        t = e.get('tags', {}); g = t.get('golf'); kind = None
        if e is course: continue
        if g in ('fairway', 'green', 'bunker', 'tee', 'rough', 'driving_range'): kind = g
        elif g in ('water_hazard', 'lateral_water_hazard') or t.get('natural') == 'water': kind = 'water'
        elif g == 'cartpath': kind = 'cartpath'
        elif g == 'hole': kind = 'hole'
        elif t.get('waterway') in ('ditch', 'drain') and cfg.get('style', {}).get('ditches'): kind = 'ditch'
        if not kind or 'geometry' not in e and e['type'] == 'way': continue
        if kind == 'hole':
            line = [P(p['lat'], p['lon']) for p in e['geometry']]
            if not inside(line[len(line) // 2], boundary): continue
            holes[int(t['ref'])] = {'par': int(t['par']), 'line': line}
            continue
        if kind in ('cartpath', 'ditch'):
            if e['type'] != 'way': continue
            line = [P(p['lat'], p['lon']) for p in e['geometry']]
            if any(inside(p, boundary) for p in line): feat[kind].append(line)
            continue
        outer, inner = rings(e)
        if not outer or not inside(cen(outer[0]), boundary):
            if not (kind == 'water' and outer and near_course(cen(outer[0]), 0) and any(inside(p, boundary) for p in outer[0])):
                continue
        for o in outer:
            item = {'o': o, 'i': [r for r in inner if inside(r[0], o)]} if inner else {'o': o}
            if kind == 'tee':
                item['ref'] = int(t['ref']) if t.get('ref', '').isdigit() else None
                item['c'] = t.get('tee')
            feat[kind].append(item)
    for k in ('fairway', 'green', 'bunker', 'tee', 'water', 'cartpath'): feat.setdefault(k, [])

    roads, buildings = [], []
    for e in E2:
        t = e.get('tags', {})
        if 'geometry' not in e: continue
        pts = [P(p['lat'], p['lon']) for p in e['geometry']]
        if 'building' in t and near_course(cen(pts), 120):
            buildings.append({'o': pts, 'h': 4.5 if 'building:levels' not in t else 3.2 * float(t['building:levels'].split(';')[0])})
        elif t.get('highway') in ('residential', 'secondary', 'tertiary', 'primary') and any(near_course(p, 80) for p in pts):
            roads.append({'w': 12 if t['highway'] in ('secondary', 'primary') else 9, 'p': pts, 'name': t.get('name', '')})
    missing = [n for n in range(1, 19) if n not in holes]
    print('holes', len(holes), 'missing', missing, 'features', {k: len(v) for k, v in feat.items()}, 'roads', len(roads), 'buildings', len(buildings))
    if missing: raise SystemExit(f'OpenStreetMap has no golf=hole line for holes {missing}; map them (or add them to the config) first')
    save(os.path.join(raw, 'course.json'), {'boundary': boundary, 'holes': holes, 'features': feat, 'roads': roads, 'buildings': buildings, 'origin': [lat0, lon0]})


# ---------------------------------------------------------------- Package (scorecard, tees, shaped ground)
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
                dd = edge_dist(p, poly)
                if dd < band:
                    w = 0.5 * (1 + math.cos(math.pi * dd / band))
                    z[idx] = w * shaped(p[0], p[1], zz) + (1 - w) * zz
    return s, s * k


def place_landmarks(cfg, c, holes):
    """Things the map doesn't have, described like a golfer would: "a tree 60 yd short of the green, middle of
    the fairway". Each landmark: hole, kind (tree | box), from (a tee colour, or "green" for the green's front
    edge), yards, and across (-1 left edge of the fairway, 0 middle, +1 right edge, looking at the green)."""
    out = []
    for gi, lm0 in enumerate(cfg.get('landmarks', [])):
        for yards in (lm0['yards'] if isinstance(lm0['yards'], list) else [lm0['yards']]):
            lm = {**lm0, 'yards': yards}
            h = holes[lm['hole'] - 1]; line = h['line']; pin = line[-1]
            if lm['from'] == 'green':
                g = next((gr['o'] for gr in c['features']['green'] if inside(pin, gr['o'])), None)
                front = 0.0
                while g and front < 80 and inside(along_from_pin(line, front), g): front += 0.5
                back = front + lm['yards'] * YD
            else:
                back = path_to_pin(h['tees'][lm['from']], line) - lm['yards'] * YD
            p = along_from_pin(line, back); q = along_from_pin(line, back + 2)
            dx, dy = p[0] - q[0], p[1] - q[1]; L = math.hypot(dx, dy) or 1
            nl = (-dy / L, dx / L)                                   # to the left, looking at the green
            fws = [f['o'] for f in c['features']['fairway']]
            onfw = lambda t: any(inside((p[0] + nl[0] * t, p[1] + nl[1] * t), f) for f in fws)
            left = right = None
            if onfw(0):
                left = 0.0
                while left < 60 and onfw(left + 0.5): left += 0.5
                right = 0.0
                while right < 60 and onfw(-(right + 0.5)): right += 0.5
                mid = (left - right) / 2; half = (left + right) / 2
                t = mid - lm.get('across', 0) * half
            else:
                t = -lm.get('across', 0) * 15                          # no fairway there: 15 m either side of the line
            if left is not None and abs(lm.get('across', 0)) > 1:          # past the fairway edge: measure from the edge
                edge = left if lm['across'] < 0 else -right
                t = edge - (lm['across'] - (1 if lm['across'] > 0 else -1)) * half
            pos = [round(p[0] + nl[0] * t, 1), round(p[1] + nl[1] * t, 1)]
            out.append({'hole': lm['hole'], 'kind': lm['kind'], 'x': pos[0], 'y': pos[1], 'group': gi, 'note': lm.get('note', '')})
            print(f"landmark hole {lm['hole']} {lm['kind']}: {lm['yards']} yd from {lm['from']}, across {lm.get('across', 0)}"
                  f" -> {round(path_to_pin(pos, line) / YD)} yd to the pin" + (f", fairway {round((left + right) / YD)} yd wide there" if left is not None else ', not on a fairway'))
    return out


def power_lines(raw, lat0, lon0, dem, landmarks):
    """Transmission towers and their spans from OpenStreetMap (raw/power.json), plus wooden poles placed as
    landmarks (wired pole to pole). Kept within about 2 km of the course."""
    mx = math.cos(math.radians(lat0)) * M
    P = lambda la, lo: [round((lo - lon0) * mx, 1), round((la - lat0) * M, 1)]
    cx = dem['x0'] + (dem['nx'] - 1) * dem['step'] / 2; cy = dem['y0'] + (dem['ny'] - 1) * dem['step'] / 2
    near = lambda p: math.hypot(p[0] - cx, p[1] - cy) < 2200
    towers, poles, spans = {}, {}, []
    path = os.path.join(raw, 'power.json')
    if os.path.exists(path):
        E = load(path)['elements']
        for e in E:
            if e['type'] == 'node' and e.get('tags', {}).get('power') in ('tower', 'pole'):
                p = P(e['lat'], e['lon'])
                if near(p): (towers if e['tags']['power'] == 'tower' else poles)[e['id']] = p
        for e in E:
            t = e.get('tags', {})
            if e['type'] != 'way' or t.get('power') not in ('line', 'minor_line'): continue
            sup = [n for n in e['nodes'] if n in towers or n in poles]
            for a, b in zip(sup, sup[1:]):
                pa = towers.get(a) or poles.get(a); pb = towers.get(b) or poles.get(b)
                spans.append({'a': pa, 'b': pb, 'kind': 'tower' if a in towers and b in towers else 'pole'})
    by_group = collections.defaultdict(list)
    for lm in landmarks:
        if lm['kind'] == 'pole': by_group[lm['group']].append([lm['x'], lm['y']])
    lm_poles = [p for g in by_group.values() for p in g]
    for g in by_group.values():
        for a, b in zip(g, g[1:]): spans.append({'a': a, 'b': b, 'kind': 'pole'})
    if not (towers or poles or lm_poles): return None
    print('power:', len(towers), 'towers,', len(poles) + len(lm_poles), 'poles,', len(spans), 'spans')
    return {'towers': list(towers.values()), 'poles': list(poles.values()) + lm_poles, 'spans': spans}


def arroyo_grid(dem, boundary, min_depth=2.5, min_cells=12, radius=6):
    """Dry creek beds (arroyos) found in the elevation: ground more than 1.2 m below the average of the 24 m
    around it, in channels at least `min_depth` deep and `min_cells` grid cells big, inside the course.
    Returns an 8-bit depth grid on the elevation grid (0 = no arroyo; the game treats > 16 as arroyo)."""
    import numpy as np
    from numpy.lib.stride_tricks import sliding_window_view
    nx, ny = dem['nx'], dem['ny']
    Z = np.array([v if v is not None else np.nan for v in dem['z']], dtype=float).reshape(ny, nx)
    Z = np.where(np.isnan(Z), np.nanmean(Z), Z)
    pad = np.pad(Z, radius, mode='edge')
    tpi = Z - sliding_window_view(pad, (2 * radius + 1, 2 * radius + 1)).mean(axis=(2, 3))
    ins = np.zeros((ny, nx), bool)
    for j in range(ny):
        for i in range(nx):
            ins[j, i] = inside((dem['x0'] + i * dem['step'], dem['y0'] + j * dem['step']), boundary)
    mask = (tpi < -1.2) & ins
    keep = np.zeros_like(mask); seen = np.zeros_like(mask); comps = 0
    for j in range(ny):
        for i in range(nx):
            if not mask[j, i] or seen[j, i]: continue
            stack, cells = [(j, i)], []; seen[j, i] = True
            while stack:
                a, b = stack.pop(); cells.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                    q, r = a + da, b + db
                    if 0 <= q < ny and 0 <= r < nx and mask[q, r] and not seen[q, r]: seen[q, r] = True; stack.append((q, r))
            if len(cells) >= min_cells and min(tpi[a, b] for a, b in cells) <= -min_depth:
                comps += 1
                for a, b in cells: keep[a, b] = True
    val = np.where(keep, np.clip(np.round((-tpi - 0.8) * 40), 0, 255), 0).astype(np.uint8)
    print('arroyos:', comps, 'channels,', int(keep.sum()), 'cells,', round(int(keep.sum()) * dem['step'] ** 2), 'm2')
    return {'x0': round(dem['x0'], 2), 'y0': round(dem['y0'], 2), 'step': dem['step'], 'nx': nx, 'ny': ny,
            'b64': base64.b64encode(val.tobytes()).decode()}


def pack_grid(g, res):
    z = list(g['z']); zmin = min(z)
    raw = b''.join(struct.pack('<H', max(0, min(65535, round((v - zmin) / res)))) for v in z)
    return {'x0': round(g['x0'], 2), 'y0': round(g['y0'], 2), 'step': g['step'], 'nx': g['nx'], 'ny': g['ny'],
            'zmin': round(zmin, 3), 'res': res, 'b64': base64.b64encode(raw).decode()}


def package(cfg, raw, out_dir):
    c = load(os.path.join(raw, 'course.json'))
    dem = load(os.path.join(raw, 'dem.json')); bg = load(os.path.join(raw, 'bg.json'))
    arroyo = arroyo_grid(dem, c['boundary']) if cfg.get('style', {}).get('arroyos') else None
    card = cfg['card']; tee_keys = [t['k'] for t in cfg['tees']]
    holes = []
    for n in range(1, 19):
        h = c['holes'][str(n)]; line = h['line']; pin = line[-1]
        if h['par'] != card['par'][n - 1]: print(f'  note: hole {n} is par {h["par"]} on the map, {card["par"][n - 1]} on the card (the card wins)')
        tees = {}; notes = []
        for col in tee_keys:
            card_m = card['yards'][col][n - 1] * YD
            polys = [t for t in c['features']['tee'] if t.get('ref') == n and t.get('c') == col]
            pos = None
            if polys:
                ctr = cen(polys[0]['o'])
                if abs(path_to_pin(ctr, line) - card_m) <= 0.12 * card_m: pos = ctr
            if pos is None:
                dd = card_m; pos = along_from_pin(line, dd)
                # Stay inside the course and at least 6 m clear of any building
                def blocked(p):
                    return (not inside(p, c['boundary'])) or any(inside(p, bl['o']) or edge_dist(p, bl['o']) < 6 for bl in c['buildings'] if abs(bl['o'][0][0] - p[0]) < 80 and abs(bl['o'][0][1] - p[1]) < 80)
                while blocked(pos) and dd > 30:
                    dd -= 2; pos = along_from_pin(line, dd)
                notes.append(col)
            tees[col] = [round(pos[0], 1), round(pos[1], 1)]
        hole = {'n': n, 'par': card['par'][n - 1], 'hcp': card['hcp'][n - 1], 'hcpRed': card['hcpRed'][n - 1],
                'yards': {k: card['yards'][k][n - 1] for k in tee_keys}, 'line': line, 'pin': pin, 'tees': tees}
        par_by = {k: v[str(n)] for k, v in card.get('parBy', {}).items() if str(n) in v}
        if par_by: hole['parBy'] = par_by
        holes.append(hole)
        measured = {k: round(path_to_pin(v, line) / YD) for k, v in tees.items()}
        print(f'{n:2} par {card["par"][n - 1]} measured {measured} card', {k: card['yards'][k][n - 1] for k in tee_keys}, 'placed on line:', notes)

    for g in c['features']['green']:
        r = shape_surface(dem, g['o'], 0.025, 0.25, 7)
        if r: print('green slope %.1f%% -> %.1f%%' % (r[0] * 100, r[1] * 100))
    for t in c['features']['tee']: shape_surface(dem, t['o'], 0.01, 0.0, 4)
    for h in holes:
        for p in h['tees'].values():
            pad = [[p[0] + 3.2 * math.cos(a / 8 * math.pi), p[1] + 3.2 * math.sin(a / 8 * math.pi)] for a in range(16)]
            shape_surface(dem, pad, 0.01, 0.0, 3)

    meta = {k: cfg[k] for k in ('id', 'title', 'short', 'city', 'tees', 'dailyTee', 'style') if k in cfg}
    data = {'name': cfg['name'], 'origin': c['origin'], 'rating': cfg['rating'], **meta,
            'boundary': c['boundary'], 'features': c['features'], 'roads': c['roads'], 'buildings': c['buildings'],
            'holes': holes, 'dem': pack_grid(dem, 0.01), 'bg': pack_grid(bg, 0.1)}
    if arroyo: data['arroyo'] = arroyo
    marks = place_landmarks(cfg, c, holes)
    if marks: data['landmarks'] = [m for m in marks if m['kind'] != 'pole']
    power = power_lines(raw, c['origin'][0], c['origin'][1], dem, marks)
    if power: data['power'] = power
    js = 'window.COURSE = ' + json.dumps(data, separators=(',', ':')) + ';\n'
    open(os.path.join(out_dir, 'data.js'), 'w', encoding='utf-8').write(js)
    print('data.js', round(len(js) / 1024), 'KB')


if __name__ == '__main__':
    cid = sys.argv[1]; step = sys.argv[2] if len(sys.argv) > 2 else 'all'
    cdir = os.path.join(ROOT, 'courses', cid); raw = os.path.join(cdir, 'raw'); os.makedirs(raw, exist_ok=True)
    cfg = load(os.path.join(cdir, 'course.json'))
    if step in ('fetch', 'all'): fetch(cfg, raw)
    if step in ('dem', 'all'):
        sample_grid(raw, 'dem', 60.0, 4.0)
        sample_grid(raw, 'bg', 1800.0, 40.0)
    if step in ('extract', 'all'): extract(cfg, raw)
    if step in ('package', 'all'): package(cfg, raw, cdir)
