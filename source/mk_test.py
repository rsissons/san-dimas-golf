# Builds offline test copies of the live game: the leaderboard is switched off so tests never post scores.
import re, sys
g = open(r'C:/Users/rsiss/Projects/SanDimasGolf/site/index.html', encoding='utf-8').read()
g, n = re.subn(r'window\.SUPABASE = \{[^;]*\};', 'window.SUPABASE = {};', g, count=1)
assert n == 1, 'supabase config not found'
b = open('bot3.js', encoding='utf-8').read()
open('v3.html', 'w', encoding='utf-8').write(g)
open('bot3.html', 'w', encoding='utf-8').write(g.replace('</body>', '<script>' + b + '</script></body>'))
print('test copies built, leaderboard off')
