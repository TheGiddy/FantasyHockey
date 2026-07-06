# Fantasy Hockey Keeper League — 2026-27 Prep (Twin Daddy)
*Working context file — generated 2026-07-05. Import into Claude Code as project context.*

## League setup
- 8 teams, Yahoo, **linear draft (NOT snake)**, **20 rounds (2026-27 change: was 21)**. Draft order TBD (late July). **Traded picks keep the original team's slot.**
- H2H categories — Skaters: G, A, PIM, PPP, SOG, HIT, BLK. Goalies: W, SV%, SHO
- Rosters: 3C / 3LW / 3RW / **4D (2026-27 change: was 5D)** / 2G / 5BN / IR / IR+ — D replacement level rises (32 starters, not 40), D vorp deflates, fewer D games per week league-wide. TD's old R21 pick is VOID (confirmed — R21 no longer exists). BLK/HIT weekly totals shrink league-wide (fewer D starts); category leverage weights are from the 5D season — re-derive after 2026-27.
- Keeper rules: keep at drafted round **+2**; undrafted/waiver players = round 12 default; players drafted R1-2 **cannot be kept**; a player CAN be kept using an EARLIER round pick than their keeper round; keepers limited only by matching/earlier picks owned; **pick trades must exchange equal pick counts**
- 2025-26 standings: 1 Sawchuk Dun Thats (champ, 11-9-0/22), 2 AdamSuxDix, 3 The Most Distinguished Gents, 4 Autodraft, 5 Emotional Reactions, **6 Twin Daddy (9-10-1, 19pts)**, 7 Daren Puppa'd His Pants, 8 P.K. SubUwU

## Twin Daddy keeper decisions (final)
| Player | Keeper Rd | 25-26 format rank | Rationale |
|---|---|---|---|
| Cutter Gauthier | 19 | #48 | 41G/285 SOG at pick ~150 |
| Lukas Dostal | 19 | outside top 175 | Downgraded to flier — need real G plan |
| Leo Carlsson | 12 | outside top 119 | Age-22, ANA 1C; points fine, no bangers |
| Jackson LaCombe | 12 | #105 | 128 BLK; won slot over Wallstedt |
| Dylan Guenther | 10 | #44 | 40G |
| Dylan Cozens | 15 | **#17** | 215 HIT — elite format fit |
| Logan Cooley | 16 | n/a (54 GP) | Acquired for Raddysh; injury year |
| Dylan Holloway | 7 | n/a | Marginal value; fits banger need |

