import numpy as np, json
# Reuse skater fit (equal weights confirmed) to get skater scores + yahoo ranks
exec(open("fit_yahoo.py").read().split("# Pairwise")[0])  # loads D, ranks, names, X, Z
sk_score = Z.mean(1)*7  # equal-weight z-sum
sk_rank = ranks
# goalie equal-weight z-sum
Gdat = [(9,31,.921,4),(16,29,.906,7),(21,31,.912,4),(27,39,.911,2),(30,24,.909,6),
(47,35,.899,4),(49,18,.915,4),(58,28,.903,4),(64,31,.907,2),(66,29,.901,4),
(80,26,.908,2),(83,25,.912,1),(91,38,.896,2),(94,23,.904,3),(98,20,.906,3),
(108,16,.909,3),(113,22,.909,1),(115,29,.906,0),(118,31,.894,2),(122,19,.902,3),
(142,28,.891,3),(144,29,.901,0),(154,23,.899,2),(167,15,.907,1),(174,16,.899,2)]
granks = np.array([g[0] for g in Gdat], float)
GX = np.array([g[1:] for g in Gdat], float)
gmu, gsd = GX.mean(0), GX.std(0)
gz = ((GX-gmu)/gsd).sum(1)
# For each goalie anchor: interpolate what skater z-sum sits at that overall rank
# (skater overall rank vs score curve)
o = np.argsort(sk_rank)
xr, ys = sk_rank[o], sk_score[o]
target = np.interp(granks, xr, ys)
# fit gz*alpha + beta = target
A = np.vstack([gz, np.ones(len(gz))]).T
alpha, beta = np.linalg.lstsq(A, target, rcond=None)[0]
pred = gz*alpha+beta
err = np.abs(pred-target)
print(f"goalie->skater scale: alpha={alpha:.4f} beta={beta:.4f}  mean |err|={err.mean():.3f} z-units")
# check merged ranks reproduce goalie overall ranks
allscores = np.concatenate([sk_score, pred])
merged = np.argsort(-allscores)
pos = np.empty(len(allscores)); pos[merged]=np.arange(1,len(allscores)+1)
gpos = pos[len(sk_score):]
print("goalie merged-rank vs yahoo (sample):")
for i in [0,1,3,6,12,20,24]:
    print(f"  yahoo#{int(granks[i]):3d} -> merged#{int(gpos[i]):3d}")
json.dump({"alpha":alpha,"beta":beta}, open("interleave.json","w"))
