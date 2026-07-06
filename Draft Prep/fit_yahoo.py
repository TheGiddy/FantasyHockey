import numpy as np

# (yahoo_rank, name, G, A, PIM, PPP, SOG, HIT, BLK) — 25-26 season, from league screenshots
D = [
(1,"McDavid",48,90,44,54,306,40,30),(2,"MacKinnon",53,74,39,30,350,64,35),
(3,"Celebrini",45,70,44,33,287,53,53),(4,"Kucherov",44,86,50,37,231,36,29),
(5,"Pastrnak",29,71,72,33,261,86,32),(6,"Robertson",45,51,32,41,294,48,34),
(7,"Seider",10,50,57,28,187,128,180),(8,"Suzuki",29,72,28,43,183,62,62),
(10,"Bouchard",21,74,30,33,221,29,101),(11,"Johnston",45,41,32,42,206,56,55),
(12,"Boldy",42,43,30,30,254,60,58),(13,"Kaprizov",45,44,28,32,269,52,27),
(14,"Guentzel",38,50,61,30,220,39,41),(15,"T.Thompson",40,41,35,24,272,85,48),
(17,"Cozens",28,31,59,29,205,215,24),(18,"Stutzle",34,49,39,29,194,126,44),
(19,"Forsberg",40,35,34,26,246,124,33),(20,"Svechnikov",31,39,66,29,203,148,16),
(22,"Raddysh",22,48,72,26,212,67,69),(23,"Slafkovsky",30,43,52,28,180,105,78),
(24,"Wilson",30,32,117,12,153,179,53),(25,"Dahlin",19,55,76,22,194,67,79),
(26,"Zibanejad",34,44,14,35,215,105,50),(28,"Necas",38,62,30,24,206,85,26),
(29,"Draisaitl",35,62,26,42,186,34,15),(31,"Caufield",51,37,14,29,258,50,21),
(32,"DeBrincat",41,44,19,23,287,38,39),(33,"Makar",20,59,24,29,199,35,118),
(34,"Eichel",27,63,18,28,260,35,40),(35,"Chychrun",26,34,62,18,221,58,114),
(36,"Rantanen",22,55,93,34,139,48,30),(37,"Werenski",22,59,18,21,260,30,94),
(38,"Scheifele",36,67,43,22,175,32,47),(39,"Stamkos",42,24,58,26,206,89,36),
(40,"Kempe",36,37,58,12,226,127,39),(41,"M.Tkachuk",22,37,71,20,221,162,19),
(42,"Connor",39,53,16,19,274,36,19),(43,"Keller",26,62,38,27,225,8,32),
(44,"Guenther",40,33,28,24,242,66,28),(45,"Aho",27,53,46,27,195,63,23),
(46,"Q.Hughes",7,69,32,34,187,7,87),(48,"Gauthier",41,28,28,19,285,64,20),
(50,"Weegar",4,24,88,6,154,167,175),(51,"Larkin",34,33,48,24,229,46,33),
(52,"Cuylle",20,18,65,8,157,302,68),(53,"Tuch",33,33,57,9,195,82,90),
(54,"Batherson",33,38,33,30,167,122,22),(55,"Bennett",26,32,82,14,201,115,32),
(56,"Schaefer",23,36,38,18,222,40,111),(57,"McAvoy",11,50,62,23,111,79,129),
(59,"Bedard",30,45,50,21,226,31,27),(60,"Sherwood",23,13,50,12,172,339,30),
(61,"Hertl",24,34,39,25,202,114,45),(62,"Ovechkin",32,32,26,19,244,134,16),
(63,"R.Andersson",17,30,71,13,178,37,150),(65,"Sergachev",10,49,44,26,159,38,125),
(67,"Hischier",28,38,29,23,211,58,62),(68,"Hagel",36,38,58,12,214,42,38),
(69,"Nurse",7,17,104,0,164,137,167),(70,"Hutson",12,66,34,20,124,31,137),
(71,"Marchenko",27,40,32,23,218,61,40),(72,"Fantilli",24,35,38,13,214,139,51),
(73,"Barzal",19,53,61,20,184,29,50),(74,"Geekie",39,29,22,24,181,110,34),
(75,"Heiskanen",9,54,30,28,148,21,132),(76,"Dorofeyev",37,27,24,30,230,27,28),
(77,"Konecny",27,41,59,14,168,108,38),(78,"Zadorov",2,20,152,0,107,196,102),
(79,"Clarke",8,32,63,13,159,30,185),(81,"Jarvis",32,34,23,21,224,81,27),
(82,"Schmaltz",33,41,28,20,206,23,52),(84,"Zegras",26,41,62,23,167,46,28),
(85,"Panarin",28,56,20,23,224,11,16),(86,"Crosby",29,45,44,23,160,60,30),
(87,"Rust",29,36,26,24,183,35,71),(88,"Trocheck",16,37,64,16,114,193,49),
(89,"Tavares",31,40,28,21,192,74,24),(90,"Sennecke",23,37,62,13,197,97,24),
(92,"Nelson",33,32,36,18,186,38,65),(93,"Tippett",28,23,32,7,220,166,50),
(95,"Meier",24,20,22,10,269,131,53),(96,"Raymond",25,51,22,27,173,43,29),
(97,"Dobson",12,35,34,7,158,62,188),(99,"Marner",24,56,24,24,165,24,46),
(100,"Josi",13,42,30,24,181,24,101),(101,"Hronek",8,41,33,21,137,133,100),
(102,"J.Hughes",27,50,10,23,228,4,32),(103,"Horvat",31,26,40,16,226,51,38),
(104,"Ehlers",26,45,14,29,207,21,24),(105,"LaCombe",10,48,19,17,157,74,128),
(106,"Laferriere",21,23,18,5,209,255,49),(107,"Faber",15,36,39,11,173,33,148),
(109,"Kastelic",12,10,140,1,100,215,64),(110,"E.Karlsson",15,51,22,26,176,20,64),
(111,"Knies",23,43,29,16,140,152,32),(112,"Dunn",11,33,54,21,179,27,86),
(114,"Hamilton",12,27,50,14,203,87,77),(116,"Walker",9,22,59,1,179,141,125),
(117,"O'Reilly",25,49,22,20,154,17,66),(119,"Matthews",27,26,18,12,227,42,81),
]
ranks = np.array([d[0] for d in D], float)
names = [d[1] for d in D]
X = np.array([d[2:] for d in D], float)
cats = ["G","A","PIM","PPP","SOG","HIT","BLK"]

