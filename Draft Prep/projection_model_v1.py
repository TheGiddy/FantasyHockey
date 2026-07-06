import math

# name, pos, age (Jan 2027), G, A, PIM, PPP, SOG, HIT, BLK, deploy_mult, note
P = [
("C. McDavid","C",30,48,90,44,54,306,40,30,1.00,"Elite stable"),
("N. MacKinnon","C",31,53,74,39,30,350,64,35,1.00,"Volume ages well"),
("M. Celebrini","C",20,45,70,44,33,287,53,53,1.06,"Franchise ascent, PP1 locked"),
("N. Kucherov","RW",33,44,86,50,37,231,36,29,1.00,"Skill ages, watch cliff"),
("D. Pastrnak","RW",30,29,71,72,33,261,86,32,1.00,"29G low vs 15% career sh% - positive regression"),
("J. Robertson","LW",27,45,51,32,41,294,48,34,1.00,"Prime"),
("M. Seider","D",25,10,50,57,28,187,128,180,1.03,"Entering D prime"),
("N. Suzuki","C",27,29,72,28,43,183,62,62,1.00,"Prime"),
("E. Bouchard","D",27,21,74,30,33,221,29,101,1.00,"PP1 EDM"),
("W. Johnston","C",23,45,41,32,42,206,56,55,1.05,"Ascending, Hintz aging"),
("M. Boldy","LW",25,42,43,30,30,254,60,58,1.03,"Prime entry"),
("K. Kaprizov","LW",29,45,44,28,32,269,52,27,1.00,"Stable"),
("J. Guentzel","LW",32,38,50,61,30,220,39,41,1.00,"Age risk"),
("T. Thompson","C/RW",29,40,41,35,24,272,85,48,1.00,"Stable"),
("D. Cozens","C",25,28,31,59,29,205,215,24,1.03,"OTT top-6 locked; hits sticky"),
("T. Stutzle","C",25,34,49,39,29,194,126,44,1.03,"Prime entry"),
("F. Forsberg","LW",32,40,35,34,26,246,124,33,1.00,"Age risk"),
("A. Svechnikov","LW",26,31,39,66,29,203,148,16,1.04,"Contract yr; CAR top-6"),
("J. Slafkovsky","LW",22,30,43,52,28,180,105,78,1.07,"Age-22 leap w/ Suzuki"),
("T. Wilson","RW",32,30,32,117,12,153,179,53,1.00,"Physical ages OK"),
("R. Dahlin","D",26,19,55,76,22,194,67,79,1.02,"Prime"),
("M. Zibanejad","C",33,34,44,14,35,215,105,50,1.00,"Decline watch"),
("M. Necas","RW",30,38,62,30,24,206,85,26,1.00,"COL top-6"),
("L. Draisaitl","C",31,35,62,26,42,186,34,15,1.00,"Slight fade"),
("C. Caufield","RW",26,51,37,14,29,258,50,21,1.00,"Prime sniper"),
("A. DeBrincat","RW",29,41,44,19,23,287,38,39,1.00,"Stable volume"),
("C. Makar","D",28,20,59,24,29,199,35,118,1.00,"Down-ish yr; rebound"),
("J. Eichel","C",30,27,63,18,28,260,35,40,1.00,"Stable"),
("J. Chychrun","D",28,26,34,62,18,221,58,114,1.00,"Volume D"),
("M. Rantanen","RW",30,22,55,93,34,139,48,30,1.02,"22G on 139 SOG = injury/usage dip; rebound"),
("Z. Werenski","D",29,22,59,18,21,260,30,94,1.00,"Elite volume D"),
("M. Scheifele","C",33,36,67,43,22,175,32,47,1.00,"Decline watch"),
("S. Stamkos","C/RW",36,42,24,58,26,206,89,36,1.00,"20.4 sh% at 36 - big regression"),
("A. Kempe","RW",30,36,37,58,12,226,127,39,1.00,"Stable"),
("M. Tkachuk","LW",29,22,37,71,20,221,162,19,1.02,"Injury-marred yr; rebound"),
("K. Connor","LW",30,39,53,16,19,274,36,19,1.00,"Stable"),
("C. Keller","RW",28,26,62,38,27,225,8,32,1.00,"Prime"),
("D. Guenther","RW",23,40,33,28,24,242,66,28,1.05,"Ascending sniper"),
("S. Aho","C",29,27,53,46,27,195,63,23,1.00,"Stable"),
("Q. Hughes","D",27,7,69,32,34,187,7,87,1.02,"New team yr2, PP1"),
("C. Gauthier","LW",23,41,28,28,19,285,64,20,1.06,"Ascending; ANA improving"),
("M. Weegar","D",33,4,24,88,6,154,167,175,1.00,"Physical D ages OK"),
("D. Larkin","C",30,34,33,48,24,229,46,33,1.00,"Stable"),
("W. Cuylle","LW",24,20,18,65,8,157,302,68,1.04,"Rising role NYR"),
("A. Tuch","RW",30,33,33,57,9,195,82,90,1.00,"Stable"),
("D. Batherson","RW",28,33,38,33,30,167,122,22,1.00,"Prime"),
("S. Bennett","C",30,26,32,82,14,201,115,32,1.00,"Physical stable"),
("M. Schaefer","D",19,23,36,38,18,222,40,111,1.12,"Gen talent yr2 leap"),
("C. McAvoy","D",29,11,50,62,23,111,79,129,1.00,"Injury history"),
("C. Bedard","C",21,30,45,50,21,226,31,27,1.10,"Year-4 ascent"),
("K. Sherwood","RW",31,23,13,50,12,172,339,30,0.98,"13.4 sh% ok; hits elite"),
("T. Hertl","C",33,24,34,39,25,202,114,45,1.00,"Decline watch"),
("A. Ovechkin","RW",41,32,32,26,19,244,134,16,0.90,"Age 41; volume fade"),
("R. Andersson","D",30,17,30,71,13,178,37,150,1.00,"Stable"),
("M. Sergachev","D",28,10,49,44,26,159,38,125,1.00,"Stable"),
("N. Hischier","C",28,28,38,29,23,211,58,62,1.00,"Prime"),
("B. Hagel","LW",28,36,38,58,12,214,42,38,1.00,"Prime"),
("D. Nurse","D",31,7,17,104,0,164,137,167,1.00,"Physical D"),
("L. Hutson","D",22,12,66,34,20,124,31,137,1.06,"Age-22 leap"),
("K. Marchenko","RW",27,27,40,32,23,218,61,40,1.00,"Prime"),
("A. Fantilli","C",22,24,35,38,13,214,139,51,1.08,"Age-22 leap, 1C role"),
("M. Barzal","C",29,19,53,61,20,184,29,50,1.00,"Injury history"),
("M. Geekie","C/W",28,39,29,22,24,181,110,34,0.94,"21.5 sh% - regress G hard"),
("M. Heiskanen","D",27,9,54,30,28,148,21,132,1.00,"2 straight injury yrs"),
("P. Dorofeyev","LW",27,37,27,24,30,230,27,28,0.97,"16 sh% mild regress"),
("T. Konecny","LW",29,27,41,59,14,168,108,38,1.00,"Stable"),
("N. Zadorov","D",31,2,20,152,0,107,196,102,1.00,"Physical D"),
("B. Clarke","D",23,8,32,63,13,159,30,185,1.05,"Ascending"),
("S. Jarvis","C/W",25,32,34,23,21,224,81,27,1.03,"Prime entry"),
("T. Zegras","C/W",25,26,41,62,23,167,46,28,1.02,"Re-establishing"),
("A. Panarin","LW",35,28,56,20,23,224,11,16,0.95,"Age cliff risk"),
("S. Crosby","C",39,29,45,44,23,160,60,30,0.93,"Ageless but 39"),
("V. Trocheck","C",33,16,37,64,16,114,193,49,1.00,"Physical holds"),
("J. Tavares","C",36,31,40,28,21,192,74,24,0.92,"Age cliff risk"),
("B. Sennecke","RW",20,23,37,62,13,197,97,24,1.10,"Yr2 leap; ANA rising"),
("T. Meier","W",30,24,20,22,10,269,131,53,1.02,"24G on 269 SOG - positive regression"),
("L. Raymond","RW",25,25,51,22,27,173,43,29,1.03,"Prime entry"),
("N. Dobson","D",27,12,35,34,7,158,62,188,1.02,"MTL yr2, PP time w/ Hutson competition"),
("M. Marner","W",30,24,56,24,24,165,24,46,1.00,"Stable"),
("R. Josi","D",36,13,42,30,24,181,24,101,0.92,"Age + health"),
("J. Hughes","C",25,27,50,10,23,228,4,32,1.03,"Prime; health risk"),
("J. LaCombe","D",26,10,48,19,17,157,74,128,1.03,"ANA rising, PP1"),
("A. Laferriere","W",25,21,23,18,5,209,255,49,1.03,"Rising role"),
("B. Faber","D",24,15,36,39,11,173,33,148,1.03,"Prime entry"),
("E. Karlsson","D",36,15,51,22,26,176,20,64,0.92,"Age decline"),
("M. Knies","LW",24,23,43,29,16,140,152,32,1.05,"Ascending power W"),
("V. Dunn","D",30,11,33,54,21,179,27,86,1.00,"Stable"),
("D. Hamilton","D",26,12,27,50,14,203,87,77,1.00,"Health risk"),
("A. Matthews","C",29,27,26,18,12,227,42,81,1.18,"Down yr (injury); elite rebound"),
("L. Carlsson","C",22,29,38,20,22,190,45,35,1.12,"Est. line; ANA 1C, age-22 leap"),
("L. Cooley","C",22,24,22,30,20,170,60,25,1.30,"54GP -> 78GP + leap"),
("D. Holloway","LW",25,25,38,45,15,190,140,40,1.02,"Est. line; STL top-6"),
]

