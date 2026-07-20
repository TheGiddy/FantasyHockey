# H2H weekly matchup simulation (Monte Carlo)

Rosters = keepers + need-aware vorp draft (2025 order, TD slot 7). 28 fantasy weeks from the 2026-27 schedule. Weekly noise calibrated on 2024-25 + 2025-26 actual league weeks. Seed 7.

## Calibration (league-average weekly totals per team)

| Cat | model raw | history | utilization | overdispersion phi |
|---|---|---|---|---|
| G | 13.3 | 16.0 | 1.20 | 1.4 |
| A | 23.9 | 26.7 | 1.12 | 1.8 |
| PIM | 26.8 | 28.3 | 1.06 | 3.6 |
| PPP | 11.4 | 13.2 | 1.15 | 1.6 |
| SOG | 115.5 | 130.9 | 1.13 | 4.5 |
| HIT | 55.2 | 60.4 | 1.10 | 3.6 |
| BLK | 47.7 | 47.8 | 1.00 | 2.4 |
| W | 1.7 | 3.3 | 1.91 | 1.0 |
| SHO | 0.2 | 0.4 | 1.96 | 1.0 |
| SV% | — | 0.900 | — | weekly sd 0.0248 |

## Projected power ranking (avg weekly matchup win% vs field)

| Team | win% |
|---|---|
| Autodraft | 57.8% |
| Gents | 53.5% |
| Puppa | 51.9% |
| TD | 51.6% |
| ER | 51.2% |
| ASD | 50.6% |
| Sawchuk | 45.0% |
| PK | 38.4% |

## Twin Daddy vs each opponent (per-cat weekly win rates)

| Opp | match win% | G | A | PIM | PPP | SOG | HIT | BLK | W | SHO | SV% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Gents | 48.0% | 80% | 60% | 19% | 71% | 81% | 25% | 15% | 51% | 38% | 49% |
| ER | 51.5% | 65% | 33% | 44% | 35% | 66% | 74% | 19% | 65% | 52% | 56% |
| ASD | 50.8% | 60% | 53% | 23% | 47% | 58% | 15% | 12% | 99% | 62% | 75% |
| Autodraft | 43.1% | 68% | 51% | 28% | 56% | 73% | 30% | 20% | 61% | 42% | 47% |
| Puppa | 50.4% | 74% | 47% | 35% | 57% | 70% | 55% | 15% | 57% | 45% | 48% |
| PK | 61.8% | 89% | 73% | 19% | 82% | 80% | 22% | 10% | 64% | 45% | 53% |
| Sawchuk | 55.7% | 72% | 44% | 28% | 45% | 68% | 61% | 37% | 72% | 45% | 51% |
| **avg** | | **72%** | **52%** | **28%** | **56%** | **71%** | **40%** | **18%** | **67%** | **47%** | **54%** |

## TD first pick (R1, slot 7): simulated season win% per candidate

Candidate forced at R1, rest of draft re-filled greedily, TD simmed vs all 7 opponents (4,000 weeks each, common random numbers — differences under ~0.5% are still noise).

| Candidate | pos | vorp/z | avg win% | avg cats/wk |
|---|---|---|---|---|
| Brady Tkachuk | C/LW | +7.13 | 53.4% | 4.65 |
| Moritz Seider | D | +9.07 | 53.1% | 4.63 |
| Connor McDavid | C | +9.10 | 52.8% | 4.62 |
| Nathan MacKinnon | C | +9.49 | 52.2% | 4.60 |
| David Pastrnak | RW | +6.15 | 51.5% | 4.59 |
| Nikita Kucherov | RW | +5.64 | 51.1% | 4.57 |
| Rasmus Dahlin | D | +7.34 | 50.6% | 4.55 |
| Tim Stützle | C/LW | +4.59 | 50.4% | 4.54 |
| Cale Makar | D | +7.76 | 50.1% | 4.52 |
| Mikko Rantanen | LW/RW | +2.98 | 49.7% | 4.51 |
| Leon Draisaitl | C/LW | +4.31 | 49.6% | 4.51 |
| Auston Matthews | C | +4.25 | 49.3% | 4.50 |
| Darnell Nurse | D | +3.68 | 49.3% | 4.49 |
| Seth Jarvis | C/LW/RW | +3.59 | 49.3% | 4.49 |
| Connor Bedard | C/RW | +4.26 | 49.3% | 4.50 |
| Quinn Hughes | D | +6.10 | 49.0% | 4.49 |
| Mikhail Sergachev | D | +3.41 | 48.1% | 4.46 |
| Brandt Clarke | D | +2.74 | 47.5% | 4.43 |
| Jack Hughes | C/LW | +2.56 | 47.5% | 4.43 |
| Josh Morrissey | D | +2.31 | 47.1% | 4.42 |
| Andrei Vasilevskiy | G | +5.64 | 44.8% | 4.34 |
| Ilya Sorokin | G | +5.46 | 44.0% | 4.33 |
| Connor Hellebuyck | G | +4.27 | 43.1% | 4.27 |
| Jake Oettinger | G | +3.92 | 42.9% | 4.25 |

## Assumptions & limits
- No daily lineup sitting beyond the calibrated utilization factor; players independent within a week; injuries only as gp availability thinning.
- Opponents draft best-vorp with scripted goalie rounds; keep? either/or groups resolved by vorp.
- SV% weekly noise is the historical within-team sd — dominated by randomness, per the two-season diagnosis.
