import numpy as np
# (overall_rank, name, W, SV, SA, SVpct, SHO)
G = [
(9,"Wedgewood",31,1007,1093,.921,4),(16,"Sorokin",29,1386,1530,.906,7),
(21,"L.Thompson",31,1447,1587,.912,4),(27,"Vasilevskiy",39,1351,1483,.911,2),
(30,"Hofer",24,1136,1250,.909,6),(47,"Oettinger",35,1234,1372,.899,4),
(49,"Wallstedt",18,933,1020,.915,4),(58,"Gustavsson",28,1244,1377,.903,4),
(64,"Swayman",31,1425,1571,.907,2),(66,"Gibson",29,1317,1461,.901,4),
(80,"Greaves",26,1397,1539,.908,2),(83,"Shesterkin",25,1299,1425,.912,1),
(91,"Vejmelka",38,1457,1626,.896,2),(94,"Blackwood",23,843,933,.904,3),
(98,"Lyon",20,887,979,.906,3),(108,"A.Forsberg",16,865,952,.909,3),
(113,"Luukkonen",22,845,930,.909,1),(115,"Vladar",29,1162,1283,.906,0),
(118,"Bussi",31,815,912,.894,2),(122,"Knight",19,1428,1583,.902,3),
(142,"Ullmark",28,1067,1198,.891,3),(144,"Dobes",29,1070,1187,.901,0),
(154,"Wolf",23,1400,1558,.899,2),(167,"DeSmith",15,689,760,.907,1),(174,"Ingram",16,686,763,.899,2),
]
ranks = np.array([g[0] for g in G], float)
names = [g[1] for g in G]
# features: W, SV% (weighted by workload? test raw first), SHO
X = np.array([[g[2], g[5], g[6]] for g in G], float)
cats = ["W","SV%","SHO"]
mu, sd = X.mean(0), X.std(0)
Z = (X-mu)/sd
pairs = [(i,j) for i in range(len(G)) for j in range(len(G)) if ranks[i]<ranks[j]]
diffs = np.array([Z[i]-Z[j] for i,j in pairs])
w = np.ones(3)/3
for _ in range(5000):
    p = 1/(1+np.exp(-(diffs@w)))
    w -= 0.05 * (diffs.T @ (p-1))/len(pairs)
    w = np.maximum(w,0)
def rankdata(a):
    t=np.argsort(a); r=np.empty(len(a)); r[t]=np.arange(1,len(a)+1); return r
score = Z@w
rho = np.corrcoef(rankdata(ranks), rankdata(-score))[0,1]
print("Goalie weights:", dict(zip(cats, np.round(w/w.sum(),3))), " Spearman:", round(rho,4))
viol = np.mean((diffs@w)<=0); print(f"violations {viol*100:.1f}%")
worst = np.argsort(-np.abs(rankdata(-score)-rankdata(ranks)))[:5]
for i in worst: print(f"  {names[i]:12s} yahoo#{int(ranks[i])} fitted-internal#{int(rankdata(-score)[i])}")
np.save("goalie_weights.npy", w); np.save("goalie_norm.npy", np.vstack([mu,sd]))
