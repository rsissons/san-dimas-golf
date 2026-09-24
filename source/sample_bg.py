# Samples USGS 3DEP bare-earth elevation on a regular grid over the course (plus a margin).
# Resumable: finished batches are cached in dem_parts/.
import json, math, os, time, urllib.parse, urllib.request

os.chdir(os.path.dirname(os.path.abspath(__file__)))
f = json.load(open('frame.json'))
lat0, lon0 = f['lat0'], f['lon0']
M = 111320.0
mx = math.cos(math.radians(lat0)) * M
s, w, n, e = f['bbox']
PAD, STEP = 1800.0, 40.0
x0 = (w - lon0) * mx - PAD; x1 = (e - lon0) * mx + PAD
y0 = (s - lat0) * M - PAD; y1 = (n - lat0) * M + PAD
nx = int((x1 - x0) / STEP) + 1
ny = int((y1 - y0) / STEP) + 1
print('grid', nx, 'x', ny, '=', nx * ny, flush=True)
pts = [(lon0 + (x0 + i * STEP) / mx, lat0 + (y0 + j * STEP) / M) for j in range(ny) for i in range(nx)]
os.makedirs('bg_parts', exist_ok=True)
URL = 'https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/getSamples'
B = 1000
batches = (len(pts) + B - 1) // B
for b in range(batches):
    out = f'bg_parts/{b:04d}.json'
    if os.path.exists(out):
        continue
    chunk = pts[b * B:(b + 1) * B]
    body = urllib.parse.urlencode({
        'geometry': json.dumps({'points': [[round(x, 7), round(y, 7)] for x, y in chunk], 'spatialReference': {'wkid': 4326}}),
        'geometryType': 'esriGeometryMultipoint', 'returnFirstValueOnly': 'true', 'f': 'json',
    }).encode()
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL, data=body), timeout=120) as r:
                res = json.load(r)
            vals = {smp['locationId']: float(smp['value']) for smp in res['samples'] if smp.get('value') not in (None, 'NoData')}
            if len(vals) < len(chunk) * 0.95:
                raise RuntimeError(f'only {len(vals)} of {len(chunk)} values')
            json.dump([vals.get(k) for k in range(len(chunk))], open(out, 'w'))
            break
        except Exception as ex:
            print('batch', b, 'attempt', attempt, 'failed:', ex, flush=True)
            time.sleep(5 * (attempt + 1))
    else:
        print('GAVE UP on batch', b, flush=True)
        raise SystemExit(1)
    if b % 10 == 0:
        print('batch', b + 1, 'of', batches, flush=True)
vals = []
for b in range(batches):
    vals += json.load(open(f'bg_parts/{b:04d}.json'))
missing = sum(v is None for v in vals)
json.dump({'x0': x0, 'y0': y0, 'step': STEP, 'nx': nx, 'ny': ny, 'z': vals}, open('bg.json', 'w'))
print('DONE', len(vals), 'samples, missing', missing, 'min', min(v for v in vals if v is not None), 'max', max(v for v in vals if v is not None), flush=True)