**Not keepable / trade currency:** Wallstedt (#49, G), Sennecke (#90, projects top-50 next yr), Dorofeyev (#76), Larkin (#51), Konecny (#77), Clarke (#79) — all rd-12, both TD R12s consumed by Carlsson/LaCombe. Also stuck: Pinto, Bertuzzi, E. Karlsson, Landeskog.

## Twin Daddy live draft picks (after keepers)
R1, R2, R3, R4, R4(Autodraft slot), R5, R5(ER slot), R6, R6(ER slot), R8, R8(ER slot), R9 — **12 live picks** (old R21 void with the 20-round draft)
- **Key insight: spare R8/R8/R9 can each KEEP an acquired round-12 player** (earlier-pick rule)
- TD's own R11/13/14/17/18/20 were traded away (mostly to ER, Autodraft, PK)

## Diagnosis of 2025-26 (why 6th with 5 breakouts)
~~Roster shape: skill-heavy, donated PIM/HIT/BLK weekly. Draft priority = multi-cat bangers and physical D.~~
**CORRECTED 2026-07-05 with actual weekly category W/L data (`analyze_league_2025.py` → `output/league_diagnosis_2025.md`):** the banger-deficit theory was wrong. TD's physical cats went 46% (HIT 12-of-23 was a *strength*); the real holes were **SOG (4-of-23 — worst single cat in the league), goalie cats (28%)**, and skill cats overall (36%). Compounding it: SOG is the #2 most coin-flip category league-wide (SV% is #1), so shot volume is both TD's biggest weakness AND the cheapest cat to flip. SHO is a lottery (least separable cat) — never draft for it.
**Revised draft priority: shot-volume forwards and a real goalie plan, THEN physical D.** MacKinnon (350 SOG) R1 and the DeBrincat (287 SOG)/Meier (269 SOG) trade targets align perfectly; pure-banger targets help less than assumed.

## Verified per-team keeper projections (CSV cross-checked vs pick inventories)
*Method: optimal value assignment of candidates (keeper rd or earlier pick), R1/2-drafted illegal. Tail risk: any team may burn an R1/R2 PICK to rescue a squeezed star.*

### Sawchuk Dun Thats (champ) — missing R5, R6
- KEEPS: Johnston@3 (#11), M. Tkachuk@4, Eichel@7/8, Necas@10, Blackwood@9, Bouchard@11/12, 2 of Knight/Andersson/Lundell@11-12, Will Smith@16/17
- FALLS: **Aho (#45), Meier (#95, 269 SOG/131 HIT), Adin Hill**, Guentzel (illegal), Fox (illegal)

### AdamSuxDix — pick-rich, NOT squeezed
- KEEPS: Tage@3 (#15), Reinhart@4, Zadorov, Weegar, Tavares, Geekie, Forsberg, Faber, Hischier, Hertl@13, Laferriere, Dunn@18, Gudas, Coyle
- FALLS: Pettersson (loses R3 to Tage unless they burn R2), Ovechkin (illegal)

### The Most Distinguished Gents — nothing between R3 and R11 (rebuild, 15 late picks)
- KEEPS: Kempe@3, Bennett OR Batherson@11, Carlson@14
- FALLS: **DeBrincat (#32), Nurse (#69), Stamkos, Marchand, Malkin, Lafreniere, Kastelic (#109), Bobrovsky**, Josi/Sorokin/Crosby (illegal)

### Autodraft — no R4-R7; strong R8-R11
- KEEPS: Svechnikov@3 (#20), Sherwood@8 (#60, 339 HIT), Chychrun@9 (#35), Scheifele@9, Hagel@10, Gustavsson@11, Wedgewood@11 (#9 G), Suzuki@16-18 (**#8** — confirmed on their list, rd 18), Edvinsson@17, Trouba maybe
- FALLS: **Heiskanen (#75), Jarvis (#81), Dobson (#97), Trocheck (#88), Eriksson Ek** — one R3 can't save five

### Emotional Reactions — no R5-R8, no R11
- KEEPS: Boldy@4, Slafkovsky@9 (#23 — CONFIRMED KEPT per league intel), Robertson@10 (#6), Celebrini@12 (#3), Hutson@15/16, Sanderson OR Cuylle@13, Askarov@19, + R3 → McAvoy or Tuch or Zibanejad
- FALLS: **Swayman (#64 G), Raddysh (#22), Zibanejad (#26 — owner unlikely to keep per TD's read)**, 2 of McAvoy/Tuch/Zib, Ullmark, Manson, Panarin (illegal)
- ⚠️ Tuch is TD's #1 trade target — if this manager sentimentally burns R3 on Tuch, he's gone. Trade before deadline for certainty.

### Daren Puppa'd His Pants — deep picks, deep list (young-core rebuild = future rival)
- KEEPS: Wilson@4 (#24), Bratt@5, Hyman@6, L. Thompson@7 (G #21), Jones@9, Keller@10, Marchenko@11, Gibson@12 (G #66), Zegras or Harley@12, Werenski@13 (#37), Kane@13?, Nikishin@15, Barkov@16/17, Schaefer@18 (#56, age 19)
- FALLS: Horvat (#103), Stone, Markstrom, Fiala, Zegras-or-Harley loser

### P.K. SubUwU — pick-rich (triples at 5 and 7), NOT squeezed
- KEEPS: Hamilton@4, Knies@7/8, Caufield@10-12 (#31), Fantilli@11/12 (#72), Wolf@12, Olivier@13/14, Kuemper@14, Theodore@14, Dobes/Greaves as picks allow
- FALLS: Point (illegal), Trenin/Granlund/Podkolzin tier

## Consolidated draft pool projection (elite tier)
Never kept: McDavid, MacKinnon, Kucherov, Draisaitl, Pastrnak, Kaprizov, **Matthews (#119 season / pre-rank 17 — prime buy-low)**, J. Hughes, Makar, Q. Hughes, Dahlin, Seider (#7), B. Tkachuk?, Hellebuyck (**absent from entire top-175 — investigate**), Vasilevskiy, Oettinger, Shesterkin, Vejmelka
Illegal keepers re-entering: Crosby, Ovechkin, Panarin, Point, Guentzel, Fox, Josi, Sorokin
Squeeze victims: see FALLS lists above

## Pre-draft trade targets (acquire player → keep with spare pick)
1. **Tuch (ER)** → keep @ spare R6. 90 BLK winger. Highest urgency (R3 sentiment risk)
2. **DeBrincat (Gents)** → spare R5. 287 SOG. Gents drowning in late picks, cheapest cost
3. **Meier or Aho (Sawchuk)** → spare R6/R5. Meier preferred (SOG/HIT/BLK)
4. **Jarvis (Autodraft)** → spare R6 (rd 6 exactly)
5. **Raddysh (ER)** → spare R8 (rd-12 default). #22 last season; ER can't fit him — TD traded him away for Cooley, can reacquire cheap
6. Heiskanen (Autodraft) → spare R4 ONLY at giveaway price (#75 in this format)
- Currency: Wallstedt (sell to Sawchuk — Hill falls; avoid arming ER/Puppa young cores), Sennecke (projects top-50 — price high; fits Gents rebuild), Dorofeyev, Larkin
- Reminder: pick-for-pick trades must be equal count; player-for-player avoids the rule

## Draft board by round (linear draft; targets assume pool above)
- R1: MacKinnon (350 SOG) > McDavid > Kucherov > Pastrnak
- R2: Seider (128 HIT/180 BLK) > Dahlin > B. Tkachuk > Makar/Q. Hughes (skill-D discount in this format)
- R3: **Matthews buy-low** > Dahlin if slid > Guentzel > Wilson-tier gone (kept)
- R4 (x2): Ovechkin (SOG/HIT) + Chychrun-tier D gone → DeBrincat-class if not pre-traded, Stamkos (FADE — 20.4 sh%), Zibanejad if ER releases
- R5 (x2): Panarin, Crosby, Connor, Bennett (if Gents lose him), Aho
- R6 (x2): Tuch/Meier/Jarvis (if not pre-traded), first goalie (Sorokin/Vasilevskiy/Oettinger tier)
- R8 (x2): **convert to rd-12 keeper slots (Raddysh/Swayman targets)** or second goalie + Kastelic-tier banger
- R9: third keeper-conversion slot, or Hronek/Nurse/fifth D
- R21: Sennecke reunion / rookie flier
- Goalie philosophy: 8+ starters loose; Dostal is a flier not a plan; draft situations not stats

## 2026-27 Projections (age curves + sh% regression + deployment; NHL API blocked — no xG/TOI inputs)
|Proj rank|Player|Pos|Age|G|A|PIM|PPP|SOG|HIT|BLK|Value z|Note|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|1|M. Celebrini|C|20|52|82|48|38|335|57|57|8.62|Franchise ascent, PP1 locked|
|2|C. McDavid|C|30|47|88|44|53|298|40|30|8.36|Elite stable|
|3|N. MacKinnon|C|31|50|70|38|28|329|62|34|5.65|Volume ages well|
|4|W. Johnston|C|23|50|46|35|47|229|61|59|4.49|Ascending, Hintz aging|
|5|D. Pastrnak|RW|30|28|69|72|32|254|86|32|4.36|29G low vs 15% career sh% - positive regression|
|6|J. Robertson|LW|27|45|51|32|41|294|48|34|4.17|Prime|
|7|M. Seider|D|25|11|53|59|30|198|132|185|4.09|Entering D prime|
|8|J. Slafkovsky|LW|22|34|49|56|32|204|114|84|3.51|Age-22 leap w/ Suzuki|
|9|M. Boldy|LW|25|45|46|31|32|269|62|60|3.16|Prime entry|
|10|N. Kucherov|RW|33|39|77|48|33|206|35|28|3.05|Skill ages, watch cliff|
|11|D. Cozens|C|25|30|33|61|31|217|221|25|2.92|OTT top-6 locked; hits sticky|
|12|N. Suzuki|C|27|29|72|28|43|183|62|62|2.78|Prime|
|13|T. Stutzle|C|25|36|52|40|31|206|130|45|2.53|Prime entry|
|14|A. Svechnikov|LW|26|32|41|69|30|211|154|17|2.46|Contract yr; CAR top-6|
|15|E. Bouchard|D|27|21|74|30|33|221|29|101|2.35|PP1 EDM|
|16|C. Bedard|C|21|36|54|54|25|273|34|29|2.07|Year-4 ascent|
|17|R. Dahlin|D|26|20|58|78|23|204|68|81|2.06|Prime|
|18|M. Schaefer|D|19|28|44|41|22|274|43|120|2.05|Gen talent yr2 leap|
|19|K. Kaprizov|LW|29|44|43|28|31|262|52|27|1.61|Stable|
|20|T. Thompson|C/RW|29|39|40|35|23|265|85|48|1.5|Stable|
|21|D. Guenther|RW|23|45|37|30|27|269|71|30|1.49|Ascending sniper|
|22|C. Gauthier|LW|23|46|31|30|21|320|69|22|1.38|Ascending; ANA improving|
|23|M. Rantanen|RW|30|22|55|95|34|138|49|31|1.16|22G on 139 SOG = injury/usage dip; rebound|
|24|J. Guentzel|LW|32|36|47|59|28|207|38|40|1.13|Age risk|
|25|T. Wilson|RW|32|28|30|113|11|144|174|51|1.0|Physical ages OK|
|26|M. Tkachuk|LW|29|22|37|72|20|220|165|19|0.82|Injury-marred yr; rebound|
|27|C. Caufield|RW|26|51|37|14|29|258|50|21|0.79|Prime sniper|
|28|L. Hutson|D|22|14|77|37|23|145|34|148|0.78|Age-22 leap|
|29|B. Sennecke|RW|20|28|45|67|16|238|105|26|0.78|Yr2 leap; ANA rising|
|30|W. Cuylle|LW|24|21|19|68|9|168|314|71|0.75|Rising role NYR|
|31|J. Chychrun|D|28|26|34|62|18|221|58|114|0.74|Volume D|
|32|A. Fantilli|C|22|27|40|41|15|245|150|55|0.67|Age-22 leap, 1C role|
|33|C. Makar|D|28|20|59|24|29|199|35|118|0.65|Down-ish yr; rebound|
|34|M. Necas|RW|30|37|60|30|23|201|85|26|0.63|COL top-6|
|35|F. Forsberg|LW|32|38|33|33|24|231|120|32|0.5|Age risk|
|36|Z. Werenski|D|29|22|59|18|21|260|30|94|0.35|Elite volume D|
|37|A. DeBrincat|RW|29|40|43|19|22|280|38|39|0.34|Stable volume|
|38|A. Kempe|RW|30|35|36|58|12|220|127|39|0.28|Stable|
|39|J. Eichel|C|30|26|61|18|27|254|35|40|0.22|Stable|
|40|L. Draisaitl|C|31|33|58|25|39|175|33|15|0.01|Slight fade|
|41|Q. Hughes|D|27|7|70|33|35|191|7|89|-0.02|New team yr2, PP1|
|42|C. Keller|RW|28|26|62|38|27|225|8|32|-0.07|Prime|
|43|B. Clarke|D|23|9|36|68|14|177|32|200|-0.18|Ascending|
|44|K. Connor|LW|30|38|52|16|19|267|36|19|-0.43|Stable|
|45|D. Holloway|LW|25|26|40|46|16|200|143|41|-0.43|Est. line; STL top-6|
|46|L. Carlsson|C|22|34|45|22|26|226|49|38|-0.44|Est. line; ANA 1C, age-22 leap|
|47|D. Batherson|RW|28|33|38|33|30|167|122|22|-0.46|Prime|
|48|S. Aho|C|29|26|52|46|26|190|63|23|-0.5|Stable|
|49|S. Bennett|C|30|25|31|82|14|196|115|32|-0.52|Physical stable|
|50|C. McAvoy|D|29|11|50|62|23|111|79|129|-0.55|Injury history|
|51|M. Zibanejad|C|33|30|39|14|31|191|102|48|-0.62|Decline watch|
|52|L. Cooley|C|22|33|30|32|28|234|65|27|-0.69|54GP -> 78GP + leap|
|53|M. Weegar|D|33|4|23|85|6|145|162|170|-0.78|Physical D ages OK|
|54|A. Tuch|RW|30|32|32|57|9|190|82|90|-0.79|Stable|
|55|S. Jarvis|C/W|25|34|36|24|22|238|83|28|-0.79|Prime entry|
|56|D. Larkin|C|30|33|32|48|23|223|46|33|-0.8|Stable|
|57|T. Zegras|C/W|25|27|43|63|24|175|47|29|-0.91|Re-establishing|
|58|M. Sergachev|D|28|10|49|44|26|159|38|125|-0.94|Stable|
|59|M. Scheifele|C|33|32|60|42|20|156|31|46|-0.95|Decline watch|
|60|R. Andersson|D|30|17|29|71|13|174|37|150|-1.0|Stable|
|61|B. Hagel|LW|28|36|38|58|12|214|42|38|-1.01|Prime|
|62|N. Hischier|C|28|28|38|29|23|211|58|62|-1.06|Prime|
|63|N. Zadorov|D|31|2|20|147|0|104|190|99|-1.1|Physical D|
|64|K. Marchenko|RW|27|27|40|32|23|218|61|40|-1.18|Prime|
|65|D. Nurse|D|31|7|17|101|0|160|133|162|-1.21|Physical D|
|66|L. Raymond|RW|25|27|54|23|29|184|44|30|-1.21|Prime entry|
|67|M. Barzal|C|29|19|52|61|20|179|29|50|-1.27|Injury history|
|68|K. Sherwood|RW|31|21|12|48|11|158|322|29|-1.34|13.4 sh% ok; hits elite|
|69|A. Matthews|C|29|31|30|19|14|261|44|85|-1.39|Down yr (injury); elite rebound|
|70|M. Heiskanen|D|27|9|54|30|28|148|21|132|-1.42|2 straight injury yrs|
|71|T. Konecny|LW|29|26|40|59|14|164|108|38|-1.44|Stable|
|72|M. Knies|LW|24|25|47|30|17|151|160|34|-1.5|Ascending power W|
|73|A. Laferriere|W|25|22|24|19|5|222|263|50|-1.53|Rising role|
|74|B. Faber|D|24|16|39|40|12|189|34|152|-1.56|Prime entry|
|75|J. Hughes|C|25|29|53|10|24|242|4|33|-1.59|Prime; health risk|
|76|J. LaCombe|D|26|11|51|20|18|167|76|132|-1.64|ANA rising, PP1|
|77|S. Stamkos|C/RW|36|35|20|53|22|173|81|33|-1.73|20.4 sh% at 36 - big regression|
|78|P. Dorofeyev|LW|27|36|26|23|29|223|26|27|-1.81|16 sh% mild regress|
|79|T. Meier|W|30|24|20|22|10|268|134|54|-2.03|24G on 269 SOG - positive regression|
|80|N. Dobson|D|27|12|36|35|7|161|63|192|-2.05|MTL yr2, PP time w/ Hutson competition|
|81|T. Hertl|C|33|21|30|38|22|180|111|44|-2.07|Decline watch|
|82|M. Geekie|C/W|28|37|27|21|23|170|103|32|-2.08|21.5 sh% - regress G hard|
|83|D. Hamilton|D|26|12|28|50|14|209|87|77|-2.39|Health risk|
|84|M. Marner|W|30|23|55|24|23|161|24|46|-2.51|Stable|
|85|V. Trocheck|C|33|14|33|62|14|101|187|48|-2.59|Physical holds|
|86|V. Dunn|D|30|11|32|54|20|175|27|86|-2.87|Stable|
|87|A. Panarin|LW|35|22|45|17|18|179|10|14|-4.64|Age cliff risk|
|88|J. Tavares|C|36|24|31|23|16|148|62|20|-4.98|Age cliff risk|
|89|A. Ovechkin|RW|41|22|22|21|13|167|110|13|-5.13|Age 41; volume fade|
|90|R. Josi|D|36|10|32|25|19|140|20|85|-5.13|Age + health|
|91|S. Crosby|C|39|20|32|37|16|113|51|25|-5.44|Ageless but 39|
|92|E. Karlsson|D|36|12|39|18|20|136|17|54|-5.51|Age decline|

## Projection model notes
- Risers: W. Johnston (23), Slafkovsky (22, kept by ER), Schaefer (19, kept by Puppa), Fantilli (22, kept by PK), Sennecke (20, TD trade chip), Matthews (bounce-back), Hutson (22, kept), Cuylle (24), Meier (shot-volume regression up), Carlsson (22, TD keeper)
- Decliners/fades: Stamkos (20.4 sh% at 36 — biggest fade on board), Ovechkin (41), Panarin (35, zero bangers), Tavares/Josi/E. Karlsson (36), Crosby (39), Geekie (21.5 sh%), Kucherov cliff-watch (33), Scheifele/Zibanejad (33)
- Team-change notes from 25-26: Q. Hughes→MIN, Nurse→SJ, Tuch→WSH, Panarin→LA, Dobson→MTL, Trocheck→UTA, Sherwood→SJ, Dorofeyev→NYR, Suzuki stays MTL

## 2026 offseason movement (news sweep 2026-07-05 — now in overrides.csv, merged into model)
- **Brady Tkachuk → FLA** (3 firsts + a 2nd to OTT; joins Matthew). Still elite in this format (vorp 7.2, #4 available); slight volume haircut on a loaded top-9. **OTT fallout: Cozens' top-6 is safe, Eklund arrives on Stutzle's wing** — TD's Cozens keeper unaffected.
- **Raddysh → TOR**: his 22G/70P was TBL-PP1-driven; that role is gone. Vorp collapsed 2.30 → 0.29; **trade target DEAD (−0.76 surplus)**.
- **Larkin trade request from DET** (Dallas favored; Yzerman noncommittal). DeBrincat haircut applied (0.95) → surplus down to +0.23, still positive but lowball-only. **Larkin is TD currency — his value RISES if dealt to DAL; shop him after destination confirms.**
- **Tuch → WSH** (projected Ovechkin line): improves to −0.15 — still a pass.
- **Revised trade-target table:** Jarvis +1.23 (but draft-don't-trade — Autodraft can't keep him, no R4–R7 picks), DeBrincat +0.23, everyone else negative. **The pre-draft trade market has mostly dried up; SOG/goalie fixes come from the draft.**
- Other movers in overrides.csv: Kyrou→WSH, Peterka→BOS (Pastrnak line), Byram→CHI (PP1 w/ Bedard), McTavish→STL 2C, Nemec→CGY, Zuccarello→LAK (Kaprizov loses his winger, 0.97), Trocheck+Lee→UTA (**mild Cooley TOI competition, 0.97**), Carlson→TBL (0.90), Nichushkin→CBJ, Nurse+Trouba→SJS.
- **Goalie carousel:** Bobrovsky→TOR (Gents' keeper — new team), Markstrom→FLA, Andersen→EDM (tandem w/ Jarry; Andersen is reigning champ — CAR won the Cup), Skinner→WPG, Woll→PHI (behind Vladar), Cossa→UTA. **⚠️ Hellebuyck (our G4): Jets signed Skinner 2yr/$7.5M and a trade is widely expected (BUF loudest suitor). His 58-start/32W projection assumes WPG — treat as volatile until resolved.**
- 2026 NHL draft: Gavin McKenna projected/went #1 (TOR per mocks) — 2026 draftees are NOT in the model (zero NHL games); rookie fliers need the manual NHLe module.

## Open items / TODO
1. Confirm draft order when drawn (late July) — linear, so slot value compounds; Autodraft + ER slots also matter (TD owns their picks)
2. ~~Verify Hellebuyck status~~ DONE 2026-07-05: projects G4 overall in v2 model — Yahoo top-175 absence was a Yahoo list artifact, not performance
3. Verify Holloway 25-26 season line before locking R7 keeper (v2 model: 23G/31A/149HIT in 67gp proj, z −1.60 — marginal, as suspected)
4. ~~Pull TD's weekly category W/L splits~~ DONE 2026-07-05: diagnosis CORRECTED — see revised section above (SOG + goalies, not bangers)
5. ~~Make Tuch trade call to ER~~ REVISED 2026-07-05 by `pick_value.py` (leverage-weighted board): Tuch surplus at R6 keep = **−0.62** — a pass at any real price; the urgency came from the disproven banger diagnosis. New target order by net surplus: **Raddysh +1.32 (R8 keep), DeBrincat +0.95 (R5), Jarvis +0.88 (R6)**; Heiskanen +0.03 breakeven; Aho/Meier/Tuch negative. Full table in `output/pick_values.md`
6. Watch for rivals discovering Autodraft's R4-R7 hole
7. ~~NHL API blocked in sandbox~~ DONE 2026-07-05: full v2 data pulled at home; projections in `output/projections_v2.md`
8. Re-pull Yahoo ADP/pre-draft ranks in September (`fetch_yahoo_draftprep.py` — not published yet in July); sleeper list = v2 vorp rank vs ADP
9. Manual review needed: July 1 FA movers (rates reflect old-team deployment) + zero-NHL-game rookies + goalie depth-chart changes

## Raw keeper CSV (ground truth, decoded from UTF-16)
Team Name,Player Name,Drafted Round,Keeper Round,C,LW,RW,D,G
Autodraft,Nick Suzuki,20,18,x,,,,
Autodraft,Vincent Trocheck,7,5,x,,,,
Autodraft,Andrei Svechnikov,6,4,,x,x,,
Autodraft,Kiefer Sherwood,10,8,,x,x,,
Autodraft,Seth Jarvis,8,6,x,x,x,,
Autodraft,Brandon Hagel,12,10,,x,x,,
Autodraft,Miro Heiskanen,6,4,,,,x,
Autodraft,Jacob Trouba,14,12,,,,x,
Autodraft,Jakob Chychrun,11,9,,,,x,
Autodraft,Noah Dobson,9,7,,,,x,
Autodraft,Simon Edvinsson,19,17,,,,x,
Autodraft,Mark Scheifele,11,9,x,,,,
Autodraft,Joel Eriksson Ek,9,7,x,,,,
Autodraft,Filip Gustavsson,13,11,,,,,x
Autodraft,Scott Wedgewood,Not Drafted,12,,,,,x
The Most Distinguished Gents,Sam Bennett,10,12,x,,,,
The Most Distinguished Gents,Mark Kastelic,Not Drafted,12,x,,x,,
The Most Distinguished Gents,Alexis Lafreniere,20,12,,x,x,,
The Most Distinguished Gents,Steven Stamkos,7,12,x,x,x,,
The Most Distinguished Gents,Adrian Kempe,5,3,,,x,,
The Most Distinguished Gents,Roman Josi,4,2,,,,x,
The Most Distinguished Gents,Darnell Nurse,8,6,,,,x,
The Most Distinguished Gents,John Carlson,16,14,,,,x,
The Most Distinguished Gents,Alex DeBrincat,7,5,,x,x,,
The Most Distinguished Gents,Drake Batherson,13,11,,x,x,,
The Most Distinguished Gents,Sergei Bobrovsky,10,8,,,,,x
The Most Distinguished Gents,Ilya Sorokin,4,2,,,,,x
The Most Distinguished Gents,Brad Marchand,14,12,,x,x,,
The Most Distinguished Gents,Sidney Crosby,4,2,x,,,,
The Most Distinguished Gents,Evgeni Malkin,Not Drafted,12,x,x,x,,
Sawchuk Dun Thats,Sebastian Aho,8,6,x,,,,
Sawchuk Dun Thats,Jake Guentzel,4,2,,x,x,,
Sawchuk Dun Thats,Timo Meier,8,6,,x,x,,
Sawchuk Dun Thats,Matthew Tkachuk,6,4,,x,x,,
Sawchuk Dun Thats,Martin Necas,12,10,,,x,,
Sawchuk Dun Thats,Will Smith,19,17,x,x,x,,
Sawchuk Dun Thats,Wyatt Johnston,5,3,x,,x,,
Sawchuk Dun Thats,Evan Bouchard,5,12,,,,x,
Sawchuk Dun Thats,Adam Fox,4,2,,,,x,
Sawchuk Dun Thats,Jack Eichel,10,8,x,,,,
Sawchuk Dun Thats,Rasmus Andersson,Not Drafted,12,,,,x,
Sawchuk Dun Thats,Spencer Knight,Not Drafted,12,,,,,x
Sawchuk Dun Thats,Adin Hill,8,6,,,,,x
Sawchuk Dun Thats,Mackenzie Blackwood,11,9,,,,,x
Sawchuk Dun Thats,Anton Lundell,Not Drafted,12,x,,,,
AdamSuxDix,Nico Hischier,16,12,x,,,,
AdamSuxDix,Tage Thompson,5,3,x,,x,,
AdamSuxDix,Elias Pettersson,5,3,x,x,,,
AdamSuxDix,Filip Forsberg,14,12,,x,,,
AdamSuxDix,Morgan Geekie,Not Drafted,12,x,x,x,,
AdamSuxDix,Bryan Rust,Not Drafted,12,,,x,,
AdamSuxDix,Charlie Coyle,Not Drafted,12,x,,x,,
AdamSuxDix,MacKenzie Weegar,11,9,,,,x,
AdamSuxDix,Vince Dunn,20,18,,,,x,
AdamSuxDix,Nikita Zadorov,10,8,,,,x,
AdamSuxDix,Brock Faber,Not Drafted,12,,,,x,
AdamSuxDix,Alex Laferriere,Not Drafted,12,x,x,x,,
AdamSuxDix,Alex Ovechkin,4,2,,x,x,,
AdamSuxDix,Tomas Hertl,18,16,x,x,,,
AdamSuxDix,John Tavares,9,7,x,,,,
AdamSuxDix,Alex Lyon,Not Drafted,12,,,,,x
AdamSuxDix,Dan Vladar,Not Drafted,12,,,,,x
AdamSuxDix,Sam Reinhart,6,4,x,,x,,
AdamSuxDix,Radko Gudas,10,8,,,,x,
Emotional Reactions,Mika Zibanejad,9,7,x,,x,,
Emotional Reactions,Artemi Panarin,4,2,,x,,,
Emotional Reactions,Will Cuylle,15,13,,x,x,,
Emotional Reactions,Jason Robertson,12,10,,x,x,,
Emotional Reactions,Juraj Slafkovsk�,11,9,,x,x,,
Emotional Reactions,Darren Raddysh,Not Drafted,12,,,,x,
Emotional Reactions,Josh Manson,Not Drafted,12,,,,x,
Emotional Reactions,Lane Hutson,18,16,,,,x,
Emotional Reactions,Charlie McAvoy,5,3,,,,x,
Emotional Reactions,Macklin Celebrini,14,12,x,,,,
Emotional Reactions,Alex Tuch,8,6,,x,x,,
Emotional Reactions,Matt Boldy,6,4,,x,x,,
Emotional Reactions,Jeremy Swayman,12,10,,,,,x
Emotional Reactions,Linus Ullmark,7,12,,,,,x
Emotional Reactions,Jake Sanderson,15,13,,,,x,
Emotional Reactions,Yaroslav Askarov,21,19,,,,,x
Twin Daddy,Cutter Gauthier,21,19,x,x,x,,
Twin Daddy,Shane Pinto,Not Drafted,12,x,,,,
Twin Daddy,Dylan Cozens,17,15,x,,,,
Twin Daddy,Dylan Holloway,9,7,x,x,,,
Twin Daddy,Tyler Bertuzzi,Not Drafted,12,,x,x,,
Twin Daddy,Travis Konecny,7,12,,x,x,,
Twin Daddy,Pavel Dorofeyev,Not Drafted,12,,x,x,,
Twin Daddy,Beckett Sennecke,Not Drafted,12,,,x,,
Twin Daddy,Jackson LaCombe,14,12,,,,x,
Twin Daddy,Erik Karlsson,Not Drafted,12,,,,x,
Twin Daddy,Brandt Clarke,20,12,,,,x,
Twin Daddy,Dylan Guenther,12,10,,x,x,,
Twin Daddy,Logan Cooley,18,16,x,,,,
Twin Daddy,Leo Carlsson,Not Drafted,12,x,,,,
Twin Daddy,Gabriel Landeskog,19,12,,x,x,,
Twin Daddy,Dylan Larkin,13,11,x,,,,
Twin Daddy,Jesper Wallstedt,Not Drafted,12,,,,,x
Twin Daddy,Lukas Dostal,21,19,,,,,x
Daren Puppa�d His Pants,Trevor Zegras,Not Drafted,12,x,x,x,,
Daren Puppa�d His Pants,Bo Horvat,Not Drafted,12,x,,,,
Daren Puppa�d His Pants,Jesper Bratt,7,5,,x,x,,
Daren Puppa�d His Pants,Zach Hyman,9,7,,x,x,,
Daren Puppa�d His Pants,Clayton Keller,12,10,,x,x,,
Daren Puppa�d His Pants,Kirill Marchenko,Not Drafted,12,,,x,,
Daren Puppa�d His Pants,Thomas Harley,11,12,,,,x,
Daren Puppa�d His Pants,Seth Jones,11,9,,,,x,
Daren Puppa�d His Pants,Zach Werenski,16,14,,,,x,
Daren Puppa�d His Pants,Alexander Nikishin,17,15,,,,x,
Daren Puppa�d His Pants,Tom Wilson,6,4,,,x,,
Daren Puppa�d His Pants,Matthew Schaefer,20,18,,,,x,
Daren Puppa�d His Pants,Jake Walman,20,18,,,,x,
Daren Puppa�d His Pants,Mark Stone,Not Drafted,12,,,x,,
Daren Puppa�d His Pants,Evander Kane,15,13,,x,,,
Daren Puppa�d His Pants,Jacob Markstrom,8,12,,,,,x
Daren Puppa�d His Pants,John Gibson,Not Drafted,12,,,,,x
Daren Puppa�d His Pants,Logan Thompson,9,7,,,,,x
Daren Puppa�d His Pants,Aleksander Barkov,19,17,x,,,,
Daren Puppa�d His Pants,Kevin Fiala,7,12,,x,,,
P.K. SubUwU,Yakov Trenin,Not Drafted,12,x,x,x,,
P.K. SubUwU,Brayden Point,4,2,x,,,,
P.K. SubUwU,Adam Fantilli,17,12,x,,,,
P.K. SubUwU,Boone Jenner,18,16,x,x,,,
P.K. SubUwU,Mikael Granlund,Not Drafted,12,x,x,x,,
P.K. SubUwU,Cole Caufield,14,12,,x,x,,
P.K. SubUwU,Mathieu Olivier,16,14,,,x,,
P.K. SubUwU,Vasily Podkolzin,Not Drafted,12,,x,x,,
P.K. SubUwU,Mattias Samuelsson,Not Drafted,12,,,,x,
P.K. SubUwU,Shayne Gostisbehere,Not Drafted,12,,,,x,
P.K. SubUwU,Shea Theodore,16,14,,,,x,
P.K. SubUwU,Dougie Hamilton,6,4,,,,x,
P.K. SubUwU,Emil Heineman,Not Drafted,12,,x,x,,
P.K. SubUwU,Matthew Knies,10,8,,x,,,
P.K. SubUwU,Jakub Dobes,Not Drafted,12,,,,,x
P.K. SubUwU,Jet Greaves,Not Drafted,12,,,,,x
P.K. SubUwU,Darcy Kuemper,16,14,,,,,x
P.K. SubUwU,Dustin Wolf,10,12,,,,,x