def age_mult_off(age,pos):
    a = age - (1 if pos=="D" else 0)   # D peak later
    if a<=21: return 1.10
    if a<=23: return 1.06
    if a<=25: return 1.03
    if a<=28: return 1.00
    if a<=30: return 0.975
    if a<=32: return 0.94
    if a<=34: return 0.89
    if a<=36: return 0.84
    return 0.76

def age_mult_phys(age):
    if age<=23: return 1.03
    if age<=30: return 1.00
    if age<=34: return 0.97
    return 0.91

rows=[]
for (n,pos,age,g,a,pim,ppp,sog,hit,blk,dep,note) in P:
    mo = age_mult_off(age,"D" if pos=="D" else "F")*dep
    mp = age_mult_phys(age)*min(dep,1.05)
    pg,pa,pppp,psog = [round(x*mo) for x in (g,a,ppp,sog)]
    ppim,phit,pblk = [round(x*mp) for x in (pim,hit,blk)]
    rows.append([n,pos,age,pg,pa,ppim,pppp,psog,phit,pblk,note])

# z-score value in the 7 cats across this pool
import statistics as st
cats=list(zip(*[(r[3],r[4],r[5],r[6],r[7],r[8],r[9]) for r in rows]))
means=[st.mean(c) for c in cats]; sds=[st.pstdev(c) for c in cats]
for r in rows:
    z=sum((r[3+i]-means[i])/sds[i] for i in range(7))
    r.append(round(z,2))
rows.sort(key=lambda r:-r[-1])
hdr=["Proj rank","Player","Pos","Age","G","A","PIM","PPP","SOG","HIT","BLK","Value z","Note"]
print("|"+"|".join(hdr)+"|")
print("|"+"|".join(["---"]*len(hdr))+"|")
for i,r in enumerate(rows,1):
    print(f"|{i}|{r[0]}|{r[1]}|{r[2]}|{r[3]}|{r[4]}|{r[5]}|{r[6]}|{r[7]}|{r[8]}|{r[9]}|{r[10+1-1+1] if False else r[-1]}|{r[10]}|")
