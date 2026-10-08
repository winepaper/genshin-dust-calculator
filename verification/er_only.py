"""ER-only risk derived with exact fractions, independently of engine.py."""
from collections import defaultdict
from fractions import Fraction as F
from math import comb

counts=defaultdict(F)
for x in range(6):
    k=max(x,2)
    for n in range(5-k+1):
        counts[n]+=F(comb(5,x),32)*F(comb(5-k,n),2**(5-k))

rolls=(453,518,583,648)
bases=((518,F(1,6)),(583,F(1,3)),(648,F(1,2)))
roll_dist=[{0:F(1)}]
for _ in range(3):
    nxt=defaultdict(F)
    for total,p in roll_dist[-1].items():
        for value in rolls:
            nxt[total+value]+=p/4
    roll_dist.append(dict(nxt))

win=tie=bad=positive_pp=raw_pp=F(0)
for base,p_base in bases:
    for n,p_n in counts.items():
        for increment,p_roll in roll_dist[n].items():
            mass=p_base*p_n*p_roll
            diff=F(base+increment-1814,100)
            raw_pp+=mass*diff
            if diff>0:
                win+=mass
                positive_pp+=mass*diff
            elif diff<0:
                bad+=mass
            else:
                tie+=mass

if __name__=='__main__':
    print('ER count probabilities:',{n:str(p) for n,p in sorted(counts.items())})
    print('Win/tie/bad:',float(win),float(tie),float(bad))
    print('Raw ER change (percentage points):',float(raw_pp))
    print('Keep-or-revert ER improvement:',float(positive_pp))
