# Builds an offline test copy of the site in test_site/ (gitignored): the leaderboard is switched off so tests
# never post scores. test_site/bot.html is the game with the test bot (bot3.js) added.
import os, re, shutil
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.join(here, '..')
out = os.path.join(root, 'test_site')
shutil.rmtree(out, ignore_errors=True); shutil.copytree(os.path.join(root, 'site'), out)
g = open(os.path.join(out, 'index.html'), encoding='utf-8').read()
g, n = re.subn(r'window\.SUPABASE = \{[^;]*\};', 'window.SUPABASE = {};', g, count=1)
assert n == 1, 'supabase config not found'
open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(g)
b = open(os.path.join(here, 'bot3.js'), encoding='utf-8').read()
open(os.path.join(out, 'bot.html'), 'w', encoding='utf-8').write(g.replace('</body>', '<script>' + b + '</script></body>'))
print('test copy built in test_site/, leaderboard off')
