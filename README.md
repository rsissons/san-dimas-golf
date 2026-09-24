# San Dimas Canyon Golf

A daily browser golf game played on the real San Dimas Canyon Golf Course (San Dimas, California). Type a name and play: no accounts.

**Play:** https://rsissons.github.io/san-dimas-golf/

- **Daily challenge:** three holes a day (a par 3, a 4 and a 5), the same pins and wind for everyone, one scored attempt per device, with a daily leaderboard.
- **Free play:** the full 18 from Blue, White or Red tees at four player levels, with an 18-hole leaderboard.
- **Swing:** drag back from the ball for power and release. The lean of the pull is the hook or slice.

## What's real
- Holes, fairways, greens, bunkers, water, tees and cart paths are traced from [OpenStreetMap](https://www.openstreetmap.org/copyright) (© OpenStreetMap contributors, ODbL).
- The ground is USGS 3DEP 1-metre elevation (public domain), sampled at 4 m. Greens are reshaped to a maximum 2.5% tilt.
- Par, yardages and handicaps come from the course scorecard.
- Ball flight is calibrated to TrackMan PGA Tour averages; bounce, roll and putting are tuned to real-world numbers (a Stimpmeter of about 9.6).

Unofficial fan game; not affiliated with the course or American Golf.

## Building
`python source/build.py` inlines the course data, the physics and the leaderboard settings, and writes `site/index.html` (the published page).

The leaderboard is a Supabase table (`supabase-setup.sql`). Put the project URL and the publishable (anon) key in `supabase.json` as `{"url": "...", "key": "..."}` before building. That key is meant to be public; the table's rules only allow adding and reading scores.

## License
Code: MIT. Map data: © OpenStreetMap contributors (ODbL). Elevation: USGS 3DEP (public domain).
