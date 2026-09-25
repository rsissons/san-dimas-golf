# Builds the site in site/: the game page (engine, physics, sounds, leaderboard settings and the course list)
# and one data file per course (site/courses/<id>.js, made by course_tool.py). Every folder in courses/ that
# has a data.js becomes a course in the lobby's course picker; add "order" to a course.json to sort them.
import base64, glob, hashlib, json, os, shutil
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.join(here, '..')
site = os.path.join(root, 'site')
src = open(os.path.join(here, 'game_src.html'), encoding='utf-8').read()
phys = open(os.path.join(here, 'physics.js'), encoding='utf-8').read()

# The courses
os.makedirs(os.path.join(site, 'courses'), exist_ok=True)
courses = []
for cfg_path in glob.glob(os.path.join(root, 'courses', '*', 'course.json')):
    cdir = os.path.dirname(cfg_path); data_path = os.path.join(cdir, 'data.js')
    if not os.path.exists(data_path): continue
    cfg = json.load(open(cfg_path, encoding='utf-8'))
    data = open(data_path, 'rb').read()
    shutil.copyfile(data_path, os.path.join(site, 'courses', cfg['id'] + '.js'))
    courses.append({'id': cfg['id'], 'title': cfg['title'], 'short': cfg['short'], 'city': cfg['city'],
                    'v': hashlib.sha1(data).hexdigest()[:10], 'order': cfg.get('order', 100 if cfg['id'] != 'san-dimas' else 0)})
courses.sort(key=lambda c: (c.pop('order'), c['title']))
listing = 'window.COURSES = ' + json.dumps(courses) + ';'

# supabase.json holds the project URL and the publishable (anon) key, which are public by design
cfg_path = os.path.join(root, 'supabase.json')
cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else {}
supa = 'window.SUPABASE = ' + json.dumps({k: cfg[k] for k in ('url', 'key') if k in cfg}) + ';'
# Recorded sounds (Freesound, CC0; see data/sounds/CREDITS.md), embedded in the page
snd_dir = os.path.join(root, 'data', 'sounds')
clips = {os.path.splitext(os.path.basename(f))[0]: 'data:audio/mpeg;base64,' + base64.b64encode(open(f, 'rb').read()).decode() for f in sorted(glob.glob(os.path.join(snd_dir, '*.mp3')))}
sounds = 'window.SOUND_CLIPS = ' + json.dumps(clips) + ';'

assert '/*__COURSES__*/' in src, 'game_src.html has no course list placeholder'
out = src.replace('/*__COURSES__*/', listing).replace('/*__PHYSICS__*/', phys).replace('/*__SUPABASE__*/', supa).replace('/*__SOUNDS__*/', sounds)
names = ' and '.join(c['title'] for c in courses)
page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        f'<meta name="description" content="A daily golf game on the real {names} golf courses. Type a name and play.">\n'
        '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 32 32\'%3E%3Crect width=\'32\' height=\'32\' rx=\'8\' fill=\'%23173628\'/%3E%3Crect x=\'10\' y=\'5\' width=\'2.4\' height=\'22\' fill=\'%23eaf3ec\'/%3E%3Cpath d=\'M12.4 6 L24 10 L12.4 14 Z\' fill=\'%23f0643c\'/%3E%3C/svg%3E">\n'
        '</head>\n<body>\n' + out + '\n</body>\n</html>\n')
open(os.path.join(site, 'index.html'), 'w', encoding='utf-8').write(page)
sizes = ', '.join(f"{c['id']} {round(os.path.getsize(os.path.join(site, 'courses', c['id'] + '.js')) / 1024)} KB" for c in courses)
print(f"built page {round(len(page.encode()) / 1024)} KB; courses: {sizes}; leaderboard {'connected' if cfg.get('url') else 'not configured'}; {len(clips)} sound clips")
