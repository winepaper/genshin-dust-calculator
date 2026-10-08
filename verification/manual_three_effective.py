"""Independent hand-derived check: cup, ER/CR/CD all weight 1, pity CR/CD.

Does not import the production engine, inference or terminal-guarantee DP.
ER 18.1 admits triples (5.18,6.48,6.48) and (5.83,5.83,6.48),
each with three permutations and exact total 18.14.
"""
from collections import defaultdict
from fractions import Fraction
from math import comb, lcm
import json

cr=(272,311,350,389)
cd=(544,622,699,777)
er=(453,518,583,648)
factors=[Fraction(4,sum(x)) for x in (cr,cd,er)]
scale=lcm(*(f.denominator for f in factors))
a,b,c=(int(f*scale) for f in factors)

def sums(dice):
    distributions=[{0:1.0}]
    for _ in range(5):
        next_dist=defaultdict(float)
        for total,p in distributions[-1].items():
            for roll in dice:
                next_dist[total+roll]+=p/len(dice)
        distributions.append(dict(next_dist))
    return distributions

selected=sums([a*x for x in cr]+[b*x for x in cd])
other=sums([c*x for x in er]+[0]*4)
cd_states=[(544,2020,2/12),(622,2020,1/12),(622,2021,2/12),
           (699,2020,4/12),(777,2020,2/12),(777,2021,1/12)]
er_states=[(518,1/6),(583,1/3),(648,1/2)]
hypotheses=[(a*544+b*current_cd+c*1814,a*272+b*base_cd+c*base_er,p_cd*p_er)
            for base_cd,current_cd,p_cd in cd_states for base_er,p_er in er_states]
current=sum(old*p for old,base,p in hypotheses)/scale
results={}
for g in (2,3,4):
    pk=defaultdict(float)
    for k in range(6):
        pk[max(k,g)]+=comb(5,k)/32
    upgrade=defaultdict(float)
    for k,p_k in pk.items():
        for x,p_x in selected[k].items():
            for y,p_y in other[5-k].items():
                upgrade[x+y]+=p_k*p_x*p_y
    win=gain=raw=0.0
    for old,base,p_state in hypotheses:
        for increment,p_roll in upgrade.items():
            mass=p_state*p_roll
            new=base+increment
            raw+=mass*new/scale
            if new>old:
                win+=mass
                gain+=mass*(new-old)/scale
    results[g]=dict(pwin=win,gain=gain,raw_mean=raw,final_mean=current+gain)

if __name__=='__main__':
    print(json.dumps(dict(current=current,results=results),ensure_ascii=False,indent=2))