# z-normalize within sample (note: truncated top sample; fit is on ORDER so monotone-safe)
mu, sd = X.mean(0), X.std(0)
Z = (X - mu) / sd

# Pairwise logistic rank fit: for every pair (i better than j), want w·(Zi - Zj) > 0
pairs = [(i,j) for i in range(len(D)) for j in range(len(D)) if ranks[i] < ranks[j]]
diffs = np.array([Z[i]-Z[j] for i,j in pairs])

w = np.ones(7)/7
lr = 0.05
for epoch in range(3000):
    s = diffs @ w
    p = 1/(1+np.exp(-s))
    grad = diffs.T @ (p - 1) / len(pairs)
    w -= lr * grad
    w = np.maximum(w, 0)          # category weights can't be negative in a cats rank
    if w.sum() > 0: pass
wn = w / w.sum()

score = Z @ w
order = np.argsort(-score)
fitted_rank = np.empty(len(D)); fitted_rank[order] = np.arange(1, len(D)+1)

# Spearman
from numpy import corrcoef
def rankdata(a):
    tmp = np.argsort(a); r = np.empty(len(a)); r[tmp] = np.arange(1,len(a)+1); return r
rho = corrcoef(rankdata(ranks), rankdata(-score))[0,1]
viol = np.mean((diffs @ w) <= 0)

print("Learned category weights (normalized):")
for c,v in sorted(zip(cats, wn), key=lambda t:-t[1]):
    print(f"  {c:4s} {v:.3f}")
print(f"\nSpearman rho vs Yahoo rank: {rho:.4f}")
print(f"Pairwise order violations: {viol*100:.1f}%")
resid = fitted_rank - rankdata(ranks)
worst = np.argsort(-np.abs(resid))[:8]
print("\nBiggest misfits (fitted vs Yahoo):")
for i in worst:
    print(f"  {names[i]:12s} yahoo#{int(ranks[i]):3d}  fitted#{int(fitted_rank[i]):3d}  ({int(resid[i]):+d})")
np.save("yahoo_weights.npy", w)
print("\nweights saved (raw):", np.round(w,4))
print("norm params mu:", np.round(mu,2), "sd:", np.round(sd,2))
