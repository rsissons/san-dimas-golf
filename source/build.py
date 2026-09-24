# Builds the single-file game: puts the course data, the physics and the leaderboard settings into the page.
# Writes ../san-dimas-canyon-18.html and ../site/index.html (the GitHub Pages copy).
import os, json
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.join(here, '..')
src = open(os.path.join(here, 'game_src.html'), encoding='utf-8').read()
data = open(os.path.join(root, 'data', 'data.js'), encoding='utf-8').read()
phys = open(os.path.join(here, 'physics.js'), encoding='utf-8').read()
# supabase.json holds the project URL and the publishable (anon) key, which are public by design
cfg_path = os.path.join(root, 'supabase.json')
cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else {}
supa = 'window.SUPABASE = ' + json.dumps({k: cfg[k] for k in ('url', 'key') if k in cfg}) + ';'
out = src.replace('/*__DATA__*/', data).replace('/*__PHYSICS__*/', phys).replace('/*__SUPABASE__*/', supa)
open(os.path.join(root, 'san-dimas-canyon-18.html'), 'w', encoding='utf-8').write(out)
page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="A daily golf game on the real San Dimas Canyon course. Type a name and play.">\n'
        '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 32 32\'%3E%3Crect width=\'32\' height=\'32\' rx=\'8\' fill=\'%23173628\'/%3E%3Crect x=\'10\' y=\'5\' width=\'2.4\' height=\'22\' fill=\'%23eaf3ec\'/%3E%3Cpath d=\'M12.4 6 L24 10 L12.4 14 Z\' fill=\'%23f0643c\'/%3E%3C/svg%3E">\n'
        '</head>\n<body>\n' + out + '\n</body>\n</html>\n')
os.makedirs(os.path.join(root, 'site'), exist_ok=True)
open(os.path.join(root, 'site', 'index.html'), 'w', encoding='utf-8').write(page)
print('built', round(len(out.encode()) / 1024), 'KB · leaderboard', 'connected' if cfg.get('url') else 'not configured')
