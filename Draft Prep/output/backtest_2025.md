# Backtest — 2025-26 projected blind from 2022-25 data

Matched players: 631 (projected pool x actual 2025-26)

## Value-rank quality (Spearman rank correlation vs actual 7-cat z)

- model v2: **0.771**
- naive (2024-25 carried forward): **0.751**
- market (2025 live picks, n=107): **0.453** (model on same subset: **0.556**)

## Top-50 hit rate

model 34/50, naive 31/50

## Per-category correlation & MAE (actual GP >= 40)

|cat|r (model)|r (naive)|MAE (model)|
|---|---|---|---|
|G|0.834|0.793|4.3|
|A|0.848|0.799|6.2|
|PIM|0.756|0.699|11.2|
|PPP|0.872|0.835|3.0|
|SOG|0.846|0.819|24.6|
|HIT|0.820|0.829|23.3|
|BLK|0.867|0.854|13.8|

## Breakout blend check

35 players flagged; mean projected z -5.58, mean actual z -5.20 (all matched: proj -5.80, actual -6.11)

## Biggest misses (players in either top-120)

**Model too LOW (breakouts it missed):**
- Anthony Mantha: proj rank 467, actual 109 (GP 81)
- Adam Klapka: proj rank 441, actual 106 (GP 79)
- Leo Carlsson: proj rank 385, actual 100 (GP 70)
- Cutter Gauthier: proj rank 321, actual 40 (GP 76)
- Vasily Podkolzin: proj rank 357, actual 98 (GP 82)
- Brandt Clarke: proj rank 301, actual 67 (GP 82)
- Will Cuylle: proj rank 270, actual 47 (GP 82)
- Trevor Zegras: proj rank 272, actual 70 (GP 81)

**Model too HIGH (busts it bought):**
- Martin Pospisil: proj rank 81, actual 553 (GP 22)
- Victor Hedman: proj rank 74, actual 504 (GP 33)
- Pierre-Luc Dubois: proj rank 83, actual 512 (GP 29)
- Frank Vatrano: proj rank 33, actual 439 (GP 50)
- Matthew Tkachuk: proj rank 10, actual 327 (GP 31)
- Jonathan Huberdeau: proj rank 111, actual 379 (GP 50)
- Neal Pionk: proj rank 91, actual 335 (GP 51)
- Jared McCann: proj rank 97, actual 303 (GP 52)

## Goalies (actual GS >= 20, n=50)

- W: r=0.446, MAE=6.5
- SV%: r=0.066
- starts: r=0.534
