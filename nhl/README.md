# The two 88s, tracked daily

`/nhl/` follows David Pastrňák (Boston) and Martin Nečas (Colorado), both number 88, through the NHL regular season, with the whole league as the yardstick. Every number on the page is recomputed each morning.

## What the page shows

- Each player's shots on a half rink, sized by expected goals (xG).
- A funnel plot of goals minus xG for every shooter with 30+ unblocked shots, with an 80% chance band.
- Shooting percentage shrunk toward what forwards usually manage (beta-binomial).
- A simulated date for Pastrňák's 1,000th and Nečas's 500th career point.
- A permutation test of each player's longest point streak.
- Every team's points against its goal difference (Pythagorean) and its 5-on-5 PDO.

## The pieces

| File | Job |
|---|---|
| `parse.py` | Turns one game's play-by-play into shots, the non-shootout score and 5-on-5 counts |
| `collect.py` | Adds new finished games, refreshes standings, skaters and the two players |
| `analysis.py` | Fits the xG model and the estimates, writes `data.json` |
| `index.html` | Reads `data.json`, draws the page |
| `data/` | `shots.csv.gz` and `games.csv.gz` grow by one day's games; `history.json` holds past seasons for the priors |
| `.github/workflows/nhl.yml` | Runs collect and analysis at 10:15 UTC, commits, dispatches the deploy |

## How a day runs

1. The schedule lists finished regular-season games; any not yet in `games.csv.gz` is fetched and parsed.
2. A game whose goals land mostly in the wrong half after flipping ends is skipped and retried the next day.
3. `analysis.py` refits everything from scratch on the full season so far.
4. The bot commits `nhl/data` and `nhl/data.json` and triggers the deploy.

Run it by hand from the repo root:

```
pip install -r nhl/requirements.txt
python -m nhl.collect             # add --history once a season to refresh the past seasons
python -m nhl.analysis
```

## Why it is built this way

- **Leave-player-out xG.** Each 88 is scored by a model refitted without his own shots, so he is never judged on data that trained the model.
- **A band, not a p-value.** The two players were picked for their number, so their results are read against every shooter in the league.
- **Shrinkage.** A few dozen shots say little about a true shooting rate.

## Caveats

- Everything is association. The model does not see the pass before a shot, screens or the goalie.
- Arena scorers log coordinates differently.
- The Pythagorean exponent is fitted on official goal totals, which count one goal for a shootout win, and applied to goals without them.
- `SEASON`, `SEASON_START` and `PAST` in `collect.py` need changing for a new season, followed by `--history`.
