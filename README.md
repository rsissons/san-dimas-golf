# Canyon Golf

A daily browser golf game played on real Southern California courses. Type a name and play: no accounts.

**Play:** https://rsissons.github.io/san-dimas-golf/ (pick a course at the top of the lobby, or link straight to one with `?course=marshall-canyon`)

| Course | City | Par | Tees |
|---|---|---|---|
| San Dimas Canyon Golf Course | San Dimas | 72 | Blue, White, Red |
| Marshall Canyon Golf Course | La Verne | 71 (73 from Red/Gold) | Blue, White, Red, Gold |

- **Daily challenge:** three holes a day per course (a par 3, a 4 and a 5), the same pins and wind for everyone, one scored attempt per device, with a daily leaderboard.
- **Free play:** the full 18 from any tee at four player levels, with an 18-hole leaderboard per course.
- **Swing:** drag back from the ball for power and release. The lean of the pull is the hook or slice.

## What's real
- Holes, fairways, greens, bunkers, water, tees, cart paths and drainage ditches are traced from [OpenStreetMap](https://www.openstreetmap.org/copyright) (© OpenStreetMap contributors, ODbL).
- The ground is USGS 3DEP 1-metre elevation (public domain), sampled at 4 m. Greens are reshaped to a maximum 2.5% tilt.
- Dry arroyos (Marshall Canyon) are found in the elevation itself: channels at least 2.5 m below the ground around them. They play as hazards (penalty stroke and a drop), as the course's local rules say.
- Par, yardages, handicaps and ratings come from each course's scorecard. Landmarks the map doesn't have (a lone tree, a utility box) are added from people who play the course.
- Ball flight is calibrated to TrackMan PGA Tour averages; bounce, roll and putting are tuned to real-world numbers (a Stimpmeter of about 9.6).

Unofficial fan game; not affiliated with the courses or their operators.

## Adding a course
1. Make `courses/<id>/course.json` (copy `courses/marshall-canyon/course.json`): the OpenStreetMap way id of the course boundary, the tees, the scorecard (par, handicaps, yardages per tee, and `parBy` for holes whose par changes with the tees), the ratings, and a `style` (tree density, dry rough, whether to trace arroyos and ditches). OpenStreetMap needs a `golf=hole` line for each of the 18 holes.
2. `python source/course_tool.py <id>` fetches OpenStreetMap, samples the USGS elevation (a few thousand points; it resumes if interrupted), extracts the features and writes `courses/<id>/data.js`. It prints each tee's measured yardage against the card.
3. Optional `landmarks` in the config: `{ "hole": 4, "kind": "tree" | "box", "from": "white" | "green", "yards": 60, "across": 0 }` (`across`: -1 left edge of the fairway, 0 middle, +1 right edge, looking at the green).
4. `python source/build.py` picks up every course that has a `data.js`. The lobby's course picker, the leaderboards and the saved rounds all follow the course id.

## Building and testing
- `python source/build.py` writes `site/index.html` (the game) and `site/courses/<id>.js` (one data file per course).
- `python source/mk_test.py` makes an offline copy in `test_site/` with the leaderboard switched off, so tests never post scores.
- `npm install`, then `node source/test.cjs <course> [round|daily] [tee]` plays a bot round in headless Chrome, and `node source/shots.cjs <course> <prefix> <holes>` takes screenshots.

The leaderboard is a Supabase table (`supabase-setup.sql`, one table for all courses). Put the project URL and the publishable (anon) key in `supabase.json` as `{"url": "...", "key": "..."}` before building. That key is meant to be public; the table's rules only allow adding and reading scores.

## License
Code: MIT. Map data: © OpenStreetMap contributors (ODbL). Elevation: USGS 3DEP (public domain). Sounds: Freesound recordings under CC0 (public domain); see [data/sounds/CREDITS.md](data/sounds/CREDITS.md).
