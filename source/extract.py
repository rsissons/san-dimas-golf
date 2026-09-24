# Converts the OpenStreetMap course features to local metres (x east, y north) around the course centre.
import json, math, os, collections
os.chdir(os.path.dirname(os.path.abspath(__file__)))
f = json.load(open('frame.json'))
lat0, lon0 = f['lat0'], f['lon0']
M = 111320.0
mx = math.cos(math.radians(lat0)) * M
P = lambda lat, lon: [round((lon - lon0) * mx, 1), round((lat - lat0) * M, 1)]

E = json.load(open('osm.json'))['elements']
E2 = json.load(open('osm2.json'))['elements']
course = [e for e in E if e.get('tags', {}).get('name') == 'San Dimas Canyon Golf Course'][0]
boundary = [P(p['lat'], p['lon']) for p in course['geometry']]

def inside(pt, poly):
    x, y = pt; c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c

def near_course(pt, pad):
    xs = [p[0] for p in boundary]; ys = [p[1] for p in boundary]
    return min(xs) - pad <= pt[0] <= max(xs) + pad and min(ys) - pad <= pt[1] <= max(ys) + pad

def rings(e):
    """Outer and inner rings (joined from way members for multipolygons)."""
    if e['type'] == 'way':
        return [[P(p['lat'], p['lon']) for p in e['geometry']]], []
    outer, inner = [], []
    for m in e.get('members', []):
        if 'geometry' not in m: continue
        r = [P(p['lat'], p['lon']) for p in m['geometry']]
        (inner if m.get('role') == 'inner' else outer).append(r)
    return join(outer), join(inner)

def join(parts):
    """Stitch open way segments into closed rings."""
    parts = [p[:] for p in parts]; out = []
    while parts:
        ring = parts.pop(0)
        changed = True
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

def centroid(r):
    return [sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)]

feat = collections.defaultdict(list)
holes = {}
tee_tags = collections.Counter()
for e in E:
    t = e.get('tags', {})
    g = t.get('golf')
    kind = None
    if g in ('fairway', 'green', 'bunker', 'tee', 'rough', 'driving_range'): kind = g
    elif g in ('water_hazard', 'lateral_water_hazard') or t.get('natural') == 'water': kind = 'water'
    elif g == 'cartpath': kind = 'cartpath'
    elif g == 'hole': kind = 'hole'
    if not kind: continue
    if kind == 'hole':
        line = [P(p['lat'], p['lon']) for p in e['geometry']]
        if not inside(line[len(line) // 2], boundary): continue
        holes[int(t['ref'])] = {'par': int(t['par']), 'line': line}
        continue
    if kind == 'cartpath':
        line = [P(p['lat'], p['lon']) for p in e['geometry']]
        if inside(line[len(line) // 2], boundary): feat['cartpath'].append(line)
        continue
    outer, inner = rings(e)
    if not outer or not inside(centroid(outer[0]), boundary):
        # Water just outside the fence line still matters if it touches a hole
        if not (kind == 'water' and outer and near_course(centroid(outer[0]), 0) and any(inside(p, boundary) for p in outer[0])):
            continue
    if kind == 'tee': tee_tags[tuple(sorted((k, v) for k, v in t.items() if k != 'golf'))] += 1
    for o in outer:
        item = {'o': o, 'i': [r for r in inner if inside(r[0], o)]} if inner else {'o': o}
        if kind == 'tee':
            item['ref'] = int(t['ref']) if t.get('ref', '').isdigit() else None
            item['c'] = t.get('tee')
        feat[kind].append(item)

# Scenery: roads and buildings near the course
roads, buildings = [], []
for e in E2:
    t = e.get('tags', {})
    if 'geometry' not in e: continue
    pts = [P(p['lat'], p['lon']) for p in e['geometry']]
    if 'building' in t and near_course(centroid(pts), 120):
        buildings.append({'o': pts, 'h': 4.5 if 'building:levels' not in t else 3.2 * float(t['building:levels'].split(';')[0]) })
    elif t.get('highway') in ('residential', 'secondary', 'tertiary', 'primary') and any(near_course(p, 80) for p in pts):
        roads.append({'w': 12 if t['highway'] in ('secondary', 'primary') else 9, 'p': pts, 'name': t.get('name', '')})

print('holes', sorted(holes), 'features', {k: len(v) for k, v in feat.items()}, 'roads', len(roads), 'buildings', len(buildings))
print('tee tags', tee_tags.most_common(6))
json.dump({'boundary': boundary, 'holes': holes, 'features': feat, 'roads': roads, 'buildings': buildings,
           'origin': [lat0, lon0]}, open('course.json', 'w'))
print('bytes', os.path.getsize('course.json'))
